"""Prueba de Johansen, selección y normalización del vector cointegrante (sesión 14).

VECM: ΔP_t = Π P_{t−1} + Σ Γ_i ΔP_{t−i} + ε_t, con P_t = log-precios. Johansen estima por máxima verosimilitud
los eigenvalores λ̂_1 ≥ … ≥ λ̂_n y sus eigenvectores (columnas de β). El rango r de Π = αβᵀ se estima con la
secuencia de pruebas de traza (y de máximo eigenvalor como confirmación): el primer r₀ que no se rechaza es r̂.

Convención de normalización (requisito del enunciado, §3.3):
- Pata ancla j = argmax_i |β_i| del vector elegido en entrenamiento.
- β̃ = β / β_j, así que β̃_j = +1. Una sola división fija escala y signo.
- Con β̃ fijo: largo el spread = comprar los activos con β̃_i > 0 y vender los de β̃_i < 0.
"""

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.vector_ar.vecm import coint_johansen

from cointegration.half_life import compute_half_life

# --- Parámetros de este módulo (ver docs/decisiones.md) ---
DET_ORDER = 0  # constante en la relación de largo plazo (ECT = βᵀP − c)
MAX_VAR_LAGS = 10  # máximo de rezagos del VAR en niveles para elegir k por BIC
CV_COLUMN = {0.90: 0, 0.95: 1, 0.99: 2}  # columnas de los valores críticos de statsmodels
SIGNIFICANCE = 0.95
ROLLING_WINDOW = 504  # ≈ 2 años bursátiles (Johansen móvil, figura 4)
ROLLING_STEP = 21  # ≈ 1 mes

# Pata de normalización y signo, declaradas tras correr Johansen en entrenamiento sobre el grupo elegido
# (GLD-GDX-AEM-FNV): GLD tiene el mayor |β_i| del primer eigenvector. main.py verifica que el ancla calculada
# coincida con esta constante; si los datos cambian y deja de coincidir, el pipeline se detiene.
ANCHOR_TICKER = "GLD"
SIGN_CONVENTION = "beta_anchor = +1 (largo el spread = comprar los activos con beta > 0, vender los de beta < 0)"


@dataclass(frozen=True)
class JohansenResult:
    """Salida de la prueba de Johansen para un grupo.

    Atributos:
        tickers: orden de los activos (filas de `eigenvectors`).
        k_ar_diff: rezagos en diferencias del VECM.
        eigenvalues: λ̂_1 ≥ … ≥ λ̂_n.
        eigenvectors: matriz n × n; la columna i es el vector cointegrante asociado a λ̂_i (sin normalizar).
        trace_stats, maxeig_stats: LR_trace(r₀) y LR_max(r₀) para r₀ = 0, …, n − 1.
        trace_cv, maxeig_cv: valores críticos n × 3 (columnas 90 %, 95 %, 99 %).
        n_obs: observaciones usadas.
    """

    tickers: tuple[str, ...]
    k_ar_diff: int
    eigenvalues: np.ndarray
    eigenvectors: np.ndarray
    trace_stats: np.ndarray
    trace_cv: np.ndarray
    maxeig_stats: np.ndarray
    maxeig_cv: np.ndarray
    n_obs: int

    def rank(self, test: str = "trace", level: float = SIGNIFICANCE) -> int:
        """Rango estimado r̂ con la prueba `test` ∈ {'trace', 'maxeig'} al nivel `level`."""
        stats, cv = (self.trace_stats, self.trace_cv) if test == "trace" else (self.maxeig_stats, self.maxeig_cv)
        return estimate_rank(stats, cv[:, CV_COLUMN[level]])

    @property
    def trace_ratio(self) -> float:
        """LR_trace(0) / valor crítico al 95 %: fuerza de la evidencia contra 'no hay cointegración'."""
        return float(self.trace_stats[0] / self.trace_cv[0, CV_COLUMN[SIGNIFICANCE]])


def estimate_rank(stats: np.ndarray, critical_values: np.ndarray) -> int:
    """Secuencia de Johansen: prueba r₀ = 0, 1, … y devuelve el primer r₀ que NO se rechaza.

    Si se rechazan todas, devuelve n (todas las series serían estacionarias).
    """
    for r0, (stat, cv) in enumerate(zip(stats, critical_values)):
        if stat <= cv:
            return r0
    return len(stats)


