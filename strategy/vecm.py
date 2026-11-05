"""VECM en entrenamiento con el vector de Johansen como término de corrección de error (sesión 14).

    ΔP_t = α (βᵀP_{t−1} − c) + Σ_{i=1}^{k} Γ_i ΔP_{t−i} + ε_t        (P_t = log-precios)

Premultiplicando por βᵀ: ΔS_t ≈ (βᵀα) S_{t−1} + …, así que hay corrección hacia el equilibrio si −2 < βᵀα < 0 y la
vida media implícita es −ln 2 / ln(1 + βᵀα) (con −2 < βᵀα < −1 la corrección oscila y se usa |1 + βᵀα|).

Qué aporta el VECM al proyecto: α dice **qué activos corrigen** cuando el spread se abre, y βᵀα da una segunda
estimación de la velocidad de reversión. La serie que normaliza el filtro 2 no es ε_t, sino el ECT dinámico del
filtro 1 (aclaración del profesor, `docs/decisiones.md`).
"""

import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.vector_ar.vecm import VECM

# --- Parámetros de este módulo (tabla de parámetros en CLAUDE.md) ---
DETERMINISTIC = "co"  # constante sin restringir: el mismo caso que det_order = 0 de Johansen
COINT_RANK = 1  # r̂ de la parte 02
BETA_TOLERANCE = 1e-6  # el β del VECM debe ser el β̃ de Johansen


def fit_vecm(train_log_prices: pd.DataFrame, k_ar_diff: int, anchor: str, johansen_beta: dict) -> dict:
    """Estima el VECM en train y resume α, βᵀα y la vida media.

    Parámetros:
        train_log_prices: log-precios de los activos del grupo, **solo entrenamiento**.
        k_ar_diff: rezagos en diferencias (el de Johansen, por BIC).
        anchor: pata ancla de la normalización (β̃_anchor = +1).
        johansen_beta: β̃ de Johansen por ticker; se verifica que el VECM estime el mismo vector.
    Retorna:
        Diccionario con β̃, α (en la escala de β̃, con error estándar y t), βᵀα, si cumple −2 < βᵀα < 0, vida media
        y los activos con α significativo al 5 % (|t| > 1.96).
    Supuestos:
        statsmodels normaliza β con su primer elemento = 1. Se reescala a la pata ancla; Π = αβᵀ no cambia porque
        α se multiplica por el mismo factor.
    """
    tickers = list(train_log_prices.columns)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # avisos de frecuencia del índice de fechas, no afectan la estimación
        result = VECM(train_log_prices, k_ar_diff=k_ar_diff, coint_rank=COINT_RANK,
                      deterministic=DETERMINISTIC).fit()

    j = tickers.index(anchor)
    scale = result.beta[j, 0]
    beta = result.beta[:, 0] / scale
    alpha = result.alpha[:, 0] * scale
    alpha_se = result.stderr_alpha[:, 0] * abs(scale)
    expected = np.array([johansen_beta[t] for t in tickers])
    if not np.allclose(beta, expected, atol=BETA_TOLERANCE):
        raise ValueError(f"El β del VECM {beta} no coincide con el de Johansen {expected}")

    beta_alpha = float(beta @ alpha)
    corrects = -2 < beta_alpha < 0
    t_stats = alpha / alpha_se
    return {
        "tickers": tickers,
        "k_ar_diff": k_ar_diff,
        "coint_rank": COINT_RANK,
        "deterministic": DETERMINISTIC,
        "n_obs": int(result.nobs),
        "beta_normalized": dict(zip(tickers, beta.tolist())),
        "alpha": dict(zip(tickers, alpha.tolist())),
        "alpha_stderr": dict(zip(tickers, alpha_se.tolist())),
        "alpha_tstat": dict(zip(tickers, t_stats.tolist())),
        "alpha_significant_5pct": [t for t, s in zip(tickers, t_stats) if abs(s) > 1.96],
        "beta_alpha": beta_alpha,
        "error_correction": bool(corrects),
        "half_life_days": float(-np.log(2) / np.log(abs(1 + beta_alpha))) if corrects else float("inf"),
    }
