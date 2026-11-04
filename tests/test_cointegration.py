"""Pruebas del embudo de cointegración con datos sintéticos de respuesta conocida.

No son de las cuatro pruebas obligatorias (§3.11); verifican que las piezas de la parte 02 hagan lo que dicen.
"""

import numpy as np
import pandas as pd
import pytest

from cointegration.correlation import group_correlation, rolling_pairwise_correlation
from cointegration.engle_granger import engle_granger
from cointegration.half_life import compute_half_life
from cointegration.johansen import (anchor_index, compare_vectors, estimate_rank, normalize_beta, run_johansen)

SEED = 42
T = 2000


@pytest.fixture
def cointegrated_prices() -> pd.DataFrame:
    """4 log-precios con UNA tendencia común (caminata aleatoria) + ruido AR(1) estacionario propio.

    Con 4 series y 1 tendencia común hay 3 relaciones de cointegración; el spread A − B es estacionario.
    """
    rng = np.random.default_rng(SEED)
    trend = np.cumsum(rng.normal(0, 0.01, T))
    columns = {}
    for name, loading in zip("ABCD", (1.0, 1.0, 0.8, 1.2)):
        noise = np.zeros(T)
        for t in range(1, T):
            noise[t] = 0.9 * noise[t - 1] + rng.normal(0, 0.01)
        columns[name] = loading * trend + noise
    return pd.DataFrame(columns, index=pd.bdate_range("2012-01-02", periods=T))


@pytest.fixture
def independent_walks() -> pd.DataFrame:
    """4 caminatas aleatorias independientes: no hay cointegración."""
    rng = np.random.default_rng(SEED)
    return pd.DataFrame(np.cumsum(rng.normal(0, 0.01, (T, 4)), axis=0), columns=list("ABCD"),
                        index=pd.bdate_range("2012-01-02", periods=T))


def test_half_life_recovers_ar1():
    """Para un AR(1) s_t = φ s_{t−1} + ε, λ = φ − 1 y la vida media es −ln 2 / (φ − 1)."""
    rng = np.random.default_rng(SEED)
    phi = 0.95
    s = np.zeros(20_000)
    for t in range(1, len(s)):
        s[t] = phi * s[t - 1] + rng.normal()
    expected = -np.log(2) / (phi - 1)  # ≈ 13.9 días
    assert compute_half_life(pd.Series(s)) == pytest.approx(expected, rel=0.10)


def test_half_life_is_infinite_for_explosive_series():
    """Si λ ≥ 0 el spread no revierte y la vida media debe ser infinita (nunca pasa el filtro)."""
    s = pd.Series(np.cumsum(np.ones(100)) ** 1.5)
    assert compute_half_life(s) == float("inf")


def test_estimate_rank_takes_first_non_rejection():
    """Ejemplo de clase (sesión 14): traza (45.60, 14.66, 2.00) vs (29.80, 15.49, 3.84) → r̂ = 1."""
    assert estimate_rank(np.array([45.60, 14.66, 2.00]), np.array([29.80, 15.49, 3.84])) == 1
    assert estimate_rank(np.array([10.0, 5.0]), np.array([15.0, 3.8])) == 0
    assert estimate_rank(np.array([50.0, 20.0]), np.array([15.0, 3.8])) == 2


def test_normalization_fixes_scale_and_sign():
    """β̃ no depende de la escala ni del signo del eigenvector y la pata ancla vale +1."""
    beta = np.array([0.3, -1.7, 0.5, 0.9])
    anchor = anchor_index(beta)
    assert anchor == 1
    for scale in (1.0, -1.0, 2.5, -0.01):
        normalized = normalize_beta(scale * beta, anchor_index(scale * beta))
        assert normalized[anchor] == pytest.approx(1.0)
        np.testing.assert_allclose(normalized, beta / beta[anchor])


def test_johansen_detects_common_trend(cointegrated_prices):
    """Con una tendencia común, Johansen rechaza r = 0 y el primer vector da un spread reversivo."""
    result = run_johansen(cointegrated_prices, k_ar_diff=1)
    assert result.rank("trace") >= 1
    comparison = compare_vectors(cointegrated_prices, result, (1.0, 60.0), 0.05)
    first = comparison.iloc[0]
    assert first["adf_pvalue"] < 0.05
    assert first["half_life"] < 60


def test_johansen_no_rank_for_independent_walks(independent_walks):
    """Sin tendencia común, la traza no rechaza r = 0 (con esta semilla)."""
    assert run_johansen(independent_walks, k_ar_diff=1).rank("trace") == 0


def test_engle_granger_pair(cointegrated_prices, independent_walks):
    """EG detecta el par cointegrado A-B y no el par de caminatas independientes."""
    assert engle_granger(cointegrated_prices[["A", "B"]], "A").pvalue < 0.05
    assert engle_granger(independent_walks[["A", "B"]], "A").pvalue > 0.05


def test_group_correlation_uses_only_group_pairs(cointegrated_prices):
    """La correlación del grupo promedia solo sus pares y la ventana no usa datos futuros."""
    returns = cointegrated_prices.diff().dropna()
    rolling = rolling_pairwise_correlation(returns, window=252)
    assert rolling.iloc[:251].isna().all().all()
    # Truncar los datos no cambia la correlación de una fecha anterior (sin look-ahead).
    truncated = rolling_pairwise_correlation(returns.iloc[:800], window=252)
    pd.testing.assert_series_equal(rolling.iloc[799], truncated.iloc[799])
    stats = group_correlation(rolling, ["A", "B", "C"], threshold=0.7)
    assert set(stats) == {"corr_mean", "corr_min_pair", "corr_frac_above"}
    expected = rolling[["A-B", "A-C", "B-C"]].dropna().mean().mean()
    assert stats["corr_mean"] == pytest.approx(expected)