def select_k_ar_diff(log_prices: pd.DataFrame, max_lags: int = MAX_VAR_LAGS) -> int:
    """Elige k_ar_diff = p − 1, con p el orden del VAR en log-niveles que minimiza el BIC.

    Retorna:
        k_ar_diff ≥ 1 (si BIC elige p = 1 se usa 1, para que el VECM tenga dinámica de corto plazo).
    """
    p = VAR(log_prices.to_numpy()).select_order(maxlags=max_lags).selected_orders["bic"]
    return max(int(p) - 1, 1)


def _as_real(values) -> np.ndarray:
    """Convierte a real la salida de statsmodels, verificando que la parte imaginaria sea ruido numérico."""
    values = np.asarray(values)
    if np.iscomplexobj(values):
        if np.max(np.abs(values.imag)) > 1e-8:
            raise ValueError("Johansen devolvió eigenvalores/eigenvectores con parte imaginaria no despreciable")
        values = values.real
    return values.astype(float)


def run_johansen(log_prices: pd.DataFrame, k_ar_diff: int, det_order: int = DET_ORDER) -> JohansenResult:
    """Corre `coint_johansen` de statsmodels y empaqueta el resultado.

    Parámetros:
        log_prices: log-precios (solo entrenamiento cuando se usa para seleccionar).
        k_ar_diff: rezagos en diferencias (de `select_k_ar_diff`).
        det_order: 0 = constante.
    Retorna:
        JohansenResult; statsmodels ya ordena eigenvalores y eigenvectores de mayor a menor.
    """
    # statsmodels resuelve un problema de eigenvalores generalizado y puede devolver tipo complejo con parte
    # imaginaria nula; al guardar sus estadísticos la descarta y avisa. `_as_real` verifica que sea ruido numérico.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", np.exceptions.ComplexWarning)
        res = coint_johansen(log_prices.to_numpy(), det_order, k_ar_diff)
    return JohansenResult(
        tickers=tuple(log_prices.columns),
        k_ar_diff=k_ar_diff,
        eigenvalues=_as_real(res.eig),
        eigenvectors=_as_real(res.evec),
        trace_stats=_as_real(res.lr1),
        trace_cv=_as_real(res.cvt),
        maxeig_stats=_as_real(res.lr2),
        maxeig_cv=_as_real(res.cvm),
        n_obs=len(log_prices),
    )


def anchor_index(beta: np.ndarray) -> int:
    """Índice de la pata ancla: el activo con mayor |β_i|."""
    return int(np.argmax(np.abs(beta)))


def normalize_beta(beta: np.ndarray, anchor: int) -> np.ndarray:
    """β̃ = β / β_anchor: fija escala y signo con una sola división (β̃_anchor = +1).

    Es invariante a reescalar el eigenvector: normalize_beta(c·β) = normalize_beta(β) para todo c ≠ 0.
    """
    beta = np.asarray(beta, dtype=float)
    return beta / beta[anchor]


def build_spread(log_prices: pd.DataFrame, beta: np.ndarray) -> pd.Series:
    """Spread del portafolio S_t = βᵀ ln P_t (sin restar la constante c)."""
    return pd.Series(log_prices.to_numpy() @ np.asarray(beta), index=log_prices.index, name="spread")


def adf_pvalue(series: pd.Series) -> tuple[float, float]:
    """ADF con constante y rezagos por AIC. Retorna (estadístico, p-value).

    Ojo: sobre un spread cuyo β se estimó con los mismos datos, el p-value estándar es optimista (igual que en
    Engle–Granger); por eso Johansen, y no este ADF, es la prueba de cointegración.
    """
    stat, pvalue, *_ = adfuller(pd.Series(series).dropna(), regression="c", autolag="AIC",
                                result_object=False)
    return float(stat), float(pvalue)


