"""Prueba obligatoria 2 (§3.11): β̂ mantiene escala y signo estables entre reestimaciones consecutivas.

Se prueba en las dos fuentes de β del proyecto:
- Johansen (`normalize_beta`): reestimar en ventanas consecutivas da vectores con la misma escala y signo una vez
  normalizados sobre la pata ancla, aunque el eigenvector crudo cambie de escala o de signo.
- Filtro 1 (`run_weights_filter`): la pata ancla vale +1 en cada día, ningún peso cambia de signo y el cambio diario
  de β̂ es pequeño (no hay saltos de escala de un día a otro).
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from cointegration.johansen import anchor_index, normalize_beta, run_johansen
from kalman.weights_filter import beta_from_state, run_weights_filter, state_from_beta, static_ect

SEED = 42
T = 1500
BETA_TRUE = np.array([1.0, -0.6, 0.4, -0.35])  # pata ancla primero, como GLD-GDX-AEM-FNV
INTERCEPT_TRUE = 2.0
ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"


@pytest.fixture
def one_relation_prices() -> pd.DataFrame:
    """4 log-precios con UNA relación de cointegración conocida: βᵀP_t − c = u_t, u_t AR(1) con φ = 0.9.

    Las patas 2–4 son caminatas aleatorias independientes; la pata ancla se construye para cumplir la relación.
    """
    rng = np.random.default_rng(SEED)
    others = 4.0 + np.cumsum(rng.normal(0, 0.02, (T, 3)), axis=0)
    u = np.zeros(T)
    for t in range(1, T):
        u[t] = 0.9 * u[t - 1] + rng.normal(0, 0.005)
    anchor = INTERCEPT_TRUE - others @ BETA_TRUE[1:] + u
    return pd.DataFrame(np.column_stack([anchor, others]), columns=list("ABCD"),
                        index=pd.bdate_range("2012-01-02", periods=T))


def test_johansen_consecutive_reestimations_keep_scale_and_sign(one_relation_prices):
    """Ventanas consecutivas: el eigenvector crudo puede cambiar de escala y signo; el normalizado no."""
    windows = [one_relation_prices.iloc[start:start + 750] for start in (0, 250, 500, 750)]
    normalized = []
    for window in windows:
        raw = run_johansen(window, k_ar_diff=1).eigenvectors[:, 0]
        assert anchor_index(raw) == 0  # la pata ancla sigue siendo la de mayor |β| en cada reestimación
        normalized.append(normalize_beta(raw, 0))
    normalized = np.array(normalized)
    assert np.all(normalized[:, 0] == 1.0)
    assert np.all(np.sign(normalized) == np.sign(BETA_TRUE))  # mismo signo en todas las reestimaciones
    np.testing.assert_allclose(normalized, np.tile(BETA_TRUE, (len(windows), 1)), atol=0.08)
    assert np.max(np.abs(np.diff(normalized, axis=0))) < 0.1  # escala estable entre ventanas consecutivas


@pytest.mark.parametrize("scale", [1.0, -1.0, 37.5, -0.02])
def test_filter_is_invariant_to_eigenvector_scale(one_relation_prices, scale):
    """Inicializar el filtro con c·β (cualquier escala o signo) y normalizar da exactamente el mismo filtro."""
    raw = run_johansen(one_relation_prices, k_ar_diff=1).eigenvectors[:, 0]
    reference = normalize_beta(raw, 0)
    rescaled = normalize_beta(scale * raw, anchor_index(scale * raw))
    np.testing.assert_allclose(rescaled, reference)
    c = float(static_ect(one_relation_prices, reference, 0.0).mean())
    out_ref = run_weights_filter(one_relation_prices, "A", reference, c, 1e-8, 1e-4)
    out_new = run_weights_filter(one_relation_prices, "A", rescaled, c, 1e-8, 1e-4)
    pd.testing.assert_frame_equal(out_ref, out_new)


def test_filter_keeps_anchor_scale_and_signs(one_relation_prices):
    """Pata ancla = +1 en cada día (prior y posterior), sin cambios de signo y con cambios diarios pequeños."""
    start = BETA_TRUE + np.array([0.0, 0.05, -0.05, 0.05])  # arranque desplazado: el filtro debe corregirlo
    out = run_weights_filter(one_relation_prices, "A", start, INTERCEPT_TRUE, 1e-7, 1e-4)
    assert (out["beta_A"] == 1.0).all() and (out["beta_prior_A"] == 1.0).all()
    betas = out[[f"beta_{t}" for t in "ABCD"]].to_numpy()
    assert np.all(np.sign(betas) == np.sign(BETA_TRUE))
    assert np.max(np.abs(np.diff(betas, axis=0))) < 0.01
    np.testing.assert_allclose(betas[-250:].mean(axis=0), BETA_TRUE, atol=0.05)


def test_state_roundtrip_and_anchor_check():
    """z = (c, β sin ancla) ↔ β completo; un β que no está normalizado sobre la pata ancla se rechaza."""
    state = state_from_beta(BETA_TRUE, INTERCEPT_TRUE, anchor=0)
    np.testing.assert_allclose(state, [INTERCEPT_TRUE, -0.6, 0.4, -0.35])
    beta, intercept = beta_from_state(state, anchor=0)
    np.testing.assert_allclose(beta, BETA_TRUE)
    assert intercept == INTERCEPT_TRUE
    with pytest.raises(ValueError):
        state_from_beta(2 * BETA_TRUE, INTERCEPT_TRUE, anchor=0)


def test_project_filter_keeps_johansen_signs():
    """Sobre los datos del proyecto (`kf1_weights.parquet`): ancla = +1 y los signos de Johansen en todos los días."""
    path = ARTIFACTS / "kf1_weights.parquet"
    if not path.exists():
        pytest.skip("correr python main.py para generar kf1_weights.parquet")
    kf1 = pd.read_parquet(path)
    beta0 = json.loads((ARTIFACTS / "johansen_summary.json").read_text())["beta_normalized"]
    for ticker, value in beta0.items():
        assert (np.sign(kf1[f"beta_{ticker}"]) == np.sign(value)).all(), ticker
    anchor = max(beta0, key=lambda t: abs(beta0[t]))
    assert (kf1[f"beta_{anchor}"] == 1.0).all()
