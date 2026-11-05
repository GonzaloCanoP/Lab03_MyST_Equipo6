"""Motor del backtest multi-pata con costos (§3.8): contabilidad diaria exacta por pata.

Línea de tiempo de cada día t (precios de cierre P_t):

    1. Valuación: P&L bruto_t = Σ_i q_i (P_{i,t} − P_{i,t−1}) con las acciones que se traían de t − 1.
    2. Préstamo: se devenga sobre las patas cortas que se mantuvieron de t − 1 a t (`backtest/costs.py`).
    3. Ejecución al cierre de t de la señal decidida en t − `execution_lag` (por defecto 1: la señal del cierre de
       t − 1 se opera al cierre de t; ver `docs/decisiones.md`). Se compra o vende hasta las acciones objetivo de
       `strategy/sizing.py` y se paga comisión por pata sobre lo operado.
    4. Identidad contable: equity_t = cash_t + Σ_i q_i P_{i,t}, y equity_t − equity_{t−1} = bruto − comisión − préstamo.

Rebalanceo mientras la posición sigue abierta en la misma dirección: el objetivo cambia con β̂ y con V_t. Con
`rebalance_band = 0` se rebalancea cada día; con banda b > 0 una pata solo se opera si su nocional se aleja más de
b (fracción) de su objetivo. El último día del rango se cierra todo (`fin_particion`).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from backtest.costs import BORROW_RATE_ANNUAL, COMMISSION, TRADING_DAYS, borrow_cost, commission_cost
from strategy.sizing import INITIAL_CAPITAL, POSITION_FRACTION, target_shares

# --- Parámetros por defecto del motor (se pueden cambiar en `params`) ---
EXECUTION_LAG = 1  # días entre la decisión (cierre de t) y la ejecución (cierre de t + 1)
REBALANCE_BAND = 0.0  # 0 = rebalanceo diario
END_OF_RANGE_REASON = "fin_particion"

DEFAULT_PARAMS = {
    "initial_capital": INITIAL_CAPITAL,
    "position_fraction": POSITION_FRACTION,
    "commission": COMMISSION,
    "borrow_rate": BORROW_RATE_ANNUAL,
    "trading_days": TRADING_DAYS,
    "execution_lag": EXECUTION_LAG,
    "rebalance_band": REBALANCE_BAND,
}


@dataclass(frozen=True)
class BacktestResult:
    """Salida de `run_backtest`.

    Atributos:
        equity: una fila por día con `equity`, `cash`, `value_<T>` y `shares_<T>` por pata, `direction`,
            `gross_pnl`, `commission`, `borrow`, `net_pnl`, `traded_notional`, `drawdown`.
        trades: una fila por operación (de la apertura al cierre de una dirección) con `entry_date`, `exit_date`,
            `direction`, `days`, `gross_pnl`, `commission`, `borrow`, `net_pnl`, `n_rebalances`, `exit_reason`.
        params: parámetros usados (los por defecto más los que se pasaron).
    """

    equity: pd.DataFrame
    trades: pd.DataFrame
    params: dict

    @property
    def net_returns(self) -> pd.Series:
        """Rendimientos diarios netos de costos de la curva de capital (para Sharpe y demás métricas)."""
        return self.equity["equity"].pct_change().fillna(0.0)


def _rebalance_mask(current: np.ndarray, target: np.ndarray, prices: np.ndarray, band: float) -> np.ndarray:
    """Patas que se operan en un rebalanceo: todas si band = 0; si no, las que se alejan más de `band` del objetivo."""
    if band <= 0:
        return np.ones(len(target), dtype=bool)
    target_notional = np.abs(target) * prices
    deviation = np.abs(current - target) * prices
    return deviation > band * target_notional


def run_backtest(prices: pd.DataFrame, signals: pd.DataFrame, params: dict | None = None) -> BacktestResult:
    """Simula la estrategia sobre el rango de `prices` (ya recortado: train, prueba, validación o cualquier tramo).

    Parámetros:
        prices: precios (no log) de los activos del grupo, una columna por ticker, índice de fechas.
        signals: índice de fechas; `signal` ∈ {−1, 0, +1} (dirección objetivo decidida al cierre de ese día),
            `beta_<T>` para cada ticker de `prices` (pesos del filtro 1 en el día de la decisión) y, opcional,
            `exit_reason` (motivo de cierre que reporta la estrategia). Fechas sin señal = sin posición.
        params: cambia cualquiera de `DEFAULT_PARAMS`.
    Retorna:
        BacktestResult. Sin look-ahead: la ejecución de t usa la señal y los β̂ de t − execution_lag.
    """
    p = {**DEFAULT_PARAMS, **(params or {})}
    tickers = list(prices.columns)
    lag = int(p["execution_lag"])

    # Señal y pesos del día de la decisión, desplazados al día de ejecución.
    beta_cols = [f"beta_{t}" for t in tickers]
    decided = signals.reindex(prices.index)
    direction = decided["signal"].fillna(0).astype(int).shift(lag, fill_value=0).to_numpy().copy()
    betas = decided[beta_cols].shift(lag).to_numpy()
    reasons = (decided["exit_reason"] if "exit_reason" in decided else pd.Series("", index=prices.index))
    reasons = reasons.fillna("").astype(str).shift(lag, fill_value="").to_numpy()
    if np.isnan(betas[direction != 0]).any():
        raise ValueError("Hay días con señal distinta de cero y sin pesos β̂ (columnas beta_<T>)")
    direction[-1] = 0  # el último día del rango se cierra todo

    P = prices.to_numpy(dtype=float)
    T, n = P.shape
    shares = np.zeros(n)
    cash = float(p["initial_capital"])
    current_dir = 0
    rows, trades = [], []
    trade = None

    for t in range(T):
        price = P[t]
        gross = float(shares @ (price - P[t - 1])) if t > 0 else 0.0
        borrow = borrow_cost(shares, price, p["borrow_rate"], p["trading_days"]) if t > 0 else 0.0
        cash -= borrow
        equity_before = cash + float(shares @ price)  # V_t antes de operar: base del sizing

        new_dir = int(direction[t])
        closing = current_dir != 0 and new_dir != current_dir
        opening = new_dir != 0 and new_dir != current_dir
        target = (target_shares(new_dir, betas[t], price, equity_before, p["position_fraction"])
                  if new_dir != 0 else np.zeros(n))

        # La operación vigente se queda con el P&L y el préstamo de haber mantenido las patas de t − 1 a t.
        if trade is not None:
            trade["gross_pnl"] += gross
            trade["borrow"] += borrow

        if closing or opening:
            # Cierre completo de la dirección anterior y/o apertura de la nueva: cada pata paga su comisión.
            exit_commission = commission_cost(-shares, price, p["commission"]) if closing else 0.0
            open_commission = commission_cost(target, price, p["commission"]) if opening else 0.0
            traded = target - shares
            commission = exit_commission + open_commission
        else:
            # Misma dirección: rebalanceo hacia el objetivo (diario o solo las patas fuera de la banda).
            mask = _rebalance_mask(shares, target, price, p["rebalance_band"]) if new_dir != 0 else np.zeros(n, bool)
            traded = np.where(mask, target - shares, 0.0)
            commission = commission_cost(traded, price, p["commission"])

        cash -= float(traded @ price) + commission
        shares = shares + traded

        if closing:
            trade["commission"] += exit_commission
            trade["exit_date"] = prices.index[t]
            trade["days"] = t - trade.pop("_entry_t")
            if reasons[t]:
                trade["exit_reason"] = reasons[t]
            elif t == T - 1:
                trade["exit_reason"] = END_OF_RANGE_REASON
            else:
                trade["exit_reason"] = "cambio_direccion" if opening else "salida"
            trades.append(trade)
            trade = None
        if opening:
            trade = {"entry_date": prices.index[t], "_entry_t": t, "direction": new_dir, "gross_pnl": 0.0,
                     "commission": open_commission, "borrow": 0.0, "n_rebalances": 0}
        elif trade is not None and np.any(traded != 0):
            trade["commission"] += commission
            trade["n_rebalances"] += 1
        current_dir = new_dir

        rows.append({
            "equity": cash + float(shares @ price),
            "cash": cash,
            **{f"value_{tk}": float(s * pr) for tk, s, pr in zip(tickers, shares, price)},
            **{f"shares_{tk}": float(s) for tk, s in zip(tickers, shares)},
            "direction": current_dir,
            "gross_pnl": gross,
            "commission": commission,
            "borrow": borrow,
            "net_pnl": gross - commission - borrow,
            "traded_notional": float(np.sum(np.abs(traded) * price)),
        })

    equity = pd.DataFrame(rows, index=prices.index)
    equity["drawdown"] = equity["equity"] / equity["equity"].cummax() - 1.0
    trade_table = pd.DataFrame(trades, columns=["entry_date", "exit_date", "direction", "days", "gross_pnl", "commission",
                                        "borrow", "n_rebalances", "exit_reason"])
    trade_table.insert(trade_table.columns.get_loc("n_rebalances"), "net_pnl",
                       trade_table["gross_pnl"] - trade_table["commission"] - trade_table["borrow"])
    return BacktestResult(equity=equity, trades=trade_table, params=p)
