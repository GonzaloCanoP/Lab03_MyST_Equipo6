"""Vista ejecutiva del dashboard (JME): qué tan bien le fue a la estrategia y cuánto costó.

Paneles (checklist de `docs/instrucciones/08_dashboard.md`):
    1) Curva de capital con drawdown (por partición o encadenada)

La cinta de arriba es la tarjeta de la partición elegida (TODO = total encadenado), leída de `metrics.json`. Todo sale
de los artefactos; lo único que se agrega aquí son sumas y productos de esas series para el rango elegido.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from dashboard import theme
from performance.metrics import daily_returns, drawdown

HEIGHT = 300
PLOTLY_CONFIG = {"displaylogo": False, "scrollZoom": True, "modeBarButtonsToRemove": ["select2d", "lasso2d"]}
METRICS_KEY = {"TODO": "total", "TRAIN": "train", "TEST": "test", "VALID": "validation"}  # tecla → metrics.json
EQUITY_MODES = ("POR PARTICIÓN", "ENCADENADA")


def _window(frame: pd.DataFrame | pd.Series, start: pd.Timestamp, end: pd.Timestamp):
    """Recorta una serie de tiempo al rango [start, end]."""
    return frame.loc[(frame.index >= start) & (frame.index <= end)]


def _show(fig: go.Figure, height: int = HEIGHT, per_row: int = 2) -> None:
    """Dibuja la figura con la leyenda en su propio espacio (`theme.fit_legend`)."""
    theme.fit_legend(fig, height, per_row)
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)


def selected_partition() -> str:
    """Llave de `metrics.json` de la partición elegida arriba (TODO → "total")."""
    return METRICS_KEY[st.session_state.get("range") or "TODO"]


def money(value: float) -> str:
    """$ con separador de miles y signo explícito: +$205,075 / −$3,188."""
    return f"{'+' if value >= 0 else '−'}${abs(value):,.0f}"


def tape_cells(metrics: dict, partition: str) -> list[tuple[str, str, str]]:
    """Tarjeta de la partición elegida: rendimiento, razones de riesgo, caída máxima y operaciones."""
    m = metrics[partition]
    label = "TOTAL" if partition == "total" else theme.SPLIT_LABEL[partition]

    def tone(value: float) -> str:
        return "up" if value > 0 else "down"

    return [
        ("TRAMO", f"{label} {m['start']} → {m['end']}", "v"),
        ("REND. NETO", f"{m['net_return']:+.1%}", tone(m["net_return"])),
        ("CAGR", f"{m['cagr']:+.2%}", tone(m["cagr"])),
        ("SHARPE", f"{m['sharpe']:.2f}", tone(m["sharpe"])),
        ("SORTINO", f"{m['sortino']:.2f}", tone(m["sortino"])),
        ("CALMAR", f"{m['calmar']:.2f}", tone(m["calmar"])),
        ("MDD", f"{m['max_drawdown']:.1%} ({m['max_drawdown_days']}d)", "down"),
        ("WIN RATE", f"{m['win_rate']:.0%}", "v"),
        ("PROFIT F.", f"{m['profit_factor']:.2f}", tone(m["profit_factor"] - 1)),
        ("OPERACIONES", f"{m['n_trades']}", "v"),
    ]


def equity_series(equity: pd.DataFrame, mode: str) -> tuple[pd.Series, pd.Series]:
    """Curva de capital y su drawdown.

    POR PARTICIÓN: la del backtest (cada partición arranca con el capital inicial, como la figura 7).
    ENCADENADA: los rendimientos diarios de las tres particiones compuestos desde el capital inicial (la misma serie
    que usa la columna "total" de `metrics.json`).
    """
    if mode == "ENCADENADA":
        curve = equity["equity"].iloc[0] * (1.0 + daily_returns(equity)).cumprod()
        return curve.rename("equity"), drawdown(curve)
    return equity["equity"], equity["drawdown"]


def equity_panel(data: dict, start, end, mode: str) -> None:
    """1) Curva de capital (arriba) y drawdown bajo el máximo previo (abajo)."""
    full = data["equity_curve"]
    curve, dd = equity_series(full, mode)
    curve, dd, split = _window(curve, start, end), _window(dd, start, end), _window(full["split"], start, end)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
    theme.shade_splits(fig, split, row=1, col=1)
    theme.shade_splits(fig, split, row=2, col=1)
    # Por partición la curva se reinicia: un trazo por partición para no unir el final de una con el inicio de otra.
    segments = [("", curve)] if mode == "ENCADENADA" else list(curve.groupby(split, sort=False))
    for i, (_, seg) in enumerate(segments):
        fig.add_trace(go.Scatter(x=seg.index, y=seg, name="capital", legendgroup="capital", showlegend=i == 0,
                                 line={"color": theme.AMBER, "width": 1.5},
                                 hovertemplate="$%{y:,.0f}<extra>capital</extra>"), row=1, col=1)
    fig.add_hline(y=full["equity"].iloc[0], line={"color": theme.MUTED, "dash": "dot", "width": 1}, row=1, col=1,
                  annotation_text="capital inicial", annotation_font={"color": theme.MUTED, "size": 9},
                  annotation_position="bottom right")
    fig.add_trace(go.Scatter(x=dd.index, y=dd, name="drawdown", fill="tozeroy", fillcolor="rgba(230,103,103,0.25)",
                             line={"color": theme.DOWN, "width": 1}, hovertemplate="%{y:.2%}<extra>drawdown</extra>"),
                  row=2, col=1)
    fig.update_yaxes(title_text="capital ($)", tickformat="$,.0f", row=1, col=1)
    fig.update_yaxes(title_text="drawdown", tickformat=".0%", row=2, col=1)
    _show(fig, height=380, per_row=4)


def render(data: dict, start: pd.Timestamp, end: pd.Timestamp) -> None:
    """Dibuja la vista ejecutiva para el rango de fechas [start, end]."""
    metrics = data["metrics"]
    theme.ticker_tape(tape_cells(metrics, selected_partition()))

    theme.panel_title(1, "Curva de capital y drawdown",
                      "por partición: cada una arranca con $1,000,000 (figura 7); encadenada: las tres seguidas")
    mode = st.segmented_control("Curva", EQUITY_MODES, default=EQUITY_MODES[0], key="equity_mode") or EQUITY_MODES[0]
    equity_panel(data, start, end, mode)
