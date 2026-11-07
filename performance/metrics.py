"""Métricas de desempeño (parte 07, §3.9): funciones puras sobre la curva de capital y la bitácora del backtest.

Convenciones (definiciones en `docs/decisiones.md`, 2026-11-07):
    - Rendimientos diarios simples netos de costos, calculados DENTRO de cada partición (cada una arranca con el
      capital inicial; no hay rendimiento entre el último día de una y el primero de la siguiente).
    - Tasa libre de riesgo RISK_FREE_RATE anual (0: el efectivo del backtest no genera intereses) y anualización
      con TRADING_DAYS.
    - "Total" = rendimientos de las tres particiones encadenados.

    Sharpe   = √252 · media(r − r_f/252) / desv(r − r_f/252)                  (desviación muestral, ddof = 1)
    Sortino  = √252 · media(r − r_f/252) / DD,   DD = √(media(min(r − r_f/252, 0)²))   (todos los días)
    CAGR     = (V_final / V_inicial)^(252 / días) − 1
    Calmar   = CAGR / |MDD|
    MDD      = min_t (V_t / max_{s ≤ t} V_s − 1);  duración = racha más larga bajo el máximo previo (días hábiles)
    Win rate = fracción de operaciones con P&L neto > 0;  Profit factor = Σ ganancias / |Σ pérdidas|
"""

import numpy as np
import pandas as pd
from scipy.stats import jarque_bera, kurtosis, skew

# --- Parámetros de este módulo (tabla de parámetros en CLAUDE.md) ---
TRADING_DAYS = 252
RISK_FREE_RATE = 0.0
ROLLING_WINDOW = 252  # ventana del Sharpe móvil (un año bursátil)


def sharpe(returns: pd.Series, risk_free: float = RISK_FREE_RATE, periods: int = TRADING_DAYS) -> float:
    """Sharpe anualizado: √periods · media(r_t − r_f / periods) / desv(r_t), con desviación muestral (ddof = 1).

    Retorna NaN si la serie no tiene variación (p. ej. nunca hubo posición).
    """
    excess = returns - risk_free / periods
    sd = excess.std(ddof=1)
    if not np.isfinite(sd) or sd == 0:
        return float("nan")
    return float(np.sqrt(periods) * excess.mean() / sd)


def sortino(returns: pd.Series, risk_free: float = RISK_FREE_RATE, periods: int = TRADING_DAYS) -> float:
    """Sortino anualizado: como el Sharpe, pero solo castiga la volatilidad a la baja.

    DD = √(media(min(r_t − r_f / periods, 0)²)) sobre TODOS los días (los positivos cuentan como 0), objetivo = r_f.
    Retorna inf si nunca hubo un día negativo y NaN si la serie está vacía.
    """
    excess = returns - risk_free / periods
    if excess.empty:
        return float("nan")
    downside = float(np.sqrt(np.mean(np.minimum(excess.to_numpy(), 0.0) ** 2)))
    if downside == 0:
        return float("inf")
    return float(np.sqrt(periods) * excess.mean() / downside)


def drawdown(equity: pd.Series) -> pd.Series:
    """Drawdown diario: V_t / max_{s ≤ t} V_s − 1 (≤ 0)."""
    return equity / equity.cummax() - 1.0


def max_drawdown(equity: pd.Series) -> float:
    """Caída máxima de la curva de capital desde su máximo previo (número negativo, p. ej. −0.065)."""
    return float(drawdown(equity).min())


def drawdown_duration(equity: pd.Series) -> int:
    """Racha más larga, en días hábiles, con el capital por debajo de su máximo previo.

    Cuenta desde el día siguiente al pico hasta el día anterior a recuperarlo (o hasta el final si no se recupera).
    """
    underwater = (drawdown(equity) < 0).to_numpy()
    longest = current = 0
    for below in underwater:
        current = current + 1 if below else 0
        longest = max(longest, current)
    return int(longest)


def cagr(equity: pd.Series, periods: int = TRADING_DAYS) -> float:
    """Rendimiento anual compuesto: (V_final / V_inicial)^(periods / días) − 1, con días = observaciones − 1."""
    days = len(equity) - 1
    if days <= 0:
        return float("nan")
    return float((equity.iloc[-1] / equity.iloc[0]) ** (periods / days) - 1.0)


def calmar(equity: pd.Series, periods: int = TRADING_DAYS) -> float:
    """Calmar = CAGR / |MDD| sobre el mismo tramo. Retorna inf si no hubo drawdown."""
    mdd = max_drawdown(equity)
    if mdd == 0:
        return float("inf")
    return float(cagr(equity, periods) / abs(mdd))


def win_rate(trade_pnl: pd.Series) -> float:
    """Fracción de operaciones con P&L neto positivo. NaN si no hubo operaciones."""
    if trade_pnl.empty:
        return float("nan")
    return float((trade_pnl > 0).mean())


