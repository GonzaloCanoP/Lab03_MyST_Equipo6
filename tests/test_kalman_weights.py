"""Pruebas del filtro 1 contra el material de clase (no son de las cuatro obligatorias de §3.11)."""

import numpy as np
import pytest

from kalman.weights_filter import WeightsFilter


def test_reproduces_class_worked_example():
    """Ejemplo trabajado 1 de la sesión 13: y_t = β_t x_t, β̂₀ = 1, P₀ = 0.5, Q = 0.01, R = 0.25.

    Nuestro filtro escribe y_t = c_t − β'_t x_t; con c fijo en 0 (sin varianza) y β' = −β es el mismo modelo, así que
    β̂ y P deben coincidir con la tabla de clase y K cambia de signo.
    """
    kf = WeightsFilter(state=np.array([0.0, -1.0]), P_cov=np.diag([0.0, 0.5]), Q=np.diag([0.0, 0.01]), R=0.25,
                       anchor=0)
    observations = [(1.0, 1.30), (1.2, 1.40), (0.9, 1.20), (1.1, 1.25)]  # (x_t, y_t)
    expected = [  # (ỹ, S, K, β̂_t, P_t) de la tabla de clase
        (0.300, 0.760, 0.671, 1.201, 0.168),
        (-0.042, 0.506, 0.422, 1.184, 0.088),
        (0.135, 0.329, 0.267, 1.220, 0.074),
        (-0.092, 0.352, 0.263, 1.196, 0.060),
    ]
    for (x, y), (innov, innov_var, gain, beta, p_post) in zip(observations, expected):
        kf.predict()
        step = kf.update(np.array([y, x]))
        assert step["innov"] == pytest.approx(innov, abs=2e-3)
        assert step["innov_var"] == pytest.approx(innov_var, abs=2e-3)
        assert -step["gain"][1] == pytest.approx(gain, abs=2e-3)
        assert -step["state_post"][1] == pytest.approx(beta, abs=2e-3)
        assert step["P_post"][1, 1] == pytest.approx(p_post, abs=2e-3)
        assert step["state_post"][0] == 0.0  # el intercepto sin varianza no se mueve


def test_update_requires_predict():
    """El ciclo es predecir → actualizar; actualizar dos veces seguidas es un error."""
    kf = WeightsFilter(state=np.zeros(2), P_cov=np.eye(2), Q=np.eye(2), R=1.0, anchor=0)
    with pytest.raises(RuntimeError):
        kf.update(np.array([1.0, 1.0]))
    kf.predict()
    kf.update(np.array([1.0, 1.0]))
    with pytest.raises(RuntimeError):
        kf.update(np.array([1.0, 1.0]))
