"""Pipeline completo del Lab03: python main.py

Etapas (cada una escribe sus salidas en artifacts/):
    1. data           descarga, limpieza, validación y split 60/20/20
    2. cointegration  universo → correlación → Engle-Granger → Johansen → vector reversivo
    3. kalman         filtro 1 (β_t) y filtro 2 (μ_t, σ_t → z_t)
    4. strategy       VECM, grid search de umbrales en train, señales y sizing
    5. backtest       motor multi-pata con costos, walk-forward, rebalanceo vs banda
    6. performance    métricas por split

Los parámetros globales viven aquí y se pasan como argumentos a cada etapa.
Los parámetros propios de cada módulo (costos, umbrales, split) viven en ese módulo.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from cointegration.johansen import ANCHOR_TICKER, ROLLING_WINDOW, rolling_first_eigenvector
from cointegration.selection import describe_chosen_group, multiple_testing_summary, run_funnel
from cointegration.universe import UNIVERSES, all_tickers
from data.clean import clean_prices
from data.download import load_prices
from data.split import SplitDates, add_split_column, compute_split_dates, save_split_dates, slice_split
from data.validate import JUMP_THRESHOLD, assert_valid, validate_prices
from kalman.weights_filter import BURN_IN, absorbed_fraction, calibrate_q, run_weights_filter, static_ect
from performance.figures import (plot_dynamic_weights, plot_ect_comparison, plot_kalman_gains,
                                 plot_normalized_prices, plot_rolling_eigenvector)

# --- Reproducibilidad: semilla fija para todo el pipeline ---
SEED = 42

# --- Rutas ---
ROOT = Path(__file__).resolve().parent
DATA_SNAPSHOT = ROOT / "data" / "snapshot" / "prices_raw.parquet"  # versionado en Git
ARTIFACTS = ROOT / "artifacts"
FIGURES = ROOT / "docs" / "figuras"

# --- Ventana histórica (10-15 años de precios diarios, fechas fijas para reproducibilidad) ---
START_DATE = "2012-01-01"  # ≈ 14.8 años hasta END_DATE (el enunciado pide 10-15)
END_DATE = "2026-10-30"

# --- Artefactos: cifras significativas de los resultados numéricos ---
# El álgebra lineal (BLAS) da diferencias de ~1e-13 relativo entre computadoras; sin redondear, cada corrida en otra
# máquina "modifica" los artefactos versionados y genera diffs y conflictos falsos en Git. Los precios no se redondean.
ARTIFACT_SIG_DIGITS = 8


def round_floats(df: pd.DataFrame, digits: int = ARTIFACT_SIG_DIGITS) -> pd.DataFrame:
    """Copia de `df` con sus columnas flotantes redondeadas a `digits` cifras significativas (para artefactos)."""
    floats = df.select_dtypes("float").columns
    return df.assign(**{c: df[c].map(lambda v: float(f"{v:.{digits}g}")) for c in floats})


def json_text(obj, digits: int = ARTIFACT_SIG_DIGITS) -> str:
    """JSON indentado con los flotantes redondeados a `digits` cifras significativas (para artefactos)."""
    rounded = json.loads(json.dumps(obj), parse_float=lambda v: float(f"{float(v):.{digits}g}"))
    return json.dumps(rounded, indent=2, ensure_ascii=False)


def run_data_stage() -> tuple[pd.DataFrame, SplitDates]:
    """Etapa 1: precios limpios y validados de todos los universos + fechas de corte congeladas."""
    raw = load_prices(all_tickers(), START_DATE, END_DATE, DATA_SNAPSHOT)
    prices, clean_report = clean_prices(raw)
    report = validate_prices(prices)
    assert_valid(report)
    split_dates = compute_split_dates(prices.index)

    save_split_dates(split_dates, ARTIFACTS / "split_dates.json")
    (ARTIFACTS / "validation_report.json").write_text(
        json_text({"cleaning": clean_report, "validation": report.to_dict()})
    )
    print(f"[data] {report.n_rows} días × {prices.shape[1]} activos, {report.start.date()} → {report.end.date()}")
    print(f"[data] rellenados: {clean_report['filled_cells'] or 'ninguno'}; fechas eliminadas: {clean_report['rows_dropped']}")
    print(f"[data] saltos anómalos (|rend. log| > {JUMP_THRESHOLD}): {len(report.jumps)} (detalle en el notebook 01)")
    for name in ("train", "test", "validation"):
        start, end = split_dates.bounds(name)
        print(f"[data] {name:<10} {start.date()} → {end.date()}")
    return prices, split_dates


def run_cointegration_stage(prices: pd.DataFrame, split_dates: SplitDates) -> tuple[list[str], dict]:
    """Etapa 2: embudo de selección sobre ambos universos (solo train) y Johansen del grupo elegido.

    Escribe selection_table.csv, johansen_summary.json, vector_comparison.csv, rolling_eigenvector.parquet, las
    figuras 1 y 4 y prices.parquet (los 4 activos elegidos con la columna split, para las etapas siguientes).
    Retorna (tickers del grupo, β normalizado por ticker).
    """
    train = slice_split(prices, split_dates, "train")
    table = run_funnel(train, UNIVERSES)
    chosen = table.loc[table["chosen"]].iloc[0]
    tickers = chosen["group"].split("-")

    summary, comparison = describe_chosen_group(train, tickers, chosen["universe"])
    if summary["anchor"] != ANCHOR_TICKER:
        raise ValueError(f"La pata ancla calculada ({summary['anchor']}) no coincide con ANCHOR_TICKER ({ANCHOR_TICKER})")
    summary["multiple_testing"] = multiple_testing_summary(table)

    # Johansen móvil en toda la muestra: cada ventana usa solo datos pasados (diagnóstico, no selección).
    rolling = rolling_first_eigenvector(np.log(prices[tickers]), summary["k_ar_diff"], summary["anchor"])
    rolling = add_split_column(rolling, split_dates)

    # prices.parquet (contrato de la etapa de datos): precios limpios de los 4 activos elegidos + columna split.
    group_prices = add_split_column(prices[tickers], split_dates)
    group_prices.to_parquet(ARTIFACTS / "prices.parquet")
    round_floats(table).to_csv(ARTIFACTS / "selection_table.csv", index=False)
    round_floats(comparison).to_csv(ARTIFACTS / "vector_comparison.csv", index=False)
    round_floats(rolling).to_parquet(ARTIFACTS / "rolling_eigenvector.parquet")
    (ARTIFACTS / "johansen_summary.json").write_text(json_text(summary))
    fig = plot_rolling_eigenvector(rolling, tickers, summary["anchor"], ROLLING_WINDOW,
                                   FIGURES / "fig04_eigenvector_movil.png")
    plt.close(fig)  # solo se guarda; main.py no abre ventanas
    # Figura 1 (parte 01): requiere el grupo elegido, por eso se genera aquí.
    fig = plot_normalized_prices(group_prices[tickers], group_prices["split"],
                                 f"Figura 1 — Precios ajustados del grupo {'-'.join(tickers)}",
                                 FIGURES / "fig01_precios_grupo.png")
    plt.close(fig)

    total = summary["multiple_testing"]["total"]
    print(f"[cointegration] {total['groups_tested']} grupos probados; Johansen rechaza r = 0 en "
          f"{total['johansen_reject_95']} (esperados por azar: {total['expected_false_positives_95']:.1f}); "
          f"sobreviven {total['survive_all_stages']}")
    print(f"[cointegration] grupo elegido ({summary['universe']}): {'-'.join(tickers)}, "
          f"traza {summary['trace'][0]['stat']:.1f} vs {summary['trace'][0]['cv95']:.1f} (95 %), r̂ = {summary['rank_trace']}")
    beta_text = ", ".join(f"{t} {b:+.3f}" for t, b in summary["beta_normalized"].items())
    print(f"[cointegration] β̃ = ({beta_text}); ADF p = {summary['spread_adf_pvalue']:.4f}, "
          f"vida media {summary['half_life_days']:.1f} días")
    return tickers, summary["beta_normalized"]


def run_weights_filter_stage(prices: pd.DataFrame, split_dates: SplitDates, summary: dict) -> tuple[pd.DataFrame, dict]:
    """Etapa 3a: filtro de Kalman 1 (pesos dinámicos β̂_t) sobre toda la muestra, calibrado solo con train.

    Escribe kf1_weights.parquet, las figuras 3 y 5 (parte del filtro 1) y la comparación de ECT estático vs dinámico. Retorna (kf1, parámetros del filtro 1).
    """
    tickers, anchor = summary["tickers"], summary["anchor"]
    beta = np.array([summary["beta_normalized"][t] for t in tickers])
    intercept = summary["intercept_c"]
    log_prices = np.log(prices[tickers])
    train = slice_split(log_prices, split_dates, "train")

    # R = varianza de los residuales de Johansen en train; q por separación de escalas (ver calibrate_q).
    residual_var = float(static_ect(train, beta, intercept).var(ddof=0))
    q = calibrate_q(train, anchor, beta, intercept, residual_var, summary["half_life_days"])

    kf1 = run_weights_filter(log_prices, anchor, beta, intercept, q, residual_var)
    kf1["ect_static"] = static_ect(log_prices, beta, intercept)
    kf1 = add_split_column(kf1, split_dates)
    train_absorption = kf1.loc[(kf1["split"] == "train") & ~kf1["burn_in"], "absorption"]
    params = {
        "q": q, "Q": f"q · I ({len(tickers)}×{len(tickers)})", "R": residual_var, "q_over_R": q / residual_var,
        "P0": f"{BURN_IN} · Q", "burn_in_days": BURN_IN, "state": ["c"] + [t for t in tickers if t != anchor],
        "anchor": anchor, "beta0": summary["beta_normalized"], "intercept0": intercept,
        "absorption_median_train": float(train_absorption.median()),
        "absorbed_in_trade_train": absorbed_fraction(train_absorption, summary["half_life_days"]),
        "ect": "dinámico = innovación con pesos prior (ỹ_t); estático = β̃ᵀ ln P_t − c con Johansen de train",
    }

    round_floats(kf1).to_parquet(ARTIFACTS / "kf1_weights.parquet")
    fig = plot_dynamic_weights(kf1, tickers, anchor, summary["beta_normalized"], FIGURES / "fig03_pesos_dinamicos.png")
    plt.close(fig)
    fig = plot_kalman_gains(kf1, params["state"], path=FIGURES / "fig05_ganancia_kalman.png")
    plt.close(fig)
    fig = plot_ect_comparison(kf1, FIGURES / "ect_estatico_vs_dinamico.png")
    plt.close(fig)

    last = kf1.iloc[-1]
    print(f"[kalman-1] q = {q:.3e}, R = {residual_var:.3e} (q/R = {q / residual_var:.2e}), burn-in {BURN_IN} días; "
          f"absorbe {params['absorbed_in_trade_train']:.0%} de una desviación en una operación típica (train)")
    print(f"[kalman-1] β̂ al final: " + ", ".join(f"{t} {last[f'beta_{t}']:+.3f}" for t in tickers))
    return kf1, params


def main() -> None:
    np.random.seed(SEED)
    ARTIFACTS.mkdir(exist_ok=True)
    prices, split_dates = run_data_stage()
    tickers, beta = run_cointegration_stage(prices, split_dates)
    summary = json.loads((ARTIFACTS / "johansen_summary.json").read_text())
    kf1, kf1_params = run_weights_filter_stage(prices, split_dates, summary)

    # params.json: parámetros de cada etapa (el filtro 2 y la estrategia agregan sus llaves).
    params = {"seed": SEED, "kf1": kf1_params}
    (ARTIFACTS / "params.json").write_text(json_text(params))
    # Las siguientes etapas se conectan aquí conforme se implementan.


if __name__ == "__main__":
    main()
