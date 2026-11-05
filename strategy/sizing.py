"""Tamaño de posición multi-pata (sesión 14): 80 % del capital repartido según |β̂_t|.

    N_i = 0.8 · V_t · |β_i| / Σ_j |β_j|            nocional en dólares de la pata i
    q_i = d_t · sgn(β_i) · N_i / P_i               acciones (d_t = +1 largo el spread, −1 corto)

Largo el spread: comprar los activos con β_i > 0 y vender los de β_i < 0. Como β se estimó sobre log-precios,
β_i es la sensibilidad del spread al rendimiento del activo i, así que repartir el nocional en dólares ∝ |β_i|
reproduce el spread. "Capital disponible" = V_t, el valor actual del portafolio (efectivo + patas), no el capital
inicial: las posiciones crecen o se encogen con las ganancias y pérdidas.
"""

import numpy as np

# --- Parámetros de este módulo (tabla de parámetros en CLAUDE.md) ---
INITIAL_CAPITAL = 1_000_000.0
POSITION_FRACTION = 0.80


def target_shares(direction: int, beta: np.ndarray, prices: np.ndarray, equity: float,
                  fraction: float = POSITION_FRACTION) -> np.ndarray:
    """Acciones objetivo por pata para la dirección `direction` ∈ {−1, 0, +1}.

    Parámetros:
        direction: +1 largo el spread, −1 corto, 0 sin posición.
        beta: pesos del vector cointegrante (β̂_t del filtro 1, con la pata ancla = +1).
        prices: precios (no log) del día de ejecución.
        equity: V_t, capital disponible al momento de ejecutar.
        fraction: fracción del capital que se invierte (nocional bruto total).
    Retorna:
        Vector de acciones con signo (positivo largo, negativo corto). Σ_i |q_i| P_i = fraction · V_t.
    """
    beta = np.asarray(beta, dtype=float)
    if direction == 0:
        return np.zeros_like(beta)
    notional = fraction * equity * np.abs(beta) / np.sum(np.abs(beta))
    return direction * np.sign(beta) * notional / np.asarray(prices, dtype=float)
