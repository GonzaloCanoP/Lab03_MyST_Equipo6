"""Pruebas de la regla de señales y del VECM con casos armados a mano (no son de las cuatro obligatorias)."""

import numpy as np
import pandas as pd
import pytest

from cointegration.johansen import normalize_beta, run_johansen
from strategy.signals import SignalRule, build_signals, generate_signals
from strategy.vecm import fit_vecm

RULE = SignalRule(z_entry=1.0, z_exit=0.5, z_stop=3.0, max_holding=5)


def run(z: list[float], rule: SignalRule = RULE) -> pd.DataFrame:
    return generate_signals(pd.Series(z, index=pd.bdate_range("2021-01-04", periods=len(z)), dtype=float), rule)


def test_entry_and_directional_exit():
    """Largo bajo −z_entrada, sale al llegar a −z_salida; corto simétrico. La salida se marca el día del cierre."""
    out = run([0.0, -1.2, -0.8, -0.4, 0.0, 1.5, 0.9, 0.3])
    assert out["signal"].tolist() == [0, 1, 1, 0, 0, -1, -1, 0]
    assert out["exit_reason"].tolist() == ["", "", "", "salida", "", "", "", "salida"]


def test_overshoot_closes_long():
    """Si z salta de −1.5 a +1.5 sin pasar por la banda de salida, el largo se cierra (salida direccional)."""
    out = run([-1.5, 1.5, 1.5])
    assert out["signal"].tolist() == [1, 0, -1]
    assert out["exit_reason"].iloc[1] == "salida"


def test_stop_and_rearm():
    """Stop al tocar |z| ≥ z_stop; no reentra mientras |z| ≥ z_entrada y se rearma al volver dentro."""
    out = run([1.5, 2.5, 3.2, 2.0, 1.5, 0.8, 1.4])
    assert out["signal"].tolist() == [-1, -1, 0, 0, 0, 0, -1]
    assert out["exit_reason"].iloc[2] == "stop"


def test_no_entry_beyond_stop():
    """No abre si z ya está más allá del stop (esa operación se cerraría de inmediato)."""
    assert run([-3.5, -3.1, -2.0])["signal"].tolist() == [0, 0, 1]


def test_holding_limit():
    """Cierra al cumplir h_max días y no reabre la misma dirección hasta rearmarse."""
    out = run([-1.5] * 8 + [-0.9, -1.2])
    assert out["signal"].tolist() == [1, 1, 1, 1, 1, 0, 0, 0, 0, 1]
    assert out["holding_days"].iloc[:5].tolist() == [0, 1, 2, 3, 4]
    assert out["exit_reason"].iloc[5] == "holding"


def test_rule_validates_thresholds():
    with pytest.raises(ValueError):
        SignalRule(z_entry=1.0, z_exit=1.0, z_stop=3.0, max_holding=5)
    with pytest.raises(ValueError):
        SignalRule(z_entry=2.0, z_exit=0.5, z_stop=1.5, max_holding=5)


def test_signals_restart_flat_each_split_and_skip_burn_in():
    """Cada partición arranca plana y el burn-in no genera señales ni aparece en signals.parquet."""
    index = pd.bdate_range("2021-01-04", periods=8)
    kf2 = pd.DataFrame({"zscore": [-2.0, -2.0, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5],
                        "burn_in": [True, True, False, False, False, False, False, False],
                        "split": ["train"] * 5 + ["test"] * 3}, index=index)
    kf1 = pd.DataFrame({"beta_A": 1.0, "beta_B": -0.5}, index=index)
    out = build_signals(kf2, kf1, ["A", "B"], RULE)
    assert out.index[0] == index[2]
    assert out["signal"].tolist() == [1, 1, 1, 1, 1, 1]
    # La operación de train no se hereda: en prueba h_t vuelve a empezar en 0.
    assert out.loc[out["split"] == "test", "holding_days"].iloc[0] == 0
    assert list(out.columns) == ["zscore", "signal", "exit_reason", "holding_days", "beta_A", "beta_B", "split"]


def test_vecm_recovers_error_correction():
    """VECM sobre un par simulado con α conocido (solo A corrige, βᵀα = −0.05): recupera el signo de α, la condición
    −2 < βᵀα < 0 y la vida media teórica −ln 2 / ln(0.95) ≈ 13.5 días. Con un β distinto al de Johansen, falla."""
    rng = np.random.default_rng(42)
    n = 4000
    beta, alpha = np.array([1.0, -1.0]), np.array([-0.05, 0.0])
    p = np.zeros((n, 2))
    for t in range(1, n):
        p[t] = p[t - 1] + alpha * (beta @ p[t - 1]) + rng.normal(0, 0.01, 2)
    frame = pd.DataFrame(p, columns=["A", "B"], index=pd.bdate_range("2010-01-01", periods=n))
    johansen = normalize_beta(run_johansen(frame, k_ar_diff=1).eigenvectors[:, 0], 0)

    vecm = fit_vecm(frame, 1, "A", dict(zip("AB", johansen)))
    assert vecm["error_correction"]
    assert vecm["alpha_significant_5pct"] == ["A"]
    assert vecm["beta_alpha"] == pytest.approx(-0.05, abs=0.01)
    assert vecm["half_life_days"] == pytest.approx(-np.log(2) / np.log(0.95), rel=0.25)
    with pytest.raises(ValueError):
        fit_vecm(frame, 1, "A", {"A": 1.0, "B": -0.9})
