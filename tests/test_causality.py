"""Prueba 1 (§3.11), causalidad: z_t y la señal de t no cambian si el pipeline se recalcula con datos solo hasta t.

Se recalcula todo lo que viene después de los datos limpios: Johansen del grupo y normalización, calibración y corrida
del filtro 1, calibración y corrida del filtro 2, VECM, grid search de umbrales y regla de señales. Las fechas t son
posteriores al fin de train (2020-11-19): si algo usara datos de prueba o validación para calibrar, o si un filtro
mirara hacia adelante, el valor en t cambiaría al quitar el futuro.

Supuestos: las fechas de corte del split están congeladas en `artifacts/split_dates.json` (son fechas de calendario,
no se recalculan con la muestra truncada) y el grupo elegido en la parte 02 sale de un embudo que solo usa train.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from cointegration.selection import describe_chosen_group
from data.split import add_split_column, load_split_dates, slice_split
from kalman.signal_filter import calibrate_signal_filter, run_signal_filter
from kalman.weights_filter import calibrate_q, run_weights_filter, static_ect
from strategy.optimization import best_rule, grid_search
from strategy.signals import build_signals
from strategy.vecm import fit_vecm

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"
# Tres fechas después del fin de train: inicio de prueba, mitad de validación y casi el final de la muestra.
CUTOFFS = ("2021-03-15", "2024-06-14", "2026-09-15")


def run_pipeline(prices: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Recalcula desde los precios limpios del grupo hasta las señales (mismas funciones y orden que `main.py`)."""
    dates = load_split_dates(ARTIFACTS / "split_dates.json")
    universe = json.loads((ARTIFACTS / "johansen_summary.json").read_text())["universe"]
    tickers = list(prices.columns)
    train = slice_split(prices, dates, "train")
    summary, _ = describe_chosen_group(train, tickers, universe)
    beta = np.array([summary["beta_normalized"][t] for t in tickers])
    intercept, anchor = summary["intercept_c"], summary["anchor"]

    log_prices = np.log(prices)
    log_train = slice_split(log_prices, dates, "train")
    residual_var = float(static_ect(log_train, beta, intercept).var(ddof=0))
    q = calibrate_q(log_train, anchor, beta, intercept, residual_var, summary["half_life_days"])
    kf1 = add_split_column(run_weights_filter(log_prices, anchor, beta, intercept, q, residual_var), dates)

    active = kf1.loc[~kf1["burn_in"]]
    kf2_params = calibrate_signal_filter(active.loc[active["split"] == "train", "ect_dynamic"])
    kf2 = run_signal_filter(active["ect_dynamic"], *(kf2_params[k] for k in ("phi", "q_mu", "q_x", "r")))
    kf2["split"] = active["split"]

    vecm = fit_vecm(log_train, summary["k_ar_diff"], anchor, summary["beta_normalized"])
    on = kf2.loc[~kf2["burn_in"] & (kf2["split"] == "train")]
    grid = grid_search(prices.loc[on.index], on["zscore"], kf1.loc[on.index, [f"beta_{t}" for t in tickers]],
                       summary["half_life_days"])
    rule = best_rule(grid)
    calibration = {"q": q, **kf2_params, "beta_alpha": vecm["beta_alpha"], **rule.to_dict()}
    return build_signals(kf2, kf1, tickers, rule), calibration


@pytest.fixture(scope="module")
def prices() -> pd.DataFrame:
    group = pd.read_parquet(ARTIFACTS / "prices.parquet")
    return group.drop(columns="split")


@pytest.fixture(scope="module")
def full_run(prices):
    return run_pipeline(prices)


@pytest.mark.parametrize("cutoff", CUTOFFS)
def test_zscore_and_signal_do_not_use_future_data(prices, full_run, cutoff):
    """Con datos solo hasta t: misma calibración, mismo z_t y misma señal en t (y en todos los días anteriores)."""
    full_signals, full_calibration = full_run
    t = pd.Timestamp(cutoff)
    assert t > pd.Timestamp("2020-11-19") and t in full_signals.index
    truncated_signals, truncated_calibration = run_pipeline(prices.loc[:t])

    assert truncated_calibration == full_calibration
    assert truncated_signals.index[-1] == t
    assert truncated_signals.loc[t, "zscore"] == full_signals.loc[t, "zscore"]
    assert truncated_signals.loc[t, "signal"] == full_signals.loc[t, "signal"]
    pd.testing.assert_frame_equal(truncated_signals, full_signals.loc[:t])


def test_pipeline_matches_artifacts(full_run):
    """El pipeline recalculado en la prueba es el mismo que escribió `main.py` (z con diferencias < 1e-6 por redondeo)."""
    full_signals, _ = full_run
    stored = pd.read_parquet(ARTIFACTS / "signals.parquet")
    assert (stored["signal"] == full_signals["signal"]).all()
    np.testing.assert_allclose(stored["zscore"], full_signals["zscore"], rtol=0, atol=1e-6)
