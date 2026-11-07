"""Costos de operación del backtest (§3.8 del enunciado): comisión por pata y préstamo sobre los cortos.

- Comisión: 0.125 % del nocional operado en CADA pata, en cada operación (entrada, salida y cada rebalanceo).
  Un spread de n patas paga n comisiones al entrar y n al salir (3 y 3 con la tercia GLD-GDX-B).
- Préstamo: 0.25 % anual sobre el nocional corto, devengado cada día con base 252 días hábiles.
"""

import numpy as np

# --- Parámetros de este módulo (tabla de parámetros en CLAUDE.md) ---
COMMISSION = 0.00125  # 0.125 % por operación, por pata
BORROW_RATE_ANNUAL = 0.0025  # 0.25 % anual sobre nocional corto
TRADING_DAYS = 252  # base del devengo diario del préstamo


def commission_cost(shares_traded: np.ndarray, prices: np.ndarray, rate: float = COMMISSION) -> float:
    """Comisión del día: rate · Σ_i |Δq_i| · P_i (cada pata paga sobre su propio nocional operado)."""
    return float(rate * np.sum(np.abs(shares_traded) * prices))


def borrow_cost(shares: np.ndarray, prices: np.ndarray, annual_rate: float = BORROW_RATE_ANNUAL,
                days: int = TRADING_DAYS) -> float:
    """Préstamo devengado en un día: (rate / 252) · Σ_{q_i < 0} |q_i| · P_i (solo las patas cortas)."""
    short_notional = np.sum(np.abs(np.minimum(shares, 0.0)) * prices)
    return float(annual_rate / days * short_notional)
