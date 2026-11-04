"""Vida media del spread: Ornstein–Uhlenbeck en tiempo discreto (sesión 12).

Modelo: Δs_t = λ (s_{t−1} − s̄) + ε_t, con λ < 0 si el spread revierte. Se estima por OLS como
Δs_t = a + λ s_{t−1} + ε_t (la constante absorbe −λ s̄) y la vida media es −ln 2 / λ: el número esperado de
días para que una desviación se reduzca a la mitad.

Nota: la guía 02 escribe −ln 2 / ln(φ) con φ = 1 + λ (el coeficiente del AR(1) en niveles). Para |λ| pequeño
ambas son casi iguales (ln(1 + λ) ≈ λ); usamos −ln 2 / λ porque es la fórmula de clase.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm


def estimate_ou_speed(spread: pd.Series) -> float:
    """Estima λ de Δs_t = a + λ s_{t−1} + ε_t por OLS.

    Parámetros:
        spread: serie del spread (en este proyecto, βᵀ ln P_t), sin NaN.
    Retorna:
        λ (por día). Negativo si el spread revierte a su media; ≥ 0 si no revierte.
    Supuestos:
        Usa solo la muestra que recibe; para no tener look-ahead, se le pasa únicamente entrenamiento.
    """
    spread = pd.Series(spread).dropna()
    lagged = spread.shift(1).iloc[1:]
    delta = spread.diff().iloc[1:]
    fit = sm.OLS(delta.to_numpy(), sm.add_constant(lagged.to_numpy())).fit()
    return float(fit.params[1])


def compute_half_life(spread: pd.Series) -> float:
    """Vida media del spread en días: −ln 2 / λ.

    Retorna:
        Vida media (> 0) si λ < 0; `inf` si el spread no revierte (λ ≥ 0), para que nunca pase el filtro de
        vida media operable.
    """
    speed = estimate_ou_speed(spread)
    if speed >= 0:
        return float("inf")
    return float(-np.log(2) / speed)
