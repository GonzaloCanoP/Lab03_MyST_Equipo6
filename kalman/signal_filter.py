"""Filtro de Kalman 2: media latente y escala del ECT → z-score con estadísticos PRIOR (sesión 13).

Entrada: el ECT dinámico que produce el filtro 1 día a día (`kf1_weights.parquet`, columna `ect_dynamic`). Es lo que
el enunciado llama "residuales del VECM" (aclarado por el profesor, ver `docs/decisiones.md`).

Modelo: estado aumentado (decisión y motivo en `docs/decisiones.md`, 2026-11-04)

    Estado:       μ_t = μ_{t−1} + w^μ_t,      w^μ_t ~ N(0, q_μ)     media lenta del ECT (nivel local de clase)
                  x_t = φ x_{t−1} + w^x_t,    w^x_t ~ N(0, q_x)     desviación que revierte (AR(1) / OU)
    Observación:  ECT_t = μ_t + x_t + v_t,    v_t ~ N(0, r)

    En forma matricial: z_t = (μ_t, x_t)ᵀ, A = diag(1, φ), Q = diag(q_μ, q_x), C = (1, 1), R = r.

Por qué no el nivel local puro: el nivel local supone que toda desviación de μ_t es ruido de un día (v_t). Nuestro
ECT revierte en semanas, así que el filtro tendría que elegir entre perseguir al ECT con μ̂ (innovaciones limpias pero
z sin señal) o dejar μ̂ lenta (z con señal pero innovaciones autocorrelacionadas). x_t absorbe esa persistencia y
deja a μ_t como el centro del z-score. El nivel local de clase es el caso particular φ = 0, q_x = 0, P₀ₓ = 0.

z-score (SIEMPRE con estadísticos prior, calculados antes de `update`):

    z_t = (ECT_t − μ̂_{t|t−1}) / σ̂_{t|t−1},    σ̂²_{t|t−1} = q_x / (1 − φ²) + p^μ_{t|t−1} + r

σ̂² es la varianza que el modelo le asigna a ECT_t alrededor de la media prior: varianza estacionaria de la desviación
+ incertidumbre de la media + ruido. Con el nivel local se reduce a p + q + r, la σ̂ implícita de clase.

Ciclo predecir / actualizar (ecuaciones de la sesión 13):

    predecir:   ẑ_{t|t−1} = A ẑ_{t−1|t−1}                 P_{t|t−1} = A P_{t−1|t−1} Aᵀ + Q
    actualizar: ν_t = ECT_t − C ẑ_{t|t−1}                S_t = C P_{t|t−1} Cᵀ + r
                K_t = P_{t|t−1} Cᵀ / S_t                   ẑ_{t|t} = ẑ_{t|t−1} + K_t ν_t
                P_{t|t} = (I − K_t C) P_{t|t−1}
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from statsmodels.stats.diagnostic import acorr_ljungbox

from cointegration.half_life import compute_half_life, estimate_ou_speed
from kalman.weights_filter import ABSORPTION_TOLERANCE, TRADE_HALF_LIVES

# --- Parámetros de este módulo (ver docs/decisiones.md y la tabla de parámetros de CLAUDE.md) ---
BURN_IN = 63  # días (≈ un trimestre) después del burn-in del filtro 1; no se opera con ellos
MLE_SKIP = 50  # días iniciales que no entran a la verosimilitud (transitorio de P₀)
Q_MU_SEARCH_BOUNDS = (1e-12, 1e-3)  # intervalo de búsqueda de q_μ
INNOVATION_VAR_TOLERANCE = (0.9, 1.1)  # prueba 4: rango aceptado para la varianza de ν_t / √S_t


def stationary_variance(phi: float, q_x: float) -> float:
    """Varianza estacionaria de la desviación AR(1): Var(x) = q_x / (1 − φ²). Es 0 si q_x = 0."""
    return 0.0 if q_x == 0 else q_x / (1.0 - phi ** 2)


@dataclass
class SignalFilter:
    """Filtro de Kalman 2 con `predict()`, `zscore_prior(obs)` y `update(obs)` separados.

    Atributos:
        state, P_cov: media (μ̂, x̂) y covarianza 2 × 2 de la creencia vigente (prior tras `predict`, posterior tras
            `update`).
        phi, q_mu, q_x, r: parámetros del modelo (ver docstring del módulo).
    """

    state: np.ndarray
    P_cov: np.ndarray
    phi: float
    q_mu: float
    q_x: float
    r: float
    _predicted: bool = field(default=False, repr=False)

    @property
    def A(self) -> np.ndarray:
        return np.diag([1.0, self.phi])

    @property
    def Q(self) -> np.ndarray:
        return np.diag([self.q_mu, self.q_x])

    C = np.array([1.0, 1.0])

    def predict(self) -> tuple[np.ndarray, np.ndarray]:
        """Paso de predicción: ẑ_{t|t−1} = A ẑ_{t−1|t−1}, P_{t|t−1} = A P Aᵀ + Q. Retorna copias del prior."""
        self.state = self.A @ self.state
        self.P_cov = self.A @ self.P_cov @ self.A.T + self.Q
        self._predicted = True
        return self.state.copy(), self.P_cov.copy()

    def sigma_prior(self) -> float:
        """σ̂_{t|t−1} = √(q_x / (1 − φ²) + p^μ_{t|t−1} + r). Requiere haber llamado a `predict()`."""
        return float(np.sqrt(stationary_variance(self.phi, self.q_x) + self.P_cov[0, 0] + self.r))

    def zscore_prior(self, obs: float) -> float:
        """z_t = (ECT_t − μ̂_{t|t−1}) / σ̂_{t|t−1}, calculado ANTES de `update`.

        Usa solo la creencia prior (información hasta t − 1) para juzgar la observación de t. Con la media posterior
        la observación se juzgaría a sí misma: el z se encoge hacia cero (en el nivel local, z_post = (1 − K_t) z_prior).
        """
        if not self._predicted:
            raise RuntimeError("zscore_prior() requiere el prior: llamar antes a predict()")
        return float((obs - self.state[0]) / self.sigma_prior())

    def update(self, obs: float) -> dict:
        """Paso de actualización con el ECT del día t. Debe llamarse después de `predict()`.

        Retorna:
            dict con `innov` (ν_t), `innov_var` (S_t), `gain` (K_t = (K^μ, K^x)), `state_post` y `P_post`.
        """
        if not self._predicted:
            raise RuntimeError("update() requiere llamar antes a predict() (ciclo predecir → actualizar)")
        innov = obs - self.C @ self.state
        innov_var = float(self.C @ self.P_cov @ self.C + self.r)
        gain = self.P_cov @ self.C / innov_var
        self.state = self.state + gain * innov
        # Forma de Joseph (como en el filtro 1): conserva simetría y positividad numéricamente.
        I_KC = np.eye(2) - np.outer(gain, self.C)
        self.P_cov = I_KC @ self.P_cov @ I_KC.T + self.r * np.outer(gain, gain)
        self._predicted = False
        return {"innov": float(innov), "innov_var": innov_var, "gain": gain.copy(),
                "state_post": self.state.copy(), "P_post": self.P_cov.copy()}


def initial_filter(phi: float, q_mu: float, q_x: float, r: float) -> SignalFilter:
    """Filtro inicializado con μ̂₀ = 0, x̂₀ = 0 y P₀ = diag(v_x, v_x), v_x = q_x / (1 − φ²).

    El ECT dinámico está centrado en cero por construcción (el intercepto va en el estado del filtro 1); P₀ igual a
    la dispersión del spread es un prior vago en su propia escala.
    """
    v_x = stationary_variance(phi, q_x)
    return SignalFilter(state=np.zeros(2), P_cov=np.diag([v_x, v_x]), phi=phi, q_mu=q_mu, q_x=q_x, r=r)


def run_signal_filter(ect: pd.Series, phi: float, q_mu: float, q_x: float, r: float,
                      burn_in: int = BURN_IN) -> pd.DataFrame:
    """Corre el filtro 2 día por día sobre el ECT (causal: z_t solo usa información hasta t − 1 para μ̂ y σ̂).

    Parámetros:
        ect: ECT dinámico del filtro 1, sin su burn-in (índice de fechas).
        phi, q_mu, q_x, r: parámetros calibrados en train (`calibrate_signal_filter`).
        burn_in: días iniciales marcados como burn-in (no se opera con ellos).
    Retorna:
        DataFrame indexado por fecha con `ect`, `mu_prior`, `mu_post`, `x_prior`, `x_post`, `sigma_prior`,
        `zscore` (prior, la señal), `zscore_post` (solo diagnóstico, para mostrar por qué no se usa), `innov` (ν_t),
        `innov_var` (S_t), `innov_norm` (ν_t / √S_t), `gain_mu`, `gain_x`, `var_post_mu`, `var_post_x` y `burn_in`.
    """
    kf = initial_filter(phi, q_mu, q_x, r)
    rows = []
    for obs in ect.to_numpy():
        state_prior, _ = kf.predict()
        sigma = kf.sigma_prior()
        z = kf.zscore_prior(obs)  # ← ANTES de update: estadísticos prior
        step = kf.update(obs)
        rows.append({
            "ect": obs,
            "mu_prior": state_prior[0],
            "mu_post": step["state_post"][0],
            "x_prior": state_prior[1],
            "x_post": step["state_post"][1],
            "sigma_prior": sigma,
            "zscore": z,
            "zscore_post": (obs - step["state_post"][0]) / sigma,
            "innov": step["innov"],
            "innov_var": step["innov_var"],
            "gain_mu": step["gain"][0],
            "gain_x": step["gain"][1],
            "var_post_mu": step["P_post"][0, 0],
            "var_post_x": step["P_post"][1, 1],
        })
    out = pd.DataFrame(rows, index=ect.index)
    out["innov_norm"] = out["innov"] / np.sqrt(out["innov_var"])
    out["burn_in"] = np.arange(len(out)) < burn_in
    return out


def _negative_log_likelihood(log_params: np.ndarray, ect: np.ndarray, phi: float, q_mu: float) -> float:
    """−log verosimilitud gaussiana de las innovaciones (sin constantes), excluyendo los primeros MLE_SKIP días."""
    q_x, r = np.exp(log_params)
    kf = initial_filter(phi, q_mu, q_x, r)
    terms = np.empty(len(ect))
    for t, obs in enumerate(ect):
        kf.predict()
        step = kf.update(obs)
        terms[t] = np.log(step["innov_var"]) + step["innov"] ** 2 / step["innov_var"]
    return 0.5 * float(terms[MLE_SKIP:].sum())


def fit_noise_mle(train_ect: pd.Series, phi: float, q_mu: float = 0.0) -> tuple[float, float]:
    """Estima q_x y r por máxima verosimilitud de las innovaciones, SOLO con entrenamiento (φ y q_μ fijos).

    Retorna:
        (q_x, r). Se optimiza en logaritmos (garantiza positividad) con Nelder–Mead.
    """
    v = float(train_ect.var())
    start = np.log([0.05 * v, 0.005 * v])
    result = minimize(_negative_log_likelihood, start, args=(train_ect.to_numpy(), phi, q_mu), method="Nelder-Mead",
                      options={"xatol": 1e-4, "fatol": 1e-3, "maxiter": 2000})
    q_x, r = np.exp(result.x)
    return float(q_x), float(r)


def mean_absorption(phi: float, gain: np.ndarray, days: int) -> float:
    """Fracción de un desplazamiento PERMANENTE del ECT que μ̂ absorbe después de `days` días.

    Respuesta a un escalón con la ganancia de estado estable K = (K^μ, K^x): el ECT pasa de 0 a 1 y se queda ahí;
    cada día se predice (μ̂, φ x̂) y se corrige con K · ν. Lo que termina en μ̂ deja de verse como desviación en z.
    """
    A = np.diag([1.0, phi])
    state = np.zeros(2)
    for _ in range(int(round(days))):
        state = A @ state
        state = state + gain * (1.0 - state.sum())
    return float(state[0])


def calibrate_q_mu(train_ect: pd.Series, phi: float, q_x: float, r: float, half_life: float,
                   tolerance: float = ABSORPTION_TOLERANCE, trade_half_lives: float = TRADE_HALF_LIVES,
                   burn_in: int = BURN_IN, bounds: tuple[float, float] = Q_MU_SEARCH_BOUNDS,
                   iterations: int = 30) -> float:
    """Elige q_μ SOLO con entrenamiento por separación de escalas (mismo criterio que el filtro 1).

    El mayor q_μ tal que μ̂ absorbe a lo más `tolerance` de un desplazamiento durante una operación típica
    (`trade_half_lives` vidas medias del ECT). La absorción crece con q_μ, por eso basta una bisección en log10.
    La ganancia de estado estable es la mediana de K_t en train después del burn-in.
    """
    days = trade_half_lives * half_life

    def absorbed(q_mu: float) -> float:
        out = run_signal_filter(train_ect, phi, q_mu, q_x, r, burn_in)
        steady = out.loc[~out["burn_in"], ["gain_mu", "gain_x"]].median().to_numpy()
        return mean_absorption(phi, steady, days)

    lo, hi = np.log10(bounds[0]), np.log10(bounds[1])
    if absorbed(10 ** lo) > tolerance:
        raise ValueError("Ni el q_μ mínimo cumple la tolerancia de absorción; revisar el rango de búsqueda")
    for _ in range(iterations):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if absorbed(10 ** mid) <= tolerance else (lo, mid)
    return float(10 ** lo)


def calibrate_signal_filter(train_ect: pd.Series) -> dict:
    """Calibración completa del filtro 2 con el ECT de ENTRENAMIENTO (sin el burn-in del filtro 1).

    Pasos (ver `docs/decisiones.md`):
        1. φ = 1 + λ̂ del AR(1)/OU del ECT (sesión 12) y su vida media.
        2. q_x y r por máxima verosimilitud con q_μ = 0 (la verosimilitud casi no depende de q_μ).
        3. q_μ por separación de escalas (`calibrate_q_mu`).
    Retorna:
        dict con `phi`, `half_life_days`, `q_mu`, `q_x`, `r`, `stationary_sd` (√(q_x / (1 − φ²))),
        `absorbed_in_trade_train` y `burn_in_days`.
    """
    phi = 1.0 + estimate_ou_speed(train_ect)
    half_life = compute_half_life(train_ect)
    q_x, r = fit_noise_mle(train_ect, phi)
    q_mu = calibrate_q_mu(train_ect, phi, q_x, r, half_life)
    out = run_signal_filter(train_ect, phi, q_mu, q_x, r)
    steady = out.loc[~out["burn_in"], ["gain_mu", "gain_x"]].median().to_numpy()
    return {
        "phi": phi,
        "half_life_days": half_life,
        "q_mu": q_mu,
        "q_x": q_x,
        "r": r,
        "stationary_sd": float(np.sqrt(stationary_variance(phi, q_x))),
        "absorbed_in_trade_train": mean_absorption(phi, steady, TRADE_HALF_LIVES * half_life),
        "burn_in_days": BURN_IN,
    }


def innovation_diagnostics(kf2: pd.DataFrame, lags: tuple[int, ...] = (1, 5, 10)) -> pd.DataFrame:
    """Diagnóstico de la prueba 4 por partición: varianza y autocorrelación de ν_t / √S_t, sin el burn-in.

    Retorna:
        DataFrame indexado por partición con `n`, `mean`, `var`, `acf_1` y el p-value de Ljung–Box en cada rezago
        de `lags` (`lb_p_<k>`).
    """
    rows = {}
    for split, part in kf2.loc[~kf2["burn_in"]].groupby("split", sort=False):
        e = part["innov_norm"]
        lb = acorr_ljungbox(e, lags=list(lags))["lb_pvalue"]
        rows[split] = {"n": len(e), "mean": float(e.mean()), "var": float(e.var()), "acf_1": float(e.autocorr(1)),
                       **{f"lb_p_{k}": float(lb.loc[k]) for k in lags}}
    return pd.DataFrame.from_dict(rows, orient="index")
