"""Prueba obligatoria 3 (§3.11): contabilidad multi-pata del backtest.

- equity = cash + Σ valor de las patas en cada día, y ΔV = P&L bruto − comisiones − préstamo.
- Costo total = Σ (nocional operado por pata × comisión) + devengo diario del préstamo sobre los cortos.
- Caso de juguete de 2 patas calculado a mano, y caso aleatorio de 4 patas con rebalanceo diario.
"""

import numpy as np
import pandas as pd
import pytest

from backtest.costs import BORROW_RATE_ANNUAL, COMMISSION, TRADING_DAYS
from backtest.engine import run_backtest

SEED = 42
CAPITAL = 1_000_000.0


def make_signals(index: pd.DatetimeIndex, signal: list[int], betas: dict[str, float]) -> pd.DataFrame:
    """Señales con pesos constantes β por activo."""
    return pd.DataFrame({"signal": signal, **{f"beta_{t}": b for t, b in betas.items()}}, index=index)


@pytest.fixture
def random_case() -> tuple[pd.DataFrame, pd.DataFrame]:
    """4 patas, 300 días, precios lognormales, señales que abren, cierran y cambian de dirección, β que deriva."""
    rng = np.random.default_rng(SEED)
    index = pd.bdate_range("2020-01-01", periods=300)
    tickers = ["A", "B", "C", "D"]
    prices = pd.DataFrame(50 * np.exp(np.cumsum(rng.normal(0, 0.015, (300, 4)), axis=0)), index=index, columns=tickers)
    signal = np.repeat(rng.choice([-1, 0, 1], size=30), 10)
    betas = {t: b + 0.001 * np.cumsum(rng.normal(size=300)) for t, b in zip(tickers, [1.0, -0.6, 0.4, -0.35])}
    betas["A"] = np.ones(300)
    return prices, pd.DataFrame({"signal": signal, **{f"beta_{t}": b for t, b in betas.items()}}, index=index)


def test_toy_two_legs_by_hand():
    """2 patas, β = (1, −1): señal +1 al cierre del día 0 → abre el día 1, señal 0 el día 1 → cierra el día 2."""
    index = pd.bdate_range("2024-01-01", periods=4)
    prices = pd.DataFrame({"A": [100.0, 110.0, 120.0, 120.0], "B": [50.0, 50.0, 40.0, 40.0]}, index=index)
    signals = make_signals(index, [1, 0, 0, 0], {"A": 1.0, "B": -1.0})
    result = run_backtest(prices, signals)
    eq = result.equity

    # Día 1: N = 0.8 · 1,000,000 · 1/2 = 400,000 por pata; largo A, corto B.
    q_a, q_b = 400_000 / 110, -400_000 / 50
    entry_commission = COMMISSION * 800_000
    assert eq.loc[index[1], "shares_A"] == pytest.approx(q_a)
    assert eq.loc[index[1], "shares_B"] == pytest.approx(q_b)
    assert eq.loc[index[1], "commission"] == pytest.approx(entry_commission)
    assert eq.loc[index[1], "equity"] == pytest.approx(CAPITAL - entry_commission)
    assert eq.loc[index[0], "direction"] == 0  # la señal del día 0 NO se ejecuta el día 0

    # Día 2: P&L bruto, préstamo sobre la pata corta mantenida y comisión de salida de ambas patas.
    gross = q_a * (120 - 110) + q_b * (40 - 50)
    borrow = BORROW_RATE_ANNUAL / TRADING_DAYS * abs(q_b) * 40
    exit_commission = COMMISSION * (abs(q_a) * 120 + abs(q_b) * 40)
    assert eq.loc[index[2], "gross_pnl"] == pytest.approx(gross)
    assert eq.loc[index[2], "borrow"] == pytest.approx(borrow)
    assert eq.loc[index[2], "commission"] == pytest.approx(exit_commission)
    final = CAPITAL + gross - entry_commission - exit_commission - borrow
    assert eq["equity"].iloc[-1] == pytest.approx(final)
    assert eq.loc[index[2], "cash"] == pytest.approx(final)  # sin posiciones, todo es efectivo

    trade = result.trades.iloc[0]
    assert len(result.trades) == 1 and trade["direction"] == 1 and trade["days"] == 1
    assert trade["commission"] == pytest.approx(entry_commission + exit_commission)
    assert trade["net_pnl"] == pytest.approx(final - CAPITAL)
    assert trade["exit_reason"] == "salida"


