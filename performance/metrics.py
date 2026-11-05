"""Métricas de desempeño (parte 07). Por ahora solo el Sharpe, que necesita el grid search de la parte 05.

Convenciones: rendimientos diarios simples netos de costos; anualización con TRADING_DAYS; tasa libre de riesgo
RISK_FREE_RATE anual (0: el efectivo del backtest no genera intereses, `docs/decisiones.md`).
"""

import numpy as np
import pandas as pd

# --- Parámetros de este módulo (tabla de parámetros en CLAUDE.md) ---
TRADING_DAYS = 252
RISK_FREE_RATE = 0.0


def sharpe(returns: pd.Series, risk_free: float = RISK_FREE_RATE, periods: int = TRADING_DAYS) -> float:
    """Sharpe anualizado: √periods · media(r_t − r_f / periods) / desv(r_t), con desviación muestral (ddof = 1).

    Retorna NaN si la serie no tiene variación (p. ej. nunca hubo posición).
    """
    excess = returns - risk_free / periods
    sd = excess.std(ddof=1)
    if not np.isfinite(sd) or sd == 0:
        return float("nan")
    return float(np.sqrt(periods) * excess.mean() / sd)
