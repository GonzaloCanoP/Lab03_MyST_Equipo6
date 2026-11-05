"""Filtro de Kalman 1: pesos dinámicos del vector cointegrante (sesiones 13 y 14).

Modelo de espacio de estados (notación de clase; aquí P_t son LOG-precios y P_cov la covarianza del filtro):

    Estado:       z_t = A z_{t−1} + w_t,   A = I,  w_t ~ N(0, Q)       (los pesos siguen una caminata aleatoria)
    Observación:  y_t = C_t z_t + v_t,     v_t ~ N(0, R)

    y_t = P_t^{(ancla)}                       log-precio de la pata ancla (GLD), cuyo peso se fija en +1
    C_t = (1, −P_t^{(2)}, …, −P_t^{(n)})      log-precios de las otras patas con signo negativo
    z_t = (c_t, β_t^{(2)}, …, β_t^{(n)})      intercepto y pesos de las otras patas

Normalización y signo: el peso de la pata ancla vale +1 en todo momento (lo fija la ecuación de observación, no el
filtro), así que el estado está identificado: β y k·β ya no describen el mismo estado. Es la misma convención que
`cointegration/johansen.py` (β̃_ancla = +1) y por eso el filtro se inicializa con el β̃ de Johansen sin reescalar.

Con esa forma, el término de corrección de error (ECT) es exactamente el residual de la observación:

    ECT_t = β_tᵀ P_t − c_t = y_t − C_t z_t.

ECT dinámico (decisión del equipo, `docs/decisiones.md`, 2026-11-04): se calcula con los pesos PRIOR ẑ_{t|t−1},
es decir, ECT_t = ỹ_t, la innovación del filtro. Es causal (solo usa información hasta t − 1 para los pesos) y no
está encogido hacia cero, como sí lo estaría el residual posterior (R / S_t) · ỹ_t.

Ciclo predecir / actualizar (separados, como pide la guía 03):

    predecir:   ẑ_{t|t−1} = ẑ_{t−1|t−1}                P_{t|t−1} = P_{t−1|t−1} + Q
    actualizar: ỹ_t = y_t − C_t ẑ_{t|t−1}              S_t = C_t P_{t|t−1} C_tᵀ + R
                K_t = P_{t|t−1} C_tᵀ / S_t             ẑ_{t|t} = ẑ_{t|t−1} + K_t ỹ_t
                P_{t|t} = (I − K_t C_t) P_{t|t−1}
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from cointegration.half_life import compute_half_life
from cointegration.johansen import adf_pvalue

# --- Parámetros de este módulo (ver docs/decisiones.md y la tabla de parámetros de CLAUDE.md) ---
BURN_IN = 252  # días (≈ 1 año): la fracción absorbida C_t K_t se estabiliza; también fija P_0 = BURN_IN · Q
ABSORPTION_TOLERANCE = 0.20  # fracción máxima de una desviación que el filtro puede absorber durante una operación
TRADE_HALF_LIVES = 2  # duración típica de una operación, en vidas medias del spread de entrenamiento
Q_SEARCH_BOUNDS = (1e-12, 1e-4)  # intervalo de búsqueda de q (Q = q · I)


def observation(log_prices_t: np.ndarray, anchor: int) -> tuple[float, np.ndarray]:
    """Observación del día t: y_t = log-precio del ancla y C_t = (1, −log-precios de las otras patas).

    Parámetros:
        log_prices_t: vector de n log-precios del día t, en el orden de los tickers del grupo.
        anchor: posición de la pata ancla en ese vector.
    Retorna:
        (y_t, C_t) con C_t de dimensión n (1 intercepto + n − 1 pesos).
    """
    log_prices_t = np.asarray(log_prices_t, dtype=float)
    others = np.delete(log_prices_t, anchor)
    return float(log_prices_t[anchor]), np.concatenate(([1.0], -others))


def state_from_beta(beta: np.ndarray, intercept: float, anchor: int) -> np.ndarray:
    """Estado z = (c, β de las patas que no son ancla) a partir del vector completo β (con β_ancla = +1)."""
    beta = np.asarray(beta, dtype=float)
    if not np.isclose(beta[anchor], 1.0):
        raise ValueError(f"β debe estar normalizado con la pata ancla en +1 (β_ancla = {beta[anchor]})")
    return np.concatenate(([intercept], np.delete(beta, anchor)))


def beta_from_state(state: np.ndarray, anchor: int) -> tuple[np.ndarray, float]:
    """Inverso de `state_from_beta`: (β completo con β_ancla = +1, intercepto c)."""
    state = np.asarray(state, dtype=float)
    return np.insert(state[1:], anchor, 1.0), float(state[0])


@dataclass
class WeightsFilter:
    """Filtro de Kalman 1 con `predict()` y `update()` separados.

    Atributos:
        state, P_cov: media y covarianza de la creencia vigente. Después de `update` son el posterior
            ẑ_{t|t}, P_{t|t}; después de `predict`, el prior ẑ_{t|t−1}, P_{t|t−1}.
        Q: covarianza del ruido de estado (n × n). R: varianza del ruido de observación (escalar).
        anchor: posición de la pata ancla en el vector de log-precios.
    """

    state: np.ndarray
    P_cov: np.ndarray
    Q: np.ndarray
    R: float
    anchor: int
    _predicted: bool = field(default=False, repr=False)

    def predict(self) -> tuple[np.ndarray, np.ndarray]:
        """Paso de predicción (A = I): la media no cambia y la incertidumbre crece en Q.

        Retorna:
            (ẑ_{t|t−1}, P_{t|t−1}), copias.
        """
        self.P_cov = self.P_cov + self.Q
        self._predicted = True
        return self.state.copy(), self.P_cov.copy()

    def update(self, log_prices_t: np.ndarray) -> dict:
        """Paso de actualización con los log-precios del día t. Debe llamarse después de `predict()`.

        Retorna:
            dict con `innov` (ỹ_t = ECT dinámico con pesos prior), `innov_var` (S_t), `gain` (K_t, vector n),
            `state_post` (ẑ_{t|t}) y `P_post` (P_{t|t}).
        """
        if not self._predicted:
            raise RuntimeError("update() requiere llamar antes a predict() (ciclo predecir → actualizar)")
        y, C = observation(log_prices_t, self.anchor)
        innov = y - C @ self.state
        innov_var = float(C @ self.P_cov @ C + self.R)
        gain = self.P_cov @ C / innov_var
        self.state = self.state + gain * innov
        # Forma de Joseph: equivalente a (I − K C) P pero conserva la simetría y la positividad numéricamente.
        I_KC = np.eye(len(self.state)) - np.outer(gain, C)
        self.P_cov = I_KC @ self.P_cov @ I_KC.T + self.R * np.outer(gain, gain)
        self._predicted = False
        return {"innov": float(innov), "innov_var": innov_var, "gain": gain.copy(),
                "state_post": self.state.copy(), "P_post": self.P_cov.copy()}


def make_noise_matrices(q: float, residual_var: float, n_states: int, burn_in: int = BURN_IN) -> tuple:
    """Q = q · I, R = varianza de los residuales de Johansen en train y P_0 = burn_in · Q.

    Q isótropa (misma deriva para el intercepto y cada peso) es la forma δ / (1 − δ) · I de clase con
    q = δ / (1 − δ). Solo importa la razón q / R. P_0 equivale a la incertidumbre de un burn-in de deriva: el filtro
    confía en el β de Johansen al inicio pero puede corregirlo durante el burn-in.
    Retorna:
        (Q, R, P_0).
    """
    Q = q * np.eye(n_states)
    return Q, float(residual_var), burn_in * Q


def run_weights_filter(log_prices: pd.DataFrame, anchor: str, beta0: np.ndarray, intercept0: float, q: float,
                       residual_var: float, burn_in: int = BURN_IN) -> pd.DataFrame:
    """Corre el filtro 1 día por día sobre `log_prices` (causal: el día t solo usa log-precios hasta t).

    Parámetros:
        log_prices: log-precios del grupo (columnas en el orden de los tickers; puede ser toda la muestra).
        anchor: ticker de la pata ancla (peso fijo +1).
        beta0, intercept0: β̃ de Johansen (con β̃_ancla = +1) y c de entrenamiento: estado inicial.
        q, residual_var: definen Q = q · I y R (ver `make_noise_matrices`).
        burn_in: días iniciales marcados como burn-in (no se opera con ellos).
    Retorna:
        DataFrame indexado por fecha con, para cada ticker T, `beta_T` (posterior β̂_{t|t}) y `beta_prior_T`
        (β̂_{t|t−1}); `intercept` e `intercept_prior`; `gain_<estado>` (componentes de K_t) y `var_post_<estado>`
        (diagonal de P_{t|t}); `ect_dynamic` (= ỹ_t, ECT con pesos prior), `innov_var` (S_t), `innov_norm`
        (ỹ_t / √S_t), `absorption` (C_t K_t = 1 − R / S_t: fracción de la sorpresa que absorbe el filtro) y
        `burn_in`.
    """
    tickers = list(log_prices.columns)
    anchor_pos = tickers.index(anchor)
    others = [t for t in tickers if t != anchor]
    state_names = ["c"] + others
    state0 = state_from_beta(beta0, intercept0, anchor_pos)
    Q, R, P0 = make_noise_matrices(q, residual_var, len(state0), burn_in)
    kf = WeightsFilter(state=state0, P_cov=P0, Q=Q, R=R, anchor=anchor_pos)

    rows = []
    for x in log_prices.to_numpy():
        state_prior, _ = kf.predict()
        step = kf.update(x)
        beta_prior, c_prior = beta_from_state(state_prior, anchor_pos)
        beta_post, c_post = beta_from_state(step["state_post"], anchor_pos)
        rows.append({
            **{f"beta_{t}": b for t, b in zip(tickers, beta_post)},
            **{f"beta_prior_{t}": b for t, b in zip(tickers, beta_prior)},
            "intercept": c_post,
            "intercept_prior": c_prior,
            **{f"gain_{n}": k for n, k in zip(state_names, step["gain"])},
            **{f"var_post_{n}": v for n, v in zip(state_names, np.diag(step["P_post"]))},
            "ect_dynamic": step["innov"],
            "innov_var": step["innov_var"],
        })
    out = pd.DataFrame(rows, index=log_prices.index)
    out["innov_norm"] = out["ect_dynamic"] / np.sqrt(out["innov_var"])
    out["absorption"] = 1.0 - R / out["innov_var"]
    out["burn_in"] = np.arange(len(out)) < burn_in
    return out


def static_ect(log_prices: pd.DataFrame, beta: np.ndarray, intercept: float) -> pd.Series:
    """ECT estático con el β̃ y la c de Johansen congelados en train: β̃ᵀ ln P_t − c (para comparar)."""
    return pd.Series(log_prices.to_numpy() @ np.asarray(beta) - intercept, index=log_prices.index, name="ect_static")


def absorbed_fraction(absorption: pd.Series, half_life: float, trade_half_lives: float = TRADE_HALF_LIVES) -> float:
    """Fracción de una desviación que el filtro absorbe (moviendo β̂ y ĉ) durante una operación típica.

    Cada día el filtro mueve su ajuste C_t ẑ en C_t K_t · ỹ_t, así que una desviación que no se corrige por precios
    se absorbe a la tasa w = C_t K_t. En una operación de `trade_half_lives` vidas medias se absorbe
    1 − (1 − w̄)^{días}, con w̄ la mediana de C_t K_t.
    """
    days = trade_half_lives * half_life
    return float(1.0 - (1.0 - absorption.median()) ** days)


def calibrate_q(train_log_prices: pd.DataFrame, anchor: str, beta0: np.ndarray, intercept0: float,
                residual_var: float, half_life: float, tolerance: float = ABSORPTION_TOLERANCE,
                burn_in: int = BURN_IN, bounds: tuple[float, float] = Q_SEARCH_BOUNDS, iterations: int = 40) -> float:
    """Elige q (Q = q · I) SOLO con entrenamiento: el mayor q cuyo filtro absorbe a lo más `tolerance` de una
    desviación durante una operación típica (separación de escalas de tiempo).

    Por qué este criterio y no máxima verosimilitud: la verosimilitud premia que ỹ_t sea ruido blanco, y eso se
    logra moviendo β̂ y ĉ hasta "perseguir" el spread; el ECT revertiría por construcción (lo mueve el filtro, no
    los precios) y no habría nada que operar. Aquí la deriva de los pesos debe ser lenta frente a la reversión
    que se quiere operar (vida media de Johansen en train).

    Parámetros:
        train_log_prices: log-precios de ENTRENAMIENTO del grupo.
        half_life: vida media del spread de Johansen en train (días).
        tolerance, burn_in, bounds, iterations: criterio, días excluidos y búsqueda por bisección en log10(q).
    Retorna:
        q calibrado. La fracción absorbida crece con q, por eso basta una bisección.
    """
    def absorbed(q: float) -> float:
        out = run_weights_filter(train_log_prices, anchor, beta0, intercept0, q, residual_var, burn_in)
        return absorbed_fraction(out.loc[~out["burn_in"], "absorption"], half_life)

    lo, hi = np.log10(bounds[0]), np.log10(bounds[1])
    if absorbed(10 ** lo) > tolerance:
        raise ValueError("Ni el q mínimo cumple la tolerancia de absorción; revisar R o el rango de búsqueda")
    for _ in range(iterations):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if absorbed(10 ** mid) <= tolerance else (lo, mid)
    return float(10 ** lo)


def ect_comparison(kf1: pd.DataFrame) -> pd.DataFrame:
    """ECT estático vs dinámico por partición: media, desviación, ADF y vida media (sugerencia del profesor).

    Parámetros:
        kf1: `kf1_weights.parquet` (columnas `ect_static`, `ect_dynamic`, `split`, `burn_in`).
    Retorna:
        DataFrame con una fila por (ECT, partición). El burn-in se excluye.
    """
    rows = []
    data = kf1.loc[~kf1["burn_in"]]
    for column in ("ect_static", "ect_dynamic"):
        for split, part in data.groupby("split", sort=False):
            series = part[column]
            stat, pvalue = adf_pvalue(series)
            rows.append({"ect": column.removeprefix("ect_"), "split": split, "mean": float(series.mean()),
                         "std": float(series.std()), "adf_stat": stat, "adf_pvalue": pvalue,
                         "half_life": compute_half_life(series)})
    return pd.DataFrame(rows)
