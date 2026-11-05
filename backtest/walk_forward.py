"""Evaluación walk-forward: train → prueba → validación con parámetros congelados desde train.

Cada partición se simula por separado con `run_backtest`: arranca con el capital inicial y cierra sus posiciones el
último día (decisión en `docs/decisiones.md`). Así las tres curvas de capital son comparables (figura 7) y prueba y
validación no heredan posiciones de entrenamiento. Los parámetros (umbrales, Q, R) vienen de train y no se tocan.
"""

import pandas as pd

from backtest.engine import BacktestResult, run_backtest
from data.split import SPLIT_NAMES, SplitDates, slice_split
from performance.metrics import sharpe

# --- Parámetros de este módulo ---
REBALANCE_BANDS = (0.0, 0.05, 0.10, 0.20)  # 0 = rebalanceo diario (la política evaluada); el resto, para comparar


def run_walk_forward(prices: pd.DataFrame, signals: pd.DataFrame, split_dates: SplitDates,
                     params: dict | None = None) -> dict[str, BacktestResult]:
    """Corre el backtest en cada partición con los mismos parámetros. Retorna {partición: BacktestResult}."""
    return {name: run_backtest(slice_split(prices, split_dates, name), slice_split(signals, split_dates, name), params)
            for name in SPLIT_NAMES}


def stack_results(results: dict[str, BacktestResult]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Une las particiones en una curva de capital y una bitácora, cada una con la columna `split`."""
    equity = pd.concat([r.equity.assign(split=name) for name, r in results.items()])
    trades = pd.concat([r.trades.assign(split=name) for name, r in results.items()], ignore_index=True)
    return equity, trades


def compare_rebalance(prices: pd.DataFrame, signals: pd.DataFrame, split_dates: SplitDates, params: dict | None,
                      bands: tuple[float, ...]) -> pd.DataFrame:
    """Rebalanceo diario (banda 0) contra bandas de no-rebalanceo, por partición (`rebalance_comparison.csv`).

    Retorna:
        Una fila por (banda, partición) con las columnas de `split_summary` (rendimiento y Sharpe netos, drawdown,
        costos, nocional operado, operaciones y rebalanceos).
    """
    rows = []
    for band in bands:
        results = run_walk_forward(prices, signals, split_dates, {**(params or {}), "rebalance_band": band})
        for name, result in results.items():
            eq, tr = result.equity, result.trades
            rows.append({"rebalance_band": band, "split": name, **split_summary(result)})
    return pd.DataFrame(rows)


def split_summary(result: BacktestResult) -> dict:
    """Resumen de una partición: rendimiento y Sharpe netos, drawdown máximo, P&L bruto, costos y operaciones."""
    eq, tr = result.equity, result.trades
    gross = float(eq["gross_pnl"].sum())
    commission, borrow = float(eq["commission"].sum()), float(eq["borrow"].sum())
    return {
        "net_return": float(eq["equity"].iloc[-1] / eq["equity"].iloc[0] - 1.0),
        "sharpe_net": sharpe(result.net_returns),
        "max_drawdown": float(eq["drawdown"].min()),
        "gross_pnl": gross,
        "commission": commission,
        "borrow": borrow,
        "net_pnl": gross - commission - borrow,
        "cost_share_of_gross": (commission + borrow) / gross if gross > 0 else float("nan"),
        "traded_notional": float(eq["traded_notional"].sum()),
        "n_trades": len(tr),
        "win_rate": float((tr["net_pnl"] > 0).mean()) if len(tr) else float("nan"),
        "n_rebalances": int(tr["n_rebalances"].sum()) if len(tr) else 0,
        "exposure": float((eq["direction"] != 0).mean()),
    }
