"""Embudo de selección del grupo de 4 activos (§3.2 del enunciado + etapa 7 de la sesión 14).

Un solo código para ambos universos. Todo se calcula **solo con entrenamiento**. Para cada grupo de 4 se
calculan todos los estadísticos (aunque el grupo se descarte antes), para que `selection_table.csv` sea completa
y la discusión de pruebas múltiples tenga números.

Etapas (criterio fijado antes de correr, ver `docs/decisiones.md`):
    1. Universo con justificación económica (`universe.py`)               → define los candidatos
    2. Correlación móvil de rendimientos: media por pares > 0.7            → ELIMINA
    3. Engle–Granger (pares y grupo)                                       → solo PRIORIZA
    4. Johansen: la traza rechaza r = 0 al 95 %                            → ELIMINA
    5. Selección del vector: entre las r̂ columnas, vida media operable y menor p ADF
    6. Validación del spread: ADF p < 0.05 y vida media en [5, 60] días    → ELIMINA
    7. Estabilidad: Johansen en cada mitad de train                        → se reporta, no elimina
Grupos: pares, tercias y cuartetos (`GROUP_SIZES`) del universo activo (iteración 2, solo oro).

Elección final (iteración 2): el grupo `CHOSEN_GROUP`, que debe sobrevivir al embudo. En la iteración 1 la regla era
"el sobreviviente con mayor LR_trace(0) / v.c. 95 %" (GLD-GDX-AEM-FNV); ese grupo perdió la cointegración en
validación y, tras el proceso de búsqueda documentado en `docs/decisiones.md`, se eligió GLD-GDX-B: GDX es el ETF de
mineras y Barrick una de sus posiciones más grandes, así que el metal, el ETF y su mayor componente comparten la
tendencia casi de forma mecánica. La columna `trace_rank` muestra dónde queda cada grupo por la regla original.
"""

from itertools import combinations

import numpy as np
import pandas as pd

from cointegration.correlation import group_correlation, pair_name, rolling_pairwise_correlation
from cointegration.engle_granger import best_engle_granger, pairwise_engle_granger
from cointegration.half_life import compute_half_life
from cointegration.johansen import (CV_COLUMN, DET_ORDER, SIGN_CONVENTION, SIGNIFICANCE, adf_pvalue, anchor_index,
                                    build_spread, choose_vector, compare_vectors, normalize_beta, run_johansen,
                                    select_k_ar_diff)

# --- Parámetros de este módulo (tabla de parámetros en CLAUDE.md) ---
CORR_THRESHOLD = 0.70
CORR_WINDOW = 252
PVALUE_THRESHOLD = 0.05
HALF_LIFE_RANGE = (5.0, 60.0)  # días; rango "operable" sugerido en clase
GROUP_SIZES = (2, 3, 4)  # iteración 2: pares, tercias y cuartetos (iteración 1: solo 4)
CHOSEN_GROUP = ("GLD", "GDX", "B")  # iteración 2 (ver docstring del módulo y docs/decisiones.md)


def check_integration_order(log_prices: pd.DataFrame, pvalue_threshold: float = PVALUE_THRESHOLD) -> pd.DataFrame:
    """Verifica que cada serie sea I(1): ADF en niveles no rechaza y ADF en diferencias sí rechaza.

    Retorna:
        DataFrame indexado por ticker con `adf_pvalue_level`, `adf_pvalue_diff` e `is_I1`. Se reporta, no elimina.
    """
    rows = {}
    for ticker in log_prices.columns:
        _, p_level = adf_pvalue(log_prices[ticker])
        _, p_diff = adf_pvalue(log_prices[ticker].diff())
        rows[ticker] = {"adf_pvalue_level": p_level, "adf_pvalue_diff": p_diff,
                        "is_I1": p_level >= pvalue_threshold and p_diff < pvalue_threshold}
    return pd.DataFrame.from_dict(rows, orient="index")


def _discard_stage(row: dict) -> tuple[str, str]:
    """Primera etapa eliminatoria que el grupo no pasa y su motivo; ('', '') si sobrevive."""
    if row["corr_mean"] <= CORR_THRESHOLD:
        return "2_correlacion", f"correlación media {row['corr_mean']:.3f} ≤ {CORR_THRESHOLD}"
    if row["rank_trace"] == 0:
        return "4_johansen", (f"traza no rechaza r = 0 al 95 % ({row['trace_0']:.1f} ≤ {row['trace_cv95_0']:.1f})")
    if row["chosen_vector"] is None:
        return "6_validacion", "ningún vector del rango tiene vida media en [5, 60] días"
    if row["spread_adf_pvalue"] >= PVALUE_THRESHOLD:
        return "6_validacion", f"ADF del spread p = {row['spread_adf_pvalue']:.3f} ≥ {PVALUE_THRESHOLD}"
    return "", ""


