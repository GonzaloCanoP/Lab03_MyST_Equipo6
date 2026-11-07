"""Vista ejecutiva del dashboard (JME): qué tan bien le fue a la estrategia y cuánto costó.

Paneles (checklist de `docs/instrucciones/08_dashboard.md`):
    1) Curva de capital con drawdown (por partición o encadenada)
    2) Tabla de métricas: las cuatro columnas de `metrics.json`, con la partición elegida resaltada
    3) Atribución de costos: P&L bruto → comisiones → préstamo → P&L neto en el rango elegido
    4) Rendimiento neto por año calendario
    5) Bitácora de operaciones filtrable por periodo (rango de arriba), dirección, resultado y motivo de salida

La cinta de arriba es la tarjeta de la partición elegida (TODO = total encadenado), leída de `metrics.json`. Todo sale
de los artefactos; lo único que se agrega aquí son sumas y productos de esas series para el rango elegido.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from dashboard import theme
from performance.metrics import daily_returns, drawdown, trade_returns

HEIGHT = 300
PLOTLY_CONFIG = {"displaylogo": False, "scrollZoom": True, "modeBarButtonsToRemove": ["select2d", "lasso2d"]}
METRICS_KEY = {"TODO": "total", "TRAIN": "train", "TEST": "test", "VALID": "validation"}  # tecla → metrics.json
EQUITY_MODES = ("POR PARTICIÓN", "ENCADENADA")
COLUMNS = ("train", "test", "validation", "total")
DIRECTIONS = {"AMBAS": None, "▲ LARGO": 1, "▼ CORTO": -1}
RESULTS = {"TODAS": None, "GANADORAS": True, "PERDEDORAS": False}
REASON_LABEL = {"salida": "reversión", "stop": "stop", "holding": "holding máximo", "fin_particion": "cierre forzado"}
# (etiqueta, llave de metrics.json, formato, ¿se colorea por signo?)
METRIC_ROWS = (
    ("Rendimiento neto", "net_return", "{:+.1%}", True),
    ("CAGR", "cagr", "{:+.2%}", True),
    ("Volatilidad anual", "volatility", "{:.2%}", False),
    ("Sharpe", "sharpe", "{:.2f}", True),
    ("Sortino", "sortino", "{:.2f}", True),
    ("Calmar", "calmar", "{:.2f}", True),
    ("Max drawdown", "max_drawdown", "{:.2%}", False),
    ("Duración del MDD (días)", "max_drawdown_days", "{:d}", False),
    ("Operaciones", "n_trades", "{:d}", False),
    ("Win rate", "win_rate", "{:.0%}", False),
    ("Profit factor", "profit_factor", "{:.2f}", False),
    ("Rend. medio por operación", "avg_trade_return", "{:+.2%}", True),
)


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


def metrics_table_html(metrics: dict, selected: str) -> str:
    """Tabla HTML métricas × particiones; la columna elegida va resaltada y los signos llevan color y signo."""
    def head(col: str) -> str:
        label = "TOTAL" if col == "total" else theme.SPLIT_LABEL[col]
        return f'<th class="{"sel" if col == selected else ""}">{label}</th>'

    def cell(col: str, key: str, fmt: str, signed: bool) -> str:
        value = metrics[col][key]
        tone = ("up" if value > 0 else "down") if signed else ""
        return f'<td class="{tone} {"sel" if col == selected else ""}">{fmt.format(value)}</td>'

    rows = "".join(f"<tr><td>{label}</td>{''.join(cell(c, key, fmt, signed) for c in COLUMNS)}</tr>"
                   for label, key, fmt, signed in METRIC_ROWS)
    return f'<table class="mtable"><tr><th>MÉTRICA</th>{"".join(head(c) for c in COLUMNS)}</tr>{rows}</table>'


def cost_attribution(equity: pd.DataFrame) -> dict:
    """Sumas del rango: P&L bruto, comisiones, préstamo y neto (neto = bruto − comisiones − préstamo)."""
    return {key: float(equity[key].sum()) for key in ("gross_pnl", "commission", "borrow", "net_pnl")}


def costs_panel(data: dict, start, end) -> None:
    """3) Cascada del P&L bruto al neto: cuánto se llevan las comisiones y el préstamo de los cortos."""
    c = cost_attribution(_window(data["equity_curve"], start, end))
    steps = [("P&L bruto", c["gross_pnl"], "absolute"), ("comisiones", -c["commission"], "relative"),
             ("préstamo", -c["borrow"], "relative"), ("P&L neto", c["net_pnl"], "total")]
    fig = go.Figure(go.Waterfall(
        x=[s[0] for s in steps], y=[s[1] for s in steps], measure=[s[2] for s in steps],
        text=[money(s[1]) for s in steps], textposition="outside", textfont={"color": theme.TEXT, "size": 10},
        increasing={"marker": {"color": theme.UP}}, decreasing={"marker": {"color": theme.DOWN}},
        totals={"marker": {"color": theme.AMBER}}, connector={"line": {"color": theme.MUTED, "dash": "dot", "width": 1}},
        hovertemplate="%{x}: %{text}<extra></extra>", name="P&L"))
    fig.update_yaxes(title_text="$", tickformat="$,.0f")
    fig.update_layout(hovermode="closest")
    _show(fig)
    if c["gross_pnl"] > 0:
        share = (c["commission"] + c["borrow"]) / c["gross_pnl"]
        note = (f"costos = {share:.0%} del P&L bruto (comisiones {c['commission'] / c['gross_pnl']:.0%}, "
                f"préstamo {c['borrow'] / c['gross_pnl']:.1%}); comisión 0.125 % por pata y préstamo 0.25 % anual")
    else:
        note = "sin P&L bruto positivo en el rango: la proporción de costos no aplica"
    st.markdown(f'<div class="panel-note">{note}</div>', unsafe_allow_html=True)


def yearly_returns(returns: pd.Series) -> pd.Series:
    """Rendimiento neto de cada año calendario: producto de (1 + r_t) − 1 con los rendimientos diarios del rango."""
    return (1.0 + returns).groupby(returns.index.year).prod() - 1.0


def yearly_panel(data: dict, start, end) -> None:
    """4) Barras del rendimiento neto por año; el signo va en la etiqueta además del color."""
    yearly = yearly_returns(_window(daily_returns(data["equity_curve"]), start, end))
    colors = [theme.UP if v > 0 else theme.DOWN for v in yearly]
    fig = go.Figure(go.Bar(x=yearly.index.astype(str), y=yearly, marker={"color": colors},
                           text=[f"{v:+.1%}" for v in yearly], textposition="outside",
                           textfont={"color": theme.TEXT, "size": 10}, name="rendimiento",
                           hovertemplate="%{x}: %{y:+.2%}<extra></extra>"))
    fig.add_hline(y=0, line={"color": theme.MUTED, "width": 1})
    fig.update_yaxes(title_text="rendimiento neto", tickformat=".0%")
    fig.update_xaxes(type="category")
    fig.update_layout(hovermode="closest")
    _show(fig)
    positives = int((yearly > 0).sum())
    st.markdown(f'<div class="panel-note">{positives} de {len(yearly)} años con rendimiento positivo</div>',
                unsafe_allow_html=True)


def filter_trades(trades: pd.DataFrame, start, end, direction: int | None = None, winners: bool | None = None,
                  reasons: list[str] | None = None) -> pd.DataFrame:
    """Operaciones que ENTRAN en [start, end], con filtros opcionales de dirección (1 / −1), resultado (P&L neto > 0
    o ≤ 0) y motivo de salida (`exit_reason`)."""
    keep = trades["entry_date"].between(start, end)
    if direction is not None:
        keep &= trades["direction"] == direction
    if winners is not None:
        keep &= (trades["net_pnl"] > 0) == winners
    if reasons is not None:
        keep &= trades["exit_reason"].isin(reasons)
    return trades.loc[keep]


def trade_log(trades: pd.DataFrame, equity: pd.DataFrame) -> pd.DataFrame:
    """Bitácora para mostrar: fechas, dirección con forma, días, costos, P&L neto y su rendimiento sobre el capital."""
    out = trades.assign(ret=trade_returns(trades, equity))
    return pd.DataFrame({
        "entrada": out["entry_date"].dt.strftime("%Y-%m-%d"),
        "salida": out["exit_date"].dt.strftime("%Y-%m-%d"),
        "partición": out["split"].map(theme.SPLIT_LABEL),
        "dirección": out["direction"].map({1: "▲ LARGO", -1: "▼ CORTO"}),
        "días": out["days"],
        "P&L bruto": out["gross_pnl"],
        "comisión": out["commission"],
        "préstamo": out["borrow"],
        "P&L neto": out["net_pnl"],
        "rend.": out["ret"],
        "motivo": out["exit_reason"].map(REASON_LABEL),
    })


def log_panel(data: dict, start, end) -> None:
    """5) Filtros de la bitácora y la tabla de operaciones con su resumen."""
    trades = data["trades"]
    c1, c2, c3 = st.columns([1, 1, 2], gap="small")
    with c1:
        direction = st.segmented_control("Dirección", list(DIRECTIONS), default="AMBAS", key="log_direction") or "AMBAS"
    with c2:
        result = st.segmented_control("Resultado", list(RESULTS), default="TODAS", key="log_result") or "TODAS"
    with c3:
        present = [r for r in REASON_LABEL if r in set(trades["exit_reason"])]
        reasons = st.multiselect("Motivo de salida", present, default=present, format_func=REASON_LABEL.get,
                                 key="log_reasons")
    chosen = filter_trades(trades, start, end, DIRECTIONS[direction], RESULTS[result], reasons)
    if chosen.empty:
        st.markdown('<div class="panel-note">ninguna operación cumple los filtros en este rango</div>',
                    unsafe_allow_html=True)
        return
    log = trade_log(chosen, data["equity_curve"])
    tone = lambda v: f"color: {theme.UP}" if v > 0 else f"color: {theme.DOWN}"  # noqa: E731
    styled = (log.style.format({"P&L bruto": money, "comisión": "${:,.0f}", "préstamo": "${:,.0f}", "P&L neto": money,
                                "rend.": "{:+.2%}"})
              .map(tone, subset=["P&L neto", "rend."]))
    st.dataframe(styled, hide_index=True, width="stretch", height=min(38 + 35 * len(log), 420))
    wins = (chosen["net_pnl"] > 0).mean()
    st.markdown(f'<div class="panel-note">{len(chosen)} operaciones · {wins:.0%} ganadoras · P&L neto '
                f'{money(chosen["net_pnl"].sum())} · mejor {money(chosen["net_pnl"].max())} · peor '
                f'{money(chosen["net_pnl"].min())}</div>', unsafe_allow_html=True)


def render(data: dict, start: pd.Timestamp, end: pd.Timestamp) -> None:
    """Dibuja la vista ejecutiva para el rango de fechas [start, end]."""
    metrics = data["metrics"]
    theme.ticker_tape(tape_cells(metrics, selected_partition()))

    theme.panel_title(1, "Curva de capital y drawdown",
                      "por partición: cada una arranca con $1,000,000 (figura 7); encadenada: las tres seguidas")
    mode = st.segmented_control("Curva", EQUITY_MODES, default=EQUITY_MODES[0], key="equity_mode") or EQUITY_MODES[0]
    equity_panel(data, start, end, mode)

    theme.panel_title(2, "Métricas por partición", "partición completa (metrics.json); total = las tres encadenadas; "
                      "r_f = 0, anualización 252")
    st.markdown(metrics_table_html(metrics, selected_partition()), unsafe_allow_html=True)

    left, right = st.columns(2, gap="small")
    with left:
        theme.panel_title(3, "Atribución de costos", "P&L bruto → neto en el rango de fechas elegido")
        costs_panel(data, start, end)
    with right:
        theme.panel_title(4, "Rendimiento por año", "años calendario; extremos parciales; 2020 y 2023 mezclan dos "
                          "particiones")
        yearly_panel(data, start, end)

    theme.panel_title(5, "Bitácora de operaciones", "operaciones que entran en el rango elegido; rend. = P&L neto / "
                      "capital antes de entrar")
    log_panel(data, start, end)
