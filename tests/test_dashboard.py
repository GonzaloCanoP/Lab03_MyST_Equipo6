"""El dashboard corre sobre los artefactos versionados sin errores y muestra sus gráficas en cada rango de partición:
7 de la vista técnica y 4 de la ejecutiva. No recalcula nada: solo lee `artifacts/`. Las funciones de la vista
ejecutiva que agregan series (costos, años, curva encadenada, filtros) se comparan con los artefactos."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from dashboard.data import ARTIFACTS, missing_artifacts
from dashboard.executive import (cost_attribution, equity_series, filter_trades, metrics_table_html, yearly_returns)
from performance.metrics import daily_returns

APP = str(Path(__file__).resolve().parents[1] / "dashboard" / "app.py")
N_CHARTS = 7 + 4  # vista técnica + vista ejecutiva (las tablas no son gráficas de Plotly)


@pytest.fixture(scope="module")
def artifacts():
    equity = pd.read_parquet(ARTIFACTS / "equity_curve.parquet")
    trades = pd.read_csv(ARTIFACTS / "trades.csv", parse_dates=["entry_date", "exit_date"])
    metrics = pd.read_json(ARTIFACTS / "metrics.json")
    return equity, trades, metrics


def test_artifacts_for_dashboard_exist():
    assert missing_artifacts() == [], "corre python main.py para generar los artefactos"


@pytest.mark.parametrize("partition", ["TODO", "TRAIN", "TEST", "VALID"])
def test_dashboard_renders_without_errors(partition):
    app = AppTest.from_file(APP, default_timeout=120).run()
    app.segmented_control(key="range").set_value(partition).run()
    assert not app.exception, [e.value for e in app.exception]
    assert not app.error, [e.value for e in app.error]
    assert len(app.get("plotly_chart")) == N_CHARTS


def test_executive_filters_and_chained_curve_render():
    app = AppTest.from_file(APP, default_timeout=120).run()
    app.segmented_control(key="equity_mode").set_value("ENCADENADA").run()
    app.segmented_control(key="log_direction").set_value("▼ CORTO").run()
    app.segmented_control(key="log_result").set_value("PERDEDORAS").run()
    assert not app.exception, [e.value for e in app.exception]
    assert len(app.get("plotly_chart")) == N_CHARTS


def test_cost_attribution_matches_trade_log(artifacts):
    equity, trades, _ = artifacts
    for split, part in equity.groupby("split"):
        costs = cost_attribution(part)
        tr = trades[trades["split"] == split]
        for key in costs:
            assert costs[key] == pytest.approx(tr[key].sum(), rel=1e-6)
        assert costs["net_pnl"] == pytest.approx(costs["gross_pnl"] - costs["commission"] - costs["borrow"], rel=1e-6)  # artefactos a 8 cifras


def test_chained_curve_and_years_match_total_return(artifacts):
    equity, _, metrics = artifacts
    curve, dd = equity_series(equity, "ENCADENADA")
    total = metrics["total"]
    assert curve.iloc[-1] / curve.iloc[0] - 1 == pytest.approx(total["net_return"], rel=1e-6)
    assert dd.min() == pytest.approx(total["max_drawdown"], rel=1e-6)
    years = yearly_returns(daily_returns(equity))
    assert np.prod(1 + years) - 1 == pytest.approx(total["net_return"], rel=1e-6)


def test_filter_trades(artifacts):
    _, trades, _ = artifacts
    start, end = trades["entry_date"].min(), trades["entry_date"].max()
    assert len(filter_trades(trades, start, end)) == len(trades)
    shorts_lost = filter_trades(trades, start, end, direction=-1, winners=False)
    assert (shorts_lost["direction"] == -1).all() and (shorts_lost["net_pnl"] <= 0).all()
    stops = filter_trades(trades, start, end, reasons=["stop"])
    assert (stops["exit_reason"] == "stop").all() and len(stops) == (trades["exit_reason"] == "stop").sum()


def test_metrics_table_marks_selected_column(artifacts):
    _, _, metrics = artifacts
    html = metrics_table_html(metrics.to_dict(), "test")
    assert '<th class="sel">TEST</th>' in html
    assert all(f'<th class="">{c}</th>' in html for c in ("TRAIN", "VALID", "TOTAL"))
