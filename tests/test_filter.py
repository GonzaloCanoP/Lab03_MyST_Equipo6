"""Prueba 4 (§3.11): las innovaciones normalizadas del filtro 2 tienen varianza cercana a uno y autocorrelación no
significativa. Más pruebas del filtro 2: ejemplo 2 de la sesión 13, z prior vs posterior y causalidad.

Tolerancia declarada (`docs/decisiones.md`): varianza en INNOVATION_VAR_TOLERANCE = [0.9, 1.1]; autocorrelación:
Ljung–Box del rezago 1 con p > 0.05 en los datos del proyecto, y a 10 rezagos con datos simulados del propio modelo.
La prueba 4 aplica al filtro 2, no al filtro 1 (en el filtro 1 la innovación es el ECT y debe revertir).
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from statsmodels.stats.diagnostic import acorr_ljungbox

from kalman.signal_filter import (INNOVATION_VAR_TOLERANCE, SignalFilter, initial_filter, run_signal_filter)

SEED = 42
ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"
LO, HI = INNOVATION_VAR_TOLERANCE

# Ejemplo trabajado 2 de la sesión 13 (nivel local): s_t, μ̂_{t|t−1}, σ̂_{t|t−1}, z prior, K_t, μ̂_{t|t}, z posterior.
CLASS_EXAMPLE_2 = [
    (0.020, 0.0000, 0.0539, 0.37, 0.141, 0.0028, 0.32),
    (0.060, 0.0028, 0.0535, 1.07, 0.127, 0.0101, 0.93),
    (0.115, 0.0101, 0.0532, 1.97, 0.115, 0.0222, 1.75),
    (0.130, 0.0222, 0.0529, 2.04, 0.107, 0.0337, 1.82),
    (0.070, 0.0337, 0.0527, 0.69, 0.100, 0.0373, 0.62),
    (0.015, 0.0373, 0.0525, -0.42, 0.094, 0.0352, -0.38),
]


def local_level_filter() -> SignalFilter:
    """Nivel local de clase como caso particular del estado aumentado: φ = 0, q_x = 0 y P₀ₓ = 0 (x ≡ 0)."""
    return SignalFilter(state=np.zeros(2), P_cov=np.diag([4e-4, 0.0]), phi=0.0, q_mu=1e-5, q_x=0.0, r=2.5e-3)


def test_reproduces_class_worked_example_2():
    """El filtro reproduce la tabla del ejemplo 2 de la sesión 13 (z prior, ganancia, media posterior)."""
    kf = local_level_filter()
    for s, mu_prior, sigma, z_prior, gain, mu_post, z_post in CLASS_EXAMPLE_2:
        kf.predict()
        assert kf.state[0] == pytest.approx(mu_prior, abs=1e-4)
        assert kf.sigma_prior() == pytest.approx(sigma, abs=1e-4)
        z = kf.zscore_prior(s)
        assert z == pytest.approx(z_prior, abs=0.01)
        step = kf.update(s)
        assert step["gain"][0] == pytest.approx(gain, abs=1e-3)
        assert step["state_post"][0] == pytest.approx(mu_post, abs=1e-4)
        assert (s - step["state_post"][0]) / sigma == pytest.approx(z_post, abs=0.01)


def test_posterior_zscore_is_shrunk_by_gain():
    """En el nivel local z_post = (1 − K_t) z_prior: el posterior siempre subestima la desviación del día."""
    kf = local_level_filter()
    for s, *_ in CLASS_EXAMPLE_2:
        kf.predict()
        sigma, z_prior = kf.sigma_prior(), kf.zscore_prior(s)
        step = kf.update(s)
        z_post = (s - step["state_post"][0]) / sigma
        assert z_post == pytest.approx((1 - step["gain"][0]) * z_prior)


def test_cycle_order_is_enforced():
    """zscore_prior y update exigen el prior: no se puede juzgar ni actualizar sin predecir antes."""
    kf = initial_filter(phi=0.9, q_mu=1e-6, q_x=1e-4, r=1e-5)
    with pytest.raises(RuntimeError):
        kf.zscore_prior(0.0)
    with pytest.raises(RuntimeError):
        kf.update(0.0)


def simulate_model(phi: float, q_mu: float, q_x: float, r: float, n: int, seed: int = SEED) -> pd.Series:
    """Simula ECT_t = μ_t + x_t + v_t con el modelo del filtro 2 (para probar el filtro donde el modelo es correcto)."""
    rng = np.random.default_rng(seed)
    mu = np.cumsum(rng.normal(0, np.sqrt(q_mu), n))
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + rng.normal(0, np.sqrt(q_x))
    return pd.Series(mu + x + rng.normal(0, np.sqrt(r), n), index=pd.bdate_range("2013-01-01", periods=n))


def test_innovations_are_white_when_model_is_correct():
    """Con datos del propio modelo: varianza de ν/√S en tolerancia y Ljung–Box a 10 rezagos no significativo."""
    params = {"phi": 0.967, "q_mu": 1e-6, "q_x": 1e-4, "r": 5e-6}
    out = run_signal_filter(simulate_model(n=5000, **params), **params)
    e = out.loc[~out["burn_in"], "innov_norm"]
    assert LO <= e.var() <= HI
    assert acorr_ljungbox(e, lags=[10])["lb_pvalue"].iloc[0] > 0.05


def test_project_innovations_train():
    """Prueba 4 con los datos del proyecto (train, sin burn-in): varianza en tolerancia y rezago 1 no significativo.

    A 5–20 rezagos Ljung–Box rechaza con cualquier modelo probado: la autocorrelación (|ρ| ≤ 0.10) viene del propio
    ECT, no del filtro (ver `docs/decisiones.md` y el notebook 04).
    """
    kf2 = pd.read_parquet(ARTIFACTS / "kf2_signal.parquet")
    e = kf2.loc[(kf2["split"] == "train") & ~kf2["burn_in"], "innov_norm"]
    assert LO <= e.var() <= HI
    assert acorr_ljungbox(e, lags=[1])["lb_pvalue"].iloc[0] > 0.05


def test_zscore_is_causal():
    """z_t no cambia si se trunca la serie en t: el filtro solo usa información hasta t."""
    params = {"phi": 0.967, "q_mu": 1e-6, "q_x": 1e-4, "r": 5e-6}
    ect = simulate_model(n=600, **params)
    full = run_signal_filter(ect, **params)["zscore"]
    for t in (100, 300, 599):
        truncated = run_signal_filter(ect.iloc[: t + 1], **params)["zscore"]
        assert truncated.iloc[-1] == full.iloc[t]