def evaluate_group(universe: str, tickers: list[str], log_prices: pd.DataFrame, rolling_corr: pd.DataFrame,
                   pair_eg: pd.DataFrame) -> dict:
    """Calcula todos los estadísticos del embudo para un grupo (una fila de `selection_table.csv`).

    Parámetros:
        universe: nombre del universo del grupo.
        tickers: los 4 activos, en el orden del universo.
        log_prices: log-precios de entrenamiento del universo.
        rolling_corr: correlación móvil por pares del universo (de `rolling_pairwise_correlation`).
        pair_eg: Engle–Granger por pares del universo (de `pairwise_engle_granger`).
    Retorna:
        dict con estadísticos de las etapas 2–7, `discard_stage` y `discard_reason`.
    """
    prices = log_prices[tickers]
    row = {"universe": universe, "group": "-".join(tickers)}

    # Etapa 2: correlación.
    row.update(group_correlation(rolling_corr, tickers, CORR_THRESHOLD))

    # Etapa 3: Engle–Granger (prioriza).
    pairs = {pair_name(a, b) for a, b in combinations(tickers, 2)}
    in_group = pair_eg[(pair_eg["asset_1"] + "-" + pair_eg["asset_2"]).isin(pairs)]
    eg = best_engle_granger(prices)
    row.update({
        "eg_significant_pairs": int((in_group["pvalue_min"] < PVALUE_THRESHOLD).sum()),
        "eg_group_dependent": eg.dependent,
        "eg_group_intercept": eg.intercept,
        "eg_group_hedge_ratios": ";".join(f"{t}={h:.4f}" for t, h in zip(eg.regressors, eg.hedge_ratios)),
        "eg_group_adf_stat": eg.adf_stat,
        "eg_group_pvalue": eg.pvalue,
        "eg_group_r2": eg.r_squared,
        "eg_group_dw": eg.durbin_watson,
        "eg_group_spurious_flag": eg.spurious_flag,
    })

    # Etapa 4: Johansen.
    k_ar_diff = select_k_ar_diff(prices)
    joh = run_johansen(prices, k_ar_diff)
    cv95, cv99 = CV_COLUMN[SIGNIFICANCE], CV_COLUMN[0.99]
    row.update({
        "k_ar_diff": k_ar_diff,
        "eigenvalue_1": float(joh.eigenvalues[0]),
        "trace_0": float(joh.trace_stats[0]),
        "trace_cv95_0": float(joh.trace_cv[0, cv95]),
        "trace_cv99_0": float(joh.trace_cv[0, cv99]),
        "trace_ratio": joh.trace_ratio,
        "maxeig_0": float(joh.maxeig_stats[0]),
        "maxeig_cv95_0": float(joh.maxeig_cv[0, cv95]),
        "rank_trace": joh.rank("trace"),
        "rank_maxeig": joh.rank("maxeig"),
        "rank_trace_99": joh.rank("trace", 0.99),
    })

    # Etapas 5 y 6: selección y validación del vector (para grupos con r̂ = 0 se reporta el primer vector, informativo).
    comparison = compare_vectors(prices, joh, HALF_LIFE_RANGE, PVALUE_THRESHOLD)
    chosen = choose_vector(comparison)
    shown = comparison.iloc[(chosen or 1) - 1]
    row.update({
        "chosen_vector": chosen,
        "spread_adf_pvalue": float(shown["adf_pvalue"]),
        "half_life": float(shown["half_life"]),
    })

    # Etapa 7: estabilidad en las dos mitades de entrenamiento (mismo k).
    half = len(prices) // 2
    row["rank_trace_first_half"] = run_johansen(prices.iloc[:half], k_ar_diff).rank("trace")
    row["rank_trace_second_half"] = run_johansen(prices.iloc[half:], k_ar_diff).rank("trace")

    row["discard_stage"], row["discard_reason"] = _discard_stage(row)
    return row


def run_funnel(train_prices: pd.DataFrame, universes: dict, group_sizes: tuple[int, ...] = GROUP_SIZES,
               chosen_group: tuple[str, ...] = CHOSEN_GROUP) -> pd.DataFrame:
    """Corre el embudo sobre todos los grupos de cada tamaño de `group_sizes` en cada universo.

    Parámetros:
        train_prices: precios (no log) de ENTRENAMIENTO de todos los tickers.
        universes: dict nombre → {"tickers": [...]} (de `cointegration.universe.active_universes()`).
        chosen_group: grupo elegido; debe sobrevivir a todas las etapas o se lanza un error.
    Retorna:
        `selection_table`: una fila por grupo probado (con solo oro: C(8,2) + C(8,3) + C(8,4) = 154), con `size`,
        `trace_rank` (posición por LR_trace(0) / v.c. 95 % entre los sobrevivientes) y `chosen`.
    """
    rows = []
    for name, spec in universes.items():
        log_prices = np.log(train_prices[spec["tickers"]])
        rolling_corr = rolling_pairwise_correlation(log_prices.diff().dropna(), CORR_WINDOW)
        pair_eg = pairwise_engle_granger(log_prices)
        for size in group_sizes:
            for group in combinations(spec["tickers"], size):
                rows.append({"size": size, **evaluate_group(name, list(group), log_prices, rolling_corr, pair_eg)})
    table = pd.DataFrame(rows)
    table["survives"] = table["discard_stage"] == ""
    table["trace_rank"] = table["trace_ratio"].where(table["survives"]).rank(ascending=False, method="min")
    table["chosen"] = table["group"] == "-".join(chosen_group)
    if not table.loc[table["chosen"], "survives"].all() or not table["chosen"].any():
        raise ValueError(f"El grupo elegido {chosen_group} no sobrevive al embudo de selección")
    return table