def compare_vectors(log_prices: pd.DataFrame, result: JohansenResult, half_life_range: tuple[float, float],
                    pvalue_threshold: float) -> pd.DataFrame:
    """Construye el spread de cada eigenvector y evalúa ADF y vida media (tabla comparativa del enunciado).

    Retorna:
        DataFrame con una fila por columna de β: `vector` (1 = mayor eigenvalor), `eigenvalue`, `in_rank`
        (columna dentro del rango r̂ por traza), `anchor`, β normalizado por activo (`beta_<ticker>`),
        `adf_stat`, `adf_pvalue`, `half_life`, `operable` (vida media en rango) y `valid` (operable y ADF < umbral).
    """
    rank = result.rank("trace")
    lo, hi = half_life_range
    rows = []
    for i in range(len(result.eigenvalues)):
        raw = result.eigenvectors[:, i]
        anchor = anchor_index(raw)
        beta = normalize_beta(raw, anchor)
        spread = build_spread(log_prices, beta)
        stat, pvalue = adf_pvalue(spread)
        half_life = compute_half_life(spread)
        operable = lo <= half_life <= hi
        rows.append({
            "vector": i + 1,
            "eigenvalue": float(result.eigenvalues[i]),
            "in_rank": i < rank,
            "anchor": result.tickers[anchor],
            **{f"beta_{t}": float(b) for t, b in zip(result.tickers, beta)},
            "adf_stat": stat,
            "adf_pvalue": pvalue,
            "half_life": half_life,
            "operable": operable,
            "valid": operable and pvalue < pvalue_threshold,
        })
    return pd.DataFrame(rows)


def choose_vector(comparison: pd.DataFrame) -> int | None:
    """Elige el vector: entre las columnas dentro del rango con vida media operable, la de menor p-value ADF.

    En empate de p-value gana la de mayor eigenvalor (la tabla ya viene ordenada así).
    Retorna:
        Número de vector (1-indexado) o None si ninguna columna del rango es operable.
    """
    candidates = comparison[comparison["in_rank"] & comparison["operable"]]
    if candidates.empty:
        return None
    best = candidates.sort_values(["adf_pvalue", "eigenvalue"], ascending=[True, False]).iloc[0]
    return int(best["vector"])


def rolling_first_eigenvector(log_prices: pd.DataFrame, k_ar_diff: int, anchor: str,
                              window: int = ROLLING_WINDOW, step: int = ROLLING_STEP) -> pd.DataFrame:
    """Johansen móvil: primer eigenvector normalizado sobre la misma pata ancla, ventana hacia atrás.

    Parámetros:
        log_prices: log-precios de los activos del grupo (puede ser toda la muestra: cada ventana solo usa
            datos hasta su fecha final, así que no hay look-ahead).
        k_ar_diff: fijo, el elegido en entrenamiento.
        anchor: ticker de la pata ancla (el de entrenamiento), para que todas las ventanas sean comparables.
        window, step: tamaño y paso de la ventana en días.
    Retorna:
        DataFrame indexado por la fecha final de cada ventana (`date`) con β̃ por activo, `eigenvalue_1`,
        `trace_0`, `trace_cv95_0`, `rank_trace` y `window_start`.
    """
    anchor_pos = list(log_prices.columns).index(anchor)
    rows = []
    for end in range(window, len(log_prices) + 1, step):
        chunk = log_prices.iloc[end - window:end]
        res = run_johansen(chunk, k_ar_diff)
        beta = normalize_beta(res.eigenvectors[:, 0], anchor_pos)
        rows.append({
            "date": chunk.index[-1],
            **dict(zip(log_prices.columns, beta)),
            "eigenvalue_1": float(res.eigenvalues[0]),
            "trace_0": float(res.trace_stats[0]),
            "trace_cv95_0": float(res.trace_cv[0, CV_COLUMN[SIGNIFICANCE]]),
            "rank_trace": res.rank("trace"),
            "window_start": chunk.index[0],
        })
    return pd.DataFrame(rows).set_index("date")


def summarize_rolling(rolling: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Resume el Johansen móvil por partición: mediana y desviación de cada β̃ y fracción de ventanas con r̂ ≥ 1.

    Parámetros:
        rolling: salida de `rolling_first_eigenvector` con la columna `split` agregada.
        tickers: activos del grupo.
    Retorna:
        DataFrame indexado por partición (en orden cronológico).
    """
    grouped = rolling.groupby("split", sort=False)
    summary = pd.concat({
        **{f"{t}_median": grouped[t].median() for t in tickers},
        **{f"{t}_std": grouped[t].std() for t in tickers},
        "frac_windows_rank_ge_1": grouped["rank_trace"].apply(lambda r: float((r > 0).mean())),
        "n_windows": grouped.size(),
    }, axis=1)
    return summary