def profit_factor(trade_pnl: pd.Series) -> float:
    """Σ ganancias / |Σ pérdidas| de las operaciones (P&L neto). inf si no hubo pérdidas, NaN sin operaciones."""
    if trade_pnl.empty:
        return float("nan")
    losses = -trade_pnl[trade_pnl < 0].sum()
    if losses == 0:
        return float("inf")
    return float(trade_pnl[trade_pnl > 0].sum() / losses)


def daily_returns(equity: pd.DataFrame) -> pd.Series:
    """Rendimientos diarios netos, calculados dentro de cada partición (columna `split` de `equity_curve.parquet`).

    El primer día de cada partición vale 0: el capital se reinicia y no hay rendimiento entre particiones.
    """
    return (equity.groupby("split", sort=False)["equity"].pct_change().fillna(0.0)).rename("return")


def rolling_sharpe(returns: pd.Series, window: int = ROLLING_WINDOW, risk_free: float = RISK_FREE_RATE,
                   periods: int = TRADING_DAYS) -> pd.Series:
    """Sharpe anualizado en una ventana móvil de `window` días (causal: cada valor usa solo los días anteriores).

    NaN hasta tener la ventana completa.
    """
    excess = returns - risk_free / periods
    roll = excess.rolling(window, min_periods=window)
    return (np.sqrt(periods) * roll.mean() / roll.std(ddof=1)).rename(f"rolling_sharpe_{window}")


def trade_returns(trades: pd.DataFrame, equity: pd.DataFrame) -> pd.Series:
    """Rendimiento de cada operación = P&L neto / capital al cierre del día anterior a la entrada.

    Ese capital es la base del sizing (V_t antes de operar). Si la operación abre el primer día de la partición, se
    usa el capital de ese día.
    """
    base = {}
    for split, part in equity.groupby("split", sort=False):
        base[split] = part["equity"].shift(1).fillna(part["equity"])
    bases = [base[s].loc[pd.Timestamp(d)] for s, d in zip(trades["split"], trades["entry_date"])]
    return (trades["net_pnl"].to_numpy() / np.array(bases, dtype=float))


def summarize(returns: pd.Series, equity: pd.Series, trade_pnl: pd.Series, trade_ret: np.ndarray) -> dict:
    """Todas las métricas de un tramo: rendimientos diarios, curva de capital y P&L por operación."""
    ret = np.asarray(trade_ret, dtype=float)
    has_trades = len(ret) >= 3
    return {
        "start": equity.index[0].strftime("%Y-%m-%d"),
        "end": equity.index[-1].strftime("%Y-%m-%d"),
        "days": len(equity),
        "net_return": float(equity.iloc[-1] / equity.iloc[0] - 1.0),
        "cagr": cagr(equity),
        "volatility": float(returns.std(ddof=1) * np.sqrt(TRADING_DAYS)),
        "sharpe": sharpe(returns),
        "sortino": sortino(returns),
        "calmar": calmar(equity),
        "max_drawdown": max_drawdown(equity),
        "max_drawdown_days": drawdown_duration(equity),
        "n_trades": len(trade_pnl),
        "win_rate": win_rate(trade_pnl),
        "profit_factor": profit_factor(trade_pnl),
        "avg_trade_return": float(ret.mean()) if len(ret) else float("nan"),
        "trade_return_std": float(ret.std(ddof=1)) if len(ret) > 1 else float("nan"),
        "trade_return_skew": float(skew(ret)) if has_trades else float("nan"),
        "trade_return_kurtosis": float(kurtosis(ret, fisher=False)) if has_trades else float("nan"),
        "trade_return_jarque_bera_p": float(jarque_bera(ret).pvalue) if has_trades else float("nan"),
    }


def compute_metrics(equity: pd.DataFrame, trades: pd.DataFrame, initial_capital: float | None = None) -> dict:
    """Métricas por partición y del total (`metrics.json`).

    Parámetros:
        equity: `equity_curve.parquet` (columnas `equity` y `split`, índice de fechas).
        trades: `trades.csv` (`entry_date`, `net_pnl`, `split`).
        initial_capital: capital del que parte la curva total encadenada (por defecto, el del primer día).
    Retorna:
        dict {partición: métricas, ..., "total": métricas}. El total encadena los rendimientos diarios de las
        particiones (una sola curva que arranca con el capital inicial) y usa todas las operaciones.
    """
    returns = daily_returns(equity)
    trade_ret = trade_returns(trades, equity)
    out = {}
    for split, part in equity.groupby("split", sort=False):
        mask = (trades["split"] == split).to_numpy()
        out[split] = summarize(returns.loc[part.index], part["equity"], trades.loc[mask, "net_pnl"], trade_ret[mask])
    start = equity["equity"].iloc[0] if initial_capital is None else initial_capital
    chained = start * (1.0 + returns).cumprod()
    out["total"] = summarize(returns, chained, trades["net_pnl"], trade_ret)
    return out
