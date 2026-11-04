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
from data.split import SplitDates, compute_split_dates, label_split, save_split_dates, slice_split
from data.validate import JUMP_THRESHOLD, assert_valid, validate_prices
from performance.figures import plot_rolling_eigenvector

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


def run_data_stage() -> tuple[pd.DataFrame, SplitDates]:
    """Etapa 1: precios limpios y validados de todos los universos + fechas de corte congeladas."""
    raw = load_prices(all_tickers(), START_DATE, END_DATE, DATA_SNAPSHOT)
    prices, clean_report = clean_prices(raw)
    report = validate_prices(prices)
    assert_valid(report)
    split_dates = compute_split_dates(prices.index)

    save_split_dates(split_dates, ARTIFACTS / "split_dates.json")
    (ARTIFACTS / "validation_report.json").write_text(
        json.dumps({"cleaning": clean_report, "validation": report.to_dict()}, indent=2)
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

    Escribe selection_table.csv, johansen_summary.json, vector_comparison.csv, rolling_eigenvector.parquet y la
    figura 4. Retorna (tickers del grupo, β normalizado por ticker).
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
    rolling["split"] = label_split(rolling.index, split_dates)

    table.to_csv(ARTIFACTS / "selection_table.csv", index=False)
    comparison.to_csv(ARTIFACTS / "vector_comparison.csv", index=False)
    rolling.to_parquet(ARTIFACTS / "rolling_eigenvector.parquet")
    (ARTIFACTS / "johansen_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    fig = plot_rolling_eigenvector(rolling, tickers, summary["anchor"], ROLLING_WINDOW,
                                   FIGURES / "fig04_eigenvector_movil.png")
    plt.close(fig)  # solo se guarda; main.py no abre ventanas

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


def main() -> None:
    np.random.seed(SEED)
    ARTIFACTS.mkdir(exist_ok=True)
    prices, split_dates = run_data_stage()
    tickers, beta = run_cointegration_stage(prices, split_dates)
    # Las siguientes etapas se conectan aquí conforme se implementan.


if __name__ == "__main__":
    main()
