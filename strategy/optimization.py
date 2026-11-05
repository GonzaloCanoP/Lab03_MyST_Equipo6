"""Grid search de θ = (z_entrada, z_salida, z_stop, k) **solo en entrenamiento** (sesión 11: ajustar la PFA en train).

Cada combinación genera las señales del tramo de train (después de ambos burn-in), corre el motor completo con costos
y rebalanceo diario y se evalúa con el Sharpe neto anualizado. La rejilla y el objetivo se registraron en
`docs/decisiones.md` antes de ver resultados. Prueba y validación no participan.
"""

import itertools

import pandas as pd

from backtest.engine import run_backtest
from kalman.signal_filter import calibrate_signal_filter, run_signal_filter
from performance.metrics import sharpe
from strategy.signals import SignalRule, build_signals, generate_signals

# --- Parámetros de este módulo (tabla de parámetros en CLAUDE.md) ---
Z_ENTRY_GRID = (1.0, 1.25, 1.5, 1.75, 2.0, 2.5)
Z_EXIT_GRID = (0.0, 0.25, 0.5)
Z_STOP_GRID = (2.5, 3.0, 3.5, 4.0)
HOLDING_K_GRID = (1, 2, 3)  # h_max = k · vida media
MIN_TRADES = 10  # menos operaciones en train no dan un Sharpe confiable
OBJECTIVE = "sharpe_net"


def holding_days(k: int, half_life: float) -> int:
    """h_max = k · vida media, redondeado a días hábiles."""
    return int(round(k * half_life))


def evaluate_rule(prices: pd.DataFrame, zscore: pd.Series, betas: pd.DataFrame, rule: SignalRule,
                  params: dict | None = None) -> dict:
    """Backtest de una regla sobre un tramo: Sharpe neto, rendimiento, operaciones y motivos de salida.

    Parámetros:
        prices: precios (no log) del tramo, mismas fechas que `zscore`.
        zscore: z_t prior del tramo, sin burn-in.
        betas: columnas `beta_<T>` del filtro 1 en esas fechas.
        params: parámetros del motor (por defecto rebalanceo diario y costos del enunciado).
    """
    signals = generate_signals(zscore, rule).join(betas)
    result = run_backtest(prices, signals, params)
    equity, trades = result.equity["equity"], result.trades
    reasons = trades["exit_reason"].value_counts()
    return {
        "sharpe_net": sharpe(result.net_returns),
        "net_return": float(equity.iloc[-1] / equity.iloc[0] - 1),
        "max_drawdown": float(result.equity["drawdown"].min()),
        "n_trades": len(trades),
        "win_rate": float((trades["net_pnl"] > 0).mean()) if len(trades) else float("nan"),
        "avg_days": float(trades["days"].mean()) if len(trades) else float("nan"),
        "commission": float(result.equity["commission"].sum()),
        "exposure": float((result.equity["direction"] != 0).mean()),
        **{f"exits_{r}": int(reasons.get(r, 0)) for r in ("salida", "stop", "holding", "fin_particion")},
    }


def grid_search(prices: pd.DataFrame, zscore: pd.Series, betas: pd.DataFrame, half_life: float,
                params: dict | None = None) -> pd.DataFrame:
    """Evalúa toda la rejilla válida (z_salida < z_entrada < z_stop) en el tramo dado, que debe ser train.

    Retorna:
        Una fila por combinación con θ, h_max, las métricas de `evaluate_rule` y `valid` (≥ MIN_TRADES operaciones),
        ordenada por el objetivo de mayor a menor (las no válidas al final). Si en train nunca se toca el stop, varias
        z_stop empatan; gana la más estricta.
    """
    rows = []
    for z_entry, z_exit, z_stop, k in itertools.product(Z_ENTRY_GRID, Z_EXIT_GRID, Z_STOP_GRID, HOLDING_K_GRID):
        if not z_exit < z_entry < z_stop:
            continue
        rule = SignalRule(z_entry, z_exit, z_stop, holding_days(k, half_life))
        rows.append({"z_entry": z_entry, "z_exit": z_exit, "z_stop": z_stop, "holding_k": k,
                     "max_holding": rule.max_holding, **evaluate_rule(prices, zscore, betas, rule, params)})
    table = pd.DataFrame(rows)
    table["valid"] = table["n_trades"] >= MIN_TRADES
    # Desempate: a igual objetivo, el stop más estricto y el holding más corto (más protección fuera de muestra).
    return (table.sort_values(["valid", OBJECTIVE, "z_stop", "holding_k"], ascending=[False, False, True, True],
                              na_position="last").reset_index(drop=True))


