"""Regla de bandas sobre el z-score prior del filtro 2 (PFA de la sesión 11 con θ = (z_entrada, z_salida, z_stop, h_max)).

    plano:       d_t = +1 si −z_stop < z_t < −z_entrada (largo el spread: el ECT está por debajo de su media)
                 d_t = −1 si  z_entrada < z_t <  z_stop (corto el spread)
    con d ≠ 0:   cerrar por stop    si |z_t| ≥ z_stop
                 cerrar por holding si h_t ≥ h_max
                 cerrar por salida  si el largo llega a z_t ≥ −z_salida (el corto a z_t ≤ z_salida)
                 mantener en otro caso

Prioridad stop > holding > salida. No se reabre el mismo día de un cierre. Después de un stop o un holding, esa
dirección se rearma solo cuando |z_t| < z_entrada, para no volver a entrar a un spread que se sigue abriendo.
Todo se decide con información del cierre de t; el motor (`backtest/engine.py`) ejecuta al cierre de t + 1.
Justificación de cada regla en `docs/decisiones.md`.
"""

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

EXIT = "salida"
STOP = "stop"
HOLDING = "holding"


@dataclass(frozen=True)
class SignalRule:
    """Parámetros θ de la regla. `max_holding` en días hábiles (k · vida media, redondeado)."""

    z_entry: float
    z_exit: float
    z_stop: float
    max_holding: int

    def __post_init__(self):
        if not 0 <= self.z_exit < self.z_entry < self.z_stop:
            raise ValueError(f"Se requiere 0 ≤ z_salida < z_entrada < z_stop: {self}")
        if self.max_holding < 1:
            raise ValueError("max_holding debe ser al menos 1 día")

    def to_dict(self) -> dict:
        return asdict(self)


def generate_signals(zscore: pd.Series, rule: SignalRule) -> pd.DataFrame:
    """Aplica la regla a una serie de z-scores **sin huecos** (un tramo continuo, ya sin burn-in). Arranca plana.

    Parámetros:
        zscore: z_t prior del filtro 2 (columna `zscore` de kf2_signal.parquet).
        rule: umbrales y holding máximo.
    Retorna:
        DataFrame con el mismo índice: `signal` ∈ {−1, 0, +1} (dirección decidida al cierre de t),
        `exit_reason` (`salida`, `stop`, `holding` o vacío, el día de la decisión de cierre) y `holding_days` (h_t).
    Supuestos:
        Causal por construcción: la decisión de t solo usa z_1, …, z_t (se recorre la serie hacia adelante).
    """
    if zscore.isna().any():
        raise ValueError("zscore tiene NaN: pasar solo el tramo después del burn-in")
    z = zscore.to_numpy(dtype=float)
    signal = np.zeros(len(z), dtype=int)
    holding = np.zeros(len(z), dtype=int)
    reasons = np.full(len(z), "", dtype=object)
    armed = {+1: True, -1: True}
    d, h = 0, 0

    for t, zt in enumerate(z):
        closed = False
        if d != 0:
            h += 1
            reached_mean = zt >= -rule.z_exit if d == +1 else zt <= rule.z_exit
            if abs(zt) >= rule.z_stop:
                reasons[t], armed[d] = STOP, False
            elif h >= rule.max_holding:
                reasons[t], armed[d] = HOLDING, False
            elif reached_mean:
                reasons[t] = EXIT
            closed = reasons[t] != ""
            if closed:
                d, h = 0, 0

        if abs(zt) < rule.z_entry:
            armed = {+1: True, -1: True}

        if d == 0 and not closed and abs(zt) < rule.z_stop:
            if zt < -rule.z_entry and armed[+1]:
                d, h = +1, 0
            elif zt > rule.z_entry and armed[-1]:
                d, h = -1, 0

        signal[t], holding[t] = d, h

    return pd.DataFrame({"signal": signal, "exit_reason": reasons, "holding_days": holding}, index=zscore.index)


def build_signals(kf2: pd.DataFrame, kf1: pd.DataFrame, tickers: list[str], rule: SignalRule) -> pd.DataFrame:
    """Señales de toda la muestra para el motor: la regla se aplica **por partición**, cada una arranca plana.

    Parámetros:
        kf2: salida del filtro 2 con `zscore`, `burn_in` y `split`.
        kf1: salida del filtro 1 con los pesos posteriores `beta_<T>` (los conoce el cierre de t).
        tickers: activos del grupo.
        rule: umbrales congelados desde train.
    Retorna:
        `signals.parquet`: `zscore`, `signal`, `exit_reason`, `holding_days`, `beta_<T>` y `split`. Solo las fechas
        después de ambos burn-in; el motor trata las fechas que faltan como sin posición.
    """
    active = kf2.loc[~kf2["burn_in"]]
    parts = [generate_signals(group["zscore"], rule) for _, group in active.groupby("split", sort=False)]
    signals = pd.concat(parts).loc[active.index]
    signals.insert(0, "zscore", active["zscore"])
    for t in tickers:
        signals[f"beta_{t}"] = kf1.loc[signals.index, f"beta_{t}"]
    signals["split"] = active["split"]
    return signals