def test_equity_identity_every_day(random_case):
    """equity = cash + Σ patas y ΔV = bruto − comisión − préstamo en CADA día."""
    prices, signals = random_case
    eq = run_backtest(prices, signals).equity
    legs = eq[[f"value_{t}" for t in prices.columns]].sum(axis=1)
    np.testing.assert_allclose(eq["equity"], eq["cash"] + legs, rtol=0, atol=1e-6)
    np.testing.assert_allclose(eq["equity"].diff().iloc[1:], eq["net_pnl"].iloc[1:], rtol=0, atol=1e-6)
    np.testing.assert_allclose(eq["equity"].iloc[0], CAPITAL - eq["commission"].iloc[0])


def test_costs_equal_commission_per_leg_plus_borrow(random_case):
    """Comisión total = 0.125 % × nocional operado sumado pata por pata; préstamo = devengo diario de los cortos."""
    prices, signals = random_case
    eq = run_backtest(prices, signals).equity
    shares = eq[[f"shares_{t}" for t in prices.columns]].to_numpy()
    P = prices.to_numpy()
    traded = np.diff(np.vstack([np.zeros(shares.shape[1]), shares]), axis=0)
    expected_commission = COMMISSION * np.sum(np.abs(traded) * P)
    held_short = np.abs(np.minimum(shares[:-1], 0)) * P[1:]  # cortos mantenidos de t − 1 a t, valuados en t
    expected_borrow = BORROW_RATE_ANNUAL / TRADING_DAYS * held_short.sum()
    assert eq["commission"].sum() == pytest.approx(expected_commission)
    assert eq["borrow"].sum() == pytest.approx(expected_borrow)
    # Atribución: bruto = neto + comisiones + préstamo, y la bitácora cuadra con la curva.
    assert eq["gross_pnl"].sum() == pytest.approx(eq["net_pnl"].sum() + expected_commission + expected_borrow)


def test_trade_log_matches_equity_curve(random_case):
    """Cada operación cierra antes del final del rango y la suma de la bitácora es la de la curva de capital."""
    prices, signals = random_case
    result = run_backtest(prices, signals)
    eq, trades = result.equity, result.trades
    assert eq["direction"].iloc[-1] == 0 and (eq[[f"shares_{t}" for t in prices.columns]].iloc[-1] == 0).all()
    for column in ("gross_pnl", "commission", "borrow", "net_pnl"):
        assert trades[column].sum() == pytest.approx(eq[column].sum())
    assert eq["equity"].iloc[-1] == pytest.approx(CAPITAL + trades["net_pnl"].sum())


def test_sizing_uses_80_percent_and_beta_signs(random_case):
    """Al abrir, el nocional bruto es 80 % del capital disponible y el signo de cada pata es dirección × sgn(β)."""
    prices, signals = random_case
    eq = run_backtest(prices, signals).equity
    opened = eq["direction"].ne(eq["direction"].shift(fill_value=0)) & eq["direction"].ne(0)
    for date in eq.index[opened]:
        t = eq.index.get_loc(date)
        values = eq.loc[date, [f"value_{tk}" for tk in prices.columns]].to_numpy()
        before = eq["equity"].iloc[t] + eq["commission"].iloc[t]  # V_t antes de pagar la comisión del día
        assert np.abs(values).sum() == pytest.approx(0.8 * before)
        beta = signals[[f"beta_{tk}" for tk in prices.columns]].iloc[t - 1].to_numpy()  # pesos del día de decisión
        assert (np.sign(values) == eq.loc[date, "direction"] * np.sign(beta)).all()


def test_rebalance_band_reduces_trading(random_case):
    """Banda 0 rebalancea cada día con posición; una banda enorme no rebalancea nunca (solo entradas y salidas)."""
    prices, signals = random_case
    daily = run_backtest(prices, signals, {"rebalance_band": 0.0})
    frozen = run_backtest(prices, signals, {"rebalance_band": 1e9})
    assert daily.trades["n_rebalances"].sum() > 0
    assert frozen.trades["n_rebalances"].sum() == 0
    assert frozen.equity["commission"].sum() < daily.equity["commission"].sum()