def multiple_testing_summary(table: pd.DataFrame, alpha: float = 1 - SIGNIFICANCE) -> dict:
    """Números para la discusión de pruebas múltiples, por universo, por tamaño de grupo (`by_size`) y en total.

    Retorna:
        dict con, por universo y `total`: grupos probados, cuántos rechazan r = 0 al 95 % y al 99 %, cuántos se
        esperarían al azar (α · N) si nada estuviera cointegrado, cuántos sobreviven todas las etapas y el nivel
        de Bonferroni α / N (referencia: con tablas al 99 % no se puede probar un nivel tan estricto).
    """
    def summarize(df: pd.DataFrame) -> dict:
        n = len(df)
        return {
            "groups_tested": n,
            "johansen_reject_95": int((df["rank_trace"] > 0).sum()),
            "johansen_reject_99": int((df["rank_trace_99"] > 0).sum()),
            "expected_false_positives_95": alpha * n,
            "pass_correlation": int((df["corr_mean"] > CORR_THRESHOLD).sum()),
            "survive_all_stages": int(df["survives"].sum()),
            "bonferroni_alpha": alpha / n,
        }

    summary = {name: summarize(df) for name, df in table.groupby("universe", sort=False)}
    summary["by_size"] = {int(size): summarize(df) for size, df in table.groupby("size", sort=True)}
    summary["total"] = summarize(table)
    return summary


def describe_chosen_group(train_prices: pd.DataFrame, tickers: list[str], universe: str) -> tuple[dict, pd.DataFrame]:
    """Johansen completo del grupo elegido: contenido de `johansen_summary.json` y `vector_comparison.csv`.

    Parámetros:
        train_prices: precios (no log) de ENTRENAMIENTO.
        tickers: los 4 activos elegidos.
        universe: universo al que pertenecen.
    Retorna:
        (summary, comparison): `summary` con estadísticos de traza y máximo eigenvalor, valores críticos, rango,
        vector elegido, β crudo y normalizado, pata ancla, constante c = media de β̃ᵀ ln P_t en train, ADF y
        vida media del spread y la verificación I(1) de cada activo; `comparison` con ADF y vida media de cada
        eigenvector.
    """
    log_prices = np.log(train_prices[tickers])
    k_ar_diff = select_k_ar_diff(log_prices)
    joh = run_johansen(log_prices, k_ar_diff)
    comparison = compare_vectors(log_prices, joh, HALF_LIFE_RANGE, PVALUE_THRESHOLD)
    vector = choose_vector(comparison)
    raw = joh.eigenvectors[:, vector - 1]
    anchor = anchor_index(raw)
    beta = normalize_beta(raw, anchor)
    spread = build_spread(log_prices, beta)
    adf_stat, adf_p = adf_pvalue(spread)

    def stats_table(stats: np.ndarray, cv: np.ndarray) -> list[dict]:
        return [{"r0": r0, "stat": float(s), "cv90": float(c[0]), "cv95": float(c[1]), "cv99": float(c[2]),
                 "reject_95": bool(s > c[1])} for r0, (s, c) in enumerate(zip(stats, cv))]

    summary = {
        "universe": universe,
        "tickers": tickers,
        "train_start": log_prices.index[0].strftime("%Y-%m-%d"),
        "train_end": log_prices.index[-1].strftime("%Y-%m-%d"),
        "n_obs": joh.n_obs,
        "prices": "log",
        "det_order": DET_ORDER,
        "k_ar_diff": k_ar_diff,
        "k_selection": "BIC sobre VAR en log-niveles; k_ar_diff = p - 1 (mínimo 1)",
        "eigenvalues": joh.eigenvalues.tolist(),
        "trace": stats_table(joh.trace_stats, joh.trace_cv),
        "max_eigen": stats_table(joh.maxeig_stats, joh.maxeig_cv),
        "rank_trace": joh.rank("trace"),
        "rank_maxeig": joh.rank("maxeig"),
        "chosen_vector": vector,
        "beta_raw": dict(zip(tickers, raw.tolist())),
        "beta_normalized": dict(zip(tickers, beta.tolist())),
        "anchor": tickers[anchor],
        "sign_convention": SIGN_CONVENTION,
        "intercept_c": float(spread.mean()),
        "spread_adf_stat": adf_stat,
        "spread_adf_pvalue": adf_p,
        "half_life_days": compute_half_life(spread),
        "integration_order": {
            t: {"adf_pvalue_level": float(r["adf_pvalue_level"]), "adf_pvalue_diff": float(r["adf_pvalue_diff"]),
                "is_I1": bool(r["is_I1"])}
            for t, r in check_integration_order(log_prices).iterrows()
        },
    }
    return summary, comparison
