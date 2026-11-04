"""Correlación móvil por pares sobre rendimientos (etapa 2 del embudo).

Es solo una heurística (correlación ≠ cointegración, sesión 12): sirve para descartar grupos cuyos activos no se
mueven juntos día a día. Se calcula sobre **rendimientos** log, no sobre precios: la correlación de dos series I(1)
es alta casi siempre aunque no estén relacionadas (regresión espuria).
"""

from itertools import combinations

import numpy as np
import pandas as pd


def pair_name(a: str, b: str) -> str:
    """Nombre de columna de un par, en el orden en que aparecen los activos ('A-B')."""
    return f"{a}-{b}"


def rolling_pairwise_correlation(log_returns: pd.DataFrame, window: int) -> pd.DataFrame:
    """Correlación móvil de cada par de columnas con una ventana hacia atrás de `window` días.

    Parámetros:
        log_returns: rendimientos log diarios (una columna por activo).
        window: tamaño de la ventana (252 ≈ un año bursátil).
    Retorna:
        DataFrame con el mismo índice y una columna 'A-B' por par; las primeras `window − 1` filas son NaN.
    Supuestos:
        La ventana en t usa solo datos hasta t (rolling estándar de pandas): sin look-ahead.
    """
    return pd.DataFrame({
        pair_name(a, b): log_returns[a].rolling(window).corr(log_returns[b])
        for a, b in combinations(log_returns.columns, 2)
    })


def group_correlation(rolling_corr: pd.DataFrame, tickers: list[str], threshold: float) -> dict:
    """Resume la correlación móvil de un grupo con los pares que lo forman.

    Parámetros:
        rolling_corr: salida de `rolling_pairwise_correlation` sobre el universo completo.
        tickers: activos del grupo, en el orden del universo.
        threshold: umbral del filtro (0.7).
    Retorna:
        dict con
        - `corr_mean`: media de las correlaciones por pares, cada una promediada en el tiempo (esta es la
          cifra que se compara contra el umbral, como en la sesión 14);
        - `corr_min_pair`: la correlación media del par más débil;
        - `corr_frac_above`: fracción de días en que la media de los pares supera el umbral (estabilidad).
    """
    pairs = rolling_corr[[pair_name(a, b) for a, b in combinations(tickers, 2)]].dropna()
    pair_means = pairs.mean()
    daily_group_mean = pairs.mean(axis=1)
    return {
        "corr_mean": float(pair_means.mean()),
        "corr_min_pair": float(pair_means.min()),
        "corr_frac_above": float(np.mean(daily_group_mean > threshold)),
    }