def best_rule(table: pd.DataFrame) -> SignalRule:
    """Regla con el mayor objetivo entre las combinaciones válidas (primera fila de `grid_search`)."""
    valid = table.loc[table["valid"]]
    if valid.empty:
        raise ValueError(f"Ninguna combinación tiene al menos {MIN_TRADES} operaciones en train")
    best = valid.iloc[0]
    return SignalRule(float(best["z_entry"]), float(best["z_exit"]), float(best["z_stop"]), int(best["max_holding"]))


def evaluate_by_split(prices: pd.DataFrame, signals: pd.DataFrame, rule: SignalRule,
                      params: dict | None = None) -> pd.DataFrame:
    """`evaluate_rule` en cada partición por separado (cada una arranca plana con el capital inicial).

    Es una vista previa para elegir y defender la regla; la evaluación oficial (equity_curve, trades, métricas) la
    hace la parte 06 con `backtest/walk_forward.py`.
    Parámetros:
        prices: precios (no log) de los activos del grupo, toda la muestra.
        signals: `signals.parquet` (o el equivalente con otro ECT), con `zscore`, `beta_<T>` y `split`.
    """
    tickers = list(prices.columns)
    beta_cols = [f"beta_{t}" for t in tickers]
    rows = []
    for split, part in signals.groupby("split", sort=False):
        rows.append({"split": split, **evaluate_rule(prices.loc[part.index], part["zscore"], part[beta_cols], rule,
                                                     params)})
    return pd.DataFrame(rows).set_index("split")


def compare_static_dynamic(prices: pd.DataFrame, kf1: pd.DataFrame, static_beta: dict, rule: SignalRule,
                           params: dict | None = None) -> pd.DataFrame:
    """Backtest con el ECT dinámico del filtro 1 contra el ECT estático de Johansen (sugerencia del profesor).

    A cada ECT se le calibra su propio filtro 2 **en train** y se le aplica la misma regla θ (la elegida con el
    dinámico). El dinámico dimensiona con β̂_t del filtro 1; el estático con el β̃ fijo de Johansen.
    Parámetros:
        prices: precios (no log) del grupo, toda la muestra.
        kf1: `kf1_weights.parquet` (`ect_dynamic`, `ect_static`, `beta_<T>`, `burn_in`, `split`).
        static_beta: β̃ de Johansen por ticker.
    Retorna:
        Una fila por (ECT, partición) con las métricas de `evaluate_rule` y los parámetros del filtro 2 de cada ECT.
    """
    tickers = list(prices.columns)
    active = kf1.loc[~kf1["burn_in"]]
    static_weights = kf1.assign(**{f"beta_{t}": static_beta[t] for t in tickers})
    tables = []
    for name, weights in (("dynamic", kf1), ("static", static_weights)):
        ect = active[f"ect_{name}"]
        kf2_params = calibrate_signal_filter(ect.loc[active["split"] == "train"])
        kf2 = run_signal_filter(ect, *(kf2_params[k] for k in ("phi", "q_mu", "q_x", "r")))
        kf2["split"] = active["split"]
        table = evaluate_by_split(prices, build_signals(kf2, weights, tickers, rule), rule, params)
        tables.append(table.assign(ect=name, kf2_phi=kf2_params["phi"],
                                   kf2_half_life=kf2_params["half_life_days"]).reset_index())
    return pd.concat(tables, ignore_index=True).set_index(["ect", "split"])
