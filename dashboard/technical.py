"""Vista técnica del dashboard (GC): cómo se construye la señal, panel por panel.

Paneles (checklist de `docs/instrucciones/08_dashboard.md`):
    1) Spread (ECT dinámico) con entradas y salidas     2) z-score prior con umbrales
    3) β̂_t por activo (filtro 1)                        4) Primer eigenvector de Johansen móvil
    5) Ganancia de Kalman de ambos filtros               6) Varianza posterior de ambos filtros
    7) Sharpe neto móvil de 252 días
Todos leen artefactos ya calculados y responden al mismo rango de fechas.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from dashboard import theme

HEIGHT = 300  # alto del área de datos; la leyenda se suma arriba (theme.fit_legend)
PLOTLY_CONFIG = {"displaylogo": False, "scrollZoom": True, "modeBarButtonsToRemove": ["select2d", "lasso2d"]}
EXIT_STYLE = {  # forma + color: el motivo nunca depende solo del color. (símbolo, color, leyenda corta, hover)
    "salida": ("circle", theme.NEUTRAL, "reversión", "salida por reversión"),
    "stop": ("x", theme.DOWN, "stop", "stop"),
    "holding": ("square", theme.SERIES[1], "holding", "holding máximo"),
    "fin_particion": ("diamond", theme.MUTED, "forzada", "cierre forzado al final de la partición"),
}


def _window(frame: pd.DataFrame | pd.Series, start: pd.Timestamp, end: pd.Timestamp):
    """Recorta una serie de tiempo al rango [start, end]."""
    return frame.loc[(frame.index >= start) & (frame.index <= end)]


def _show(fig: go.Figure, height: int = HEIGHT, per_row: int = 2) -> None:
    """Dibuja la figura con la leyenda en su propio espacio (`theme.fit_legend`): `per_row` entradas por renglón."""
    theme.fit_legend(fig, height, per_row)
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)


def ticker_colors(tickers: list[str]) -> dict:
    """Color fijo por activo en todos los paneles (orden del grupo: GLD, GDX, B)."""
    return {t: theme.SERIES[i % len(theme.SERIES)] for i, t in enumerate(tickers)}


def tape_cells(data: dict, end: pd.Timestamp) -> list[tuple[str, str, str]]:
    """Celdas de la cinta: estado de la estrategia al final del rango elegido y métricas totales."""
    signals = data["signals"].loc[:end]
    last = signals.iloc[-1]
    summary, strategy, total = data["johansen_summary"], data["params"]["strategy"], data["metrics"]["total"]
    position = {1: ("LARGO ▲", "up"), -1: ("CORTO ▼", "down"), 0: ("PLANO ■", "v")}[int(last["signal"])]
    betas = [(f"β̂ {t}", f"{last[f'beta_{t}']:+.3f}", "v") for t in summary["tickers"] if t != summary["anchor"]]
    return [
        ("FECHA", signals.index[-1].strftime("%Y-%m-%d"), "v"),
        ("Z", f"{last['zscore']:+.2f}", "v"),
        ("POS", *position),
        *betas,
        ("θ", f"{strategy['z_entry']:g}/{strategy['z_exit']:g}/{strategy['z_stop']:g}/{strategy['max_holding']}d", "v"),
        ("VIDA MEDIA", f"{summary['half_life_days']:.1f}d", "v"),
        ("SHARPE TOT", f"{total['sharpe']:.2f}", "up" if total["sharpe"] > 0 else "down"),
        ("MDD TOT", f"{total['max_drawdown']:.1%}", "down"),
    ]


def spread_panel(data: dict, start, end) -> None:
    """1) ECT dinámico del filtro 1 con la media prior del filtro 2 y las operaciones (entrada y salida)."""
    kf2 = _window(data["kf2_signal"].loc[~data["kf2_signal"]["burn_in"]], start, end)
    trades = data["trades"]
    trades = trades[(trades["entry_date"] <= end) & (trades["exit_date"] >= start)]
    fig = go.Figure()
    theme.shade_splits(fig, kf2["split"])
    fig.add_trace(go.Scatter(x=kf2.index, y=kf2["ect"], name="ECT dinámico", line={"color": theme.AMBER, "width": 1.2}))
    fig.add_trace(go.Scatter(x=kf2.index, y=kf2["mu_prior"], name="μ prior filtro 2",
                             line={"color": theme.SERIES[0], "width": 1.6}))
    ect = data["kf2_signal"]["ect"]
    for direction, symbol, color, label in ((1, "triangle-up", theme.UP, "entrada largo ▲"),
                                            (-1, "triangle-down", theme.DOWN, "entrada corto ▼")):
        sel = trades[(trades["direction"] == direction) & trades["entry_date"].between(start, end)]
        fig.add_trace(go.Scatter(x=sel["entry_date"], y=ect.reindex(sel["entry_date"]).to_numpy(), mode="markers",
                                 name=label, marker={"symbol": symbol, "size": 10, "color": color,
                                                     "line": {"color": theme.BLACK, "width": 1}}))
    for reason, (symbol, color, label, hover) in EXIT_STYLE.items():
        sel = trades[(trades["exit_reason"] == reason) & trades["exit_date"].between(start, end)]
        if sel.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sel["exit_date"], y=ect.reindex(sel["exit_date"]).to_numpy(), mode="markers", name=f"salida: {label}",
            marker={"symbol": symbol, "size": 9, "color": color, "line": {"color": theme.BLACK, "width": 1}},
            customdata=sel[["net_pnl", "days"]].to_numpy(),
            hovertemplate="P&L neto %{customdata[0]:,.0f} · %{customdata[1]} días<extra>" + hover + "</extra>"))
    fig.update_yaxes(title_text="ECT (log)")
    _show(fig)


def zscore_panel(data: dict, start, end) -> None:
    """2) z-score prior (la señal) con las bandas de entrada, salida y stop congeladas desde train."""
    sig = _window(data["signals"], start, end)
    s = data["params"]["strategy"]
    fig = go.Figure()
    theme.shade_splits(fig, sig["split"])
    fig.add_trace(go.Scatter(x=sig.index, y=sig["zscore"], name="z_t prior", line={"color": theme.AMBER, "width": 1.1}))
    for level, dash, color, label in ((s["z_entry"], "dash", theme.YELLOW, "entrada"),
                                      (s["z_exit"], "dot", theme.NEUTRAL, "salida"),
                                      (s["z_stop"], "dash", theme.DOWN, "stop")):
        for sign in (1, -1) if level else (1,):
            fig.add_hline(y=sign * level, line={"color": color, "dash": dash, "width": 1},
                          annotation_text=f"{label} {sign * level:+g}", annotation_position="top right",
                          annotation_font={"color": color, "size": 9})
    fig.update_yaxes(title_text="z", range=[-max(5, s["z_stop"] + 1), max(5, s["z_stop"] + 1)])
    _show(fig)


def weights_panel(data: dict, start, end) -> None:
    """3) β̂_t posterior del filtro 1 por activo (el ancla vale +1) contra el β̃ estático de Johansen en train."""
    kf1 = _window(data["kf1_weights"].loc[~data["kf1_weights"]["burn_in"]], start, end)
    summary = data["johansen_summary"]
    colors = ticker_colors(summary["tickers"])
    free = [t for t in summary["tickers"] if t != summary["anchor"]]
    # Un renglón por activo: cada peso con su propia escala, para que se vea su deriva (en un solo eje se ven planos).
    fig = make_subplots(rows=len(free), cols=1, shared_xaxes=True, vertical_spacing=0.08)
    for row, t in enumerate(free, start=1):
        theme.shade_splits(fig, kf1["split"], row=row, col=1)
        fig.add_trace(go.Scatter(x=kf1.index, y=kf1[f"beta_{t}"], name=f"β {t}", line={"color": colors[t], "width": 1.6}),
                      row=row, col=1)
        fig.add_hline(y=summary["beta_normalized"][t], line={"color": colors[t], "dash": "dot", "width": 1},
                      annotation_text=f"Johansen {summary['beta_normalized'][t]:+.3f}",
                      annotation_font={"color": colors[t], "size": 9}, annotation_position="top left", row=row, col=1)
        fig.update_yaxes(title_text=f"β {t}", row=row, col=1)
    _show(fig)


def eigenvector_panel(data: dict, start, end) -> None:
    """4) Primer eigenvector de Johansen móvil (504 días, paso 21) y su significancia (traza / crítico 95 %)."""
    roll = _window(data["rolling_eigenvector"], start, end)
    summary = data["johansen_summary"]
    colors = ticker_colors(summary["tickers"])
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35], vertical_spacing=0.06)
    theme.shade_splits(fig, roll["split"], row=1, col=1)
    theme.shade_splits(fig, roll["split"], row=2, col=1)
    for t in summary["tickers"]:
        anchor = t == summary["anchor"]
        fig.add_trace(go.Scatter(x=roll.index, y=roll[t], name=f"β {t}" + (" (ancla)" if anchor else ""),
                                 mode="lines+markers", marker={"size": 4},
                                 line={"color": colors[t], "width": 1.4, "dash": "dash" if anchor else "solid"}),
                      row=1, col=1)
    ratio = roll["trace_0"] / roll["trace_cv95_0"]
    fig.add_trace(go.Scatter(x=roll.index, y=ratio, name="traza / crítico 95 %", line={"color": theme.AMBER, "width": 1.3}),
                  row=2, col=1)
    fig.add_hline(y=1, line={"color": theme.DOWN, "dash": "dash", "width": 1}, row=2, col=1)
    fig.update_yaxes(title_text="β (ancla = +1)", range=[-3, 3], row=1, col=1)
    fig.update_yaxes(title_text="traza/crít.", row=2, col=1)
    _show(fig)


def _two_filter_panel(data: dict, start, end, prefix: str, kf1_title: str, kf2_title: str, log: bool) -> None:
    """Paneles 5 y 6: la misma cantidad (`gain_` o `var_post_`) del filtro 1 (arriba) y del filtro 2 (abajo)."""
    kf1 = _window(data["kf1_weights"].loc[~data["kf1_weights"]["burn_in"]], start, end)
    kf2 = _window(data["kf2_signal"].loc[~data["kf2_signal"]["burn_in"]], start, end)
    summary = data["johansen_summary"]
    colors = {"c": theme.NEUTRAL, **ticker_colors(summary["tickers"])}
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08)
    theme.shade_splits(fig, kf1["split"], row=1, col=1)
    theme.shade_splits(fig, kf2["split"], row=2, col=1)
    for state in ["c"] + [t for t in summary["tickers"] if t != summary["anchor"]]:
        y = kf1[f"{prefix}{state}"]
        fig.add_trace(go.Scatter(x=kf1.index, y=y.abs() if log else y, name=f"KF1 {state}",
                                 line={"color": colors[state], "width": 1.3}), row=1, col=1)
    for state, color, label in (("mu", theme.AMBER, "KF2 μ (media)"), ("x", theme.SERIES[0], "KF2 x (desviación)")):
        fig.add_trace(go.Scatter(x=kf2.index, y=kf2[f"{prefix}{state}"], name=label,
                                 line={"color": color, "width": 1.3, "dash": "dot" if state == "x" else "solid"}),
                      row=2, col=1)
    fig.update_yaxes(title_text=kf1_title, row=1, col=1, type="log" if log else "linear", exponentformat="e")
    fig.update_yaxes(title_text=kf2_title, row=2, col=1, type="log" if log else "linear")
    _show(fig)


def gain_panel(data: dict, start, end) -> None:
    """5) Ganancia de Kalman K_t: componentes del filtro 1 (c, β) y del filtro 2 (μ, x)."""
    _two_filter_panel(data, start, end, "gain_", "K_t filtro 1", "K_t filtro 2", log=False)


def variance_panel(data: dict, start, end) -> None:
    """6) Varianza posterior (diagonal de P_{t|t}) de ambos filtros, en escala log."""
    _two_filter_panel(data, start, end, "var_post_", "P_t|t filtro 1", "P_t|t filtro 2", log=True)


def rolling_sharpe_panel(data: dict, start, end) -> None:
    """7) Sharpe neto móvil de 252 días con el Sharpe de cada partición completa como referencia."""
    eq = _window(data["equity_curve"], start, end)
    fig = go.Figure()
    theme.shade_splits(fig, eq["split"])
    fig.add_trace(go.Scatter(x=eq.index, y=eq["rolling_sharpe_252"], name="Sharpe neto móvil 252d",
                             line={"color": theme.AMBER, "width": 1.3}))
    for split in eq["split"].unique():
        dates = eq.index[eq["split"] == split]
        value = data["metrics"][split]["sharpe"]
        fig.add_trace(go.Scatter(x=[dates[0], dates[-1]], y=[value, value], mode="lines",
                                 name=f"Sharpe {theme.SPLIT_LABEL[split]} {value:.2f}",
                                 line={"color": theme.NEUTRAL, "dash": "dash", "width": 1}, showlegend=False,
                                 hovertemplate=f"Sharpe {theme.SPLIT_LABEL[split]} completo: {value:.2f}<extra></extra>"))
        fig.add_annotation(x=dates[0], y=value, text=f"{theme.SPLIT_LABEL[split]} {value:.2f}", showarrow=False,
                           xanchor="left", yanchor="bottom", font={"color": theme.NEUTRAL, "size": 9})
    fig.add_hline(y=0, line={"color": theme.MUTED, "width": 1})
    fig.update_yaxes(title_text="Sharpe anualizado")
    _show(fig, height=300, per_row=4)


def render(data: dict, start: pd.Timestamp, end: pd.Timestamp) -> None:
    """Dibuja la vista técnica completa para el rango de fechas [start, end]."""
    theme.ticker_tape(tape_cells(data, end))
    left, right = st.columns(2, gap="small")
    with left:
        theme.panel_title(1, "Spread y señales", "ECT dinámico del filtro 1, media prior del filtro 2, entradas ▲▼ y salidas por motivo")
        spread_panel(data, start, end)
        theme.panel_title(3, "β̂_t por activo (filtro 1)", "pesos posteriores (GDX = +1, ancla); punteado = β̃ de Johansen en train")
        weights_panel(data, start, end)
        theme.panel_title(5, "Ganancia de Kalman", "arriba: K_t del filtro 1 (c y pesos); abajo: K_t del filtro 2 (μ y x)")
        gain_panel(data, start, end)
    with right:
        theme.panel_title(2, "z-score y umbrales", "z prior (calculado antes de actualizar el filtro 2); θ congelado desde train")
        zscore_panel(data, start, end)
        theme.panel_title(4, "Eigenvector de Johansen móvil", "ventana de 504 días, paso 21; abajo: arriba de 1 rechaza r = 0")
        eigenvector_panel(data, start, end)
        theme.panel_title(6, "Varianza posterior", "diagonal de P_t|t en escala log (incertidumbre de cada estado)")
        variance_panel(data, start, end)
    theme.panel_title(7, "Sharpe móvil 252 días", "punteado: Sharpe de la partición completa")
    rolling_sharpe_panel(data, start, end)
