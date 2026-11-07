"""Métricas de desempeño (parte 07): cada métrica contra un caso con resultado conocido, calculado a mano."""

import numpy as np
import pandas as pd
import pytest

from performance.metrics import (cagr, calmar, compute_metrics, daily_returns, drawdown_duration, max_drawdown,
                                 profit_factor, rolling_sharpe, sharpe, sortino, trade_returns, win_rate)

DAYS = pd.bdate_range("2024-01-01", periods=5)


def test_sharpe_known_case():
    r = pd.Series([0.01, -0.01, 0.02, 0.0])
    # media 0.005, desv muestral √(0.00025 / 3 · … ) calculada explícitamente
    expected = np.sqrt(252) * r.mean() / r.std(ddof=1)
    assert sharpe(r) == pytest.approx(expected)
    assert np.isnan(sharpe(pd.Series([0.0, 0.0, 0.0])))


def test_sortino_uses_downside_deviation_over_all_days():
    r = pd.Series([0.02, -0.01, 0.03, -0.02])
    downside = np.sqrt((0.01 ** 2 + 0.02 ** 2) / 4)  # los días positivos cuentan como 0
    assert sortino(r) == pytest.approx(np.sqrt(252) * r.mean() / downside)
    assert sortino(pd.Series([0.01, 0.02])) == np.inf  # sin días negativos


def test_max_drawdown_and_duration():
    equity = pd.Series([100.0, 120.0, 90.0, 110.0, 125.0, 100.0], index=pd.bdate_range("2024-01-01", periods=6))
    assert max_drawdown(equity) == pytest.approx(90 / 120 - 1)  # −25 %
    # Bajo el máximo: días 2–3 (recupera en el día 4, 2 días) y el día 5 (sigue abajo al final, 1 día)
    assert drawdown_duration(equity) == 2
    assert drawdown_duration(pd.Series([1.0, 2.0, 3.0])) == 0


def test_cagr_and_calmar():
    equity = pd.Series(np.linspace(100, 121, 505))  # 504 días = 2 años de 252
    assert cagr(equity) == pytest.approx(0.10)  # 1.21 = 1.1²
    falling = pd.Series([100.0, 80.0, 88.0])
    expected = (0.88 ** (252 / 2) - 1) / 0.20
    assert calmar(falling) == pytest.approx(expected)


def test_win_rate_and_profit_factor():
    pnl = pd.Series([100.0, -50.0, 30.0, -20.0])
    assert win_rate(pnl) == pytest.approx(0.5)
    assert profit_factor(pnl) == pytest.approx(130 / 70)
    assert profit_factor(pd.Series([10.0, 5.0])) == np.inf
    assert np.isnan(win_rate(pd.Series(dtype=float)))


def test_daily_returns_restart_each_split():
    equity = pd.DataFrame({"equity": [100.0, 110.0, 100.0, 105.0, 84.0],
                           "split": ["train", "train", "test", "test", "test"]}, index=DAYS)
    r = daily_returns(equity)
    # el primer día de cada partición es 0: el capital se reinicia, no hay rendimiento entre particiones
    assert r.tolist() == pytest.approx([0.0, 0.10, 0.0, 0.05, -0.20])


def test_rolling_sharpe_needs_full_window():
    r = pd.Series(np.tile([0.01, -0.005], 5), index=pd.bdate_range("2024-01-01", periods=10))
    rs = rolling_sharpe(r, window=4)
    assert rs.iloc[:3].isna().all()
    assert rs.iloc[3] == pytest.approx(sharpe(r.iloc[:4]))
    assert rs.iloc[-1] == pytest.approx(sharpe(r.iloc[-4:]))


def test_trade_return_uses_equity_before_entry():
    equity = pd.DataFrame({"equity": [1000.0, 990.0, 1050.0, 1040.0, 1040.0], "split": "train"}, index=DAYS)
    trades = pd.DataFrame({"entry_date": [DAYS[1]], "net_pnl": [40.0], "split": ["train"]})
    # base = capital al cierre del día anterior a la entrada (1000), que es el que usa el sizing
    assert trade_returns(trades, equity).tolist() == pytest.approx([0.04])


def test_compute_metrics_by_split_and_total():
    equity = pd.DataFrame({"equity": [100.0, 110.0, 100.0, 90.0, 99.0],
                           "split": ["train", "train", "test", "test", "test"]}, index=DAYS)
    trades = pd.DataFrame({"entry_date": [DAYS[0], DAYS[2]], "net_pnl": [10.0, -1.0], "split": ["train", "test"]})
    out = compute_metrics(equity, trades)
    assert set(out) == {"train", "test", "total"}
    assert out["train"]["net_return"] == pytest.approx(0.10)
    assert out["test"]["net_return"] == pytest.approx(-0.01)
    assert out["test"]["max_drawdown"] == pytest.approx(-0.10)
    # total: 1.10 · 0.99 encadenado
    assert out["total"]["net_return"] == pytest.approx(1.10 * 0.99 - 1)
    assert out["total"]["n_trades"] == 2
    assert out["total"]["win_rate"] == pytest.approx(0.5)
