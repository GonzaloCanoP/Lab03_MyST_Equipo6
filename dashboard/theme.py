"""Estilo del dashboard, inspirado en una terminal financiera: fondo negro, texto ámbar, tipografía monoespaciada,
paneles densos con barra de título y "teclas de función". Lo usan ambas vistas (ejecutiva y técnica).

Colores de series validados para daltonismo y contraste sobre el fondo negro (`docs/decisiones.md`, 2026-11-07):
los tres primeros colores categóricos pasan todas las parejas (ΔE CVD ≥ 9.4, visión normal ≥ 20.9, contraste ≥ 3:1).
El ámbar es para texto, marcos y series únicas; nunca para distinguir series entre sí. Ganancia/pérdida y largo/corto
siempre llevan forma o signo además del color (triángulos, ▲/▼), así que el color nunca es la única pista.
"""

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# --- Paleta ---
BLACK = "#000000"
PANEL = "#0A0A0A"
BORDER = "#2E2E2E"
GRID = "#1C1C1C"
AMBER = "#FFA028"       # texto principal, títulos, serie única
YELLOW = "#FFD200"      # teclas de función
TEXT = "#E6E6E6"
MUTED = "#8C8C8C"
UP = "#199e70"          # ganancia / largo (siempre con ▲ o triángulo hacia arriba)
DOWN = "#e66767"        # pérdida / corto / stop (siempre con ▼, X o triángulo hacia abajo)
SERIES = ["#3987e5", "#d95926", "#199e70"]  # categóricos en orden fijo: azul, naranja, aqua
NEUTRAL = "#BDBDBD"     # serie de referencia (intercepto, estático, umbral)

# Partición: sombreado muy tenue para no competir con los datos.
SPLIT_FILL = {"train": "rgba(57,135,229,0.07)", "test": "rgba(255,160,40,0.07)", "validation": "rgba(25,158,112,0.08)"}
SPLIT_LABEL = {"train": "TRAIN", "test": "TEST", "validation": "VALID"}

FONT = "IBM Plex Mono, Menlo, Consolas, monospace"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&display=swap');
html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {{
    background-color: {BLACK} !important; color: {TEXT}; font-family: {FONT};
}}
[data-testid="stAppViewContainer"] * {{ font-family: {FONT}; }}
.block-container {{ padding-top: 3.2rem; padding-bottom: 1rem; max-width: 100%; }}
[data-testid="stHeader"] {{ height: 2.4rem; border-bottom: 1px solid {BORDER}; }}
[data-testid="stAppDeployButton"] {{ display: none; }}
/* Controles en ámbar (Streamlit los pinta con su color primario) */
[data-baseweb="slider"] [role="slider"] {{ background-color: {AMBER} !important; box-shadow: none !important; }}
[data-baseweb="slider"] > div > div > div {{ background: {AMBER} !important; }}
[data-testid="stSliderThumbValue"], [data-testid="stSliderTickBarMin"], [data-testid="stSliderTickBarMax"]
    {{ color: {AMBER} !important; }}
[data-testid="stButtonGroup"] button {{ border-radius: 0 !important; border-color: {BORDER} !important;
    background: {PANEL} !important; }}
/* Tecla activa: Streamlit 1.66 la marca con aria-checked (ya no con kind="...Active") */
[data-testid="stButtonGroup"] button[aria-checked="true"] {{ background: {AMBER} !important;
    border-color: {AMBER} !important; }}
[data-testid="stButtonGroup"] button[aria-checked="true"] p {{ color: {BLACK} !important; font-weight: 700; }}
[data-testid="stWidgetLabel"] p {{ color: {MUTED} !important; font-size: 0.75rem; text-transform: uppercase; }}
h1, h2, h3, h4, p, span, label, div {{ color: {TEXT}; }}
.cmdbar {{ display: flex; justify-content: space-between; align-items: center; background: {PANEL};
    border: 1px solid {BORDER}; padding: 6px 10px; margin-bottom: 6px; font-size: 0.95rem; }}
.cmdbar .cmd {{ color: {AMBER}; font-weight: 700; letter-spacing: 0.04em; }}
.cmdbar .go {{ background: {YELLOW}; color: {BLACK}; font-weight: 700; padding: 0 6px; margin-left: 6px; }}
.cmdbar .meta {{ color: {MUTED}; }}
.tape {{ display: flex; flex-wrap: wrap; gap: 0; border: 1px solid {BORDER}; margin-bottom: 8px; }}
.tape .cell {{ padding: 4px 12px; border-right: 1px solid {BORDER}; font-size: 0.85rem; white-space: nowrap; }}
.tape .k {{ color: {MUTED}; margin-right: 6px; }}
.tape .v {{ color: {AMBER}; font-weight: 600; }}
.tape .up {{ color: {UP}; font-weight: 600; }}
.tape .down {{ color: {DOWN}; font-weight: 600; }}
.panel-title {{ background: {AMBER}; color: {BLACK} !important; font-weight: 700; font-size: 0.8rem;
    padding: 2px 8px; margin: 6px 0 0 0; letter-spacing: 0.05em; }}
.panel-note {{ color: {MUTED} !important; font-size: 0.75rem; margin: 2px 0 4px 0; }}
/* Pestañas como teclas de función */
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
.stTabs [data-baseweb="tab"] {{ background: {YELLOW} !important; color: {BLACK}; font-weight: 700; padding: 4px 14px;
    border-radius: 0; height: auto; }}
.stTabs [data-baseweb="tab"] p {{ color: {BLACK} !important; font-weight: 700; }}
.stTabs [aria-selected="true"] {{ background: {AMBER} !important; outline: 2px solid {TEXT}; }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display: none; }}
[data-testid="stPlotlyChart"] {{ border: 1px solid {BORDER}; }}
/* Tabla de métricas de la vista ejecutiva */
.mtable {{ width: 100%; border-collapse: collapse; border: 1px solid {BORDER}; background: {PANEL}; font-size: 0.8rem; }}
.mtable th, .mtable td {{ padding: 3px 10px; border-bottom: 1px solid {GRID}; text-align: right; white-space: nowrap; }}
.mtable th {{ color: {MUTED}; font-weight: 600; }}
.mtable td:first-child, .mtable th:first-child {{ text-align: left; color: {MUTED}; }}
.mtable td {{ color: {AMBER}; }}
.mtable .sel {{ background: rgba(255,160,40,0.12); }}
.mtable th.sel {{ color: {AMBER}; }}
.mtable .up {{ color: {UP}; }}
.mtable .down {{ color: {DOWN}; }}
</style>
"""


def apply_page_style() -> None:
    """Inyecta el CSS de la terminal y registra la plantilla de Plotly. Llamar una vez al inicio de la app."""
    st.markdown(CSS, unsafe_allow_html=True)
    pio.templates["terminal"] = _plotly_template()
    pio.templates.default = "terminal"


def _plotly_template() -> go.layout.Template:
    """Plantilla de Plotly: fondo negro, rejilla discreta, texto en tipografía monoespaciada, hover en ámbar."""
    axis = {"gridcolor": GRID, "zerolinecolor": BORDER, "linecolor": BORDER, "tickfont": {"color": MUTED, "size": 10},
            "title": {"font": {"color": MUTED, "size": 11}}, "showspikes": True, "spikecolor": MUTED,
            "spikethickness": 1, "spikedash": "dot", "spikemode": "across"}
    return go.layout.Template(layout={
        "paper_bgcolor": PANEL, "plot_bgcolor": PANEL,
        "font": {"family": FONT, "color": TEXT, "size": 11},
        "colorway": SERIES,
        "xaxis": axis, "yaxis": axis,
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.0, "xanchor": "left", "x": 0,
                   "font": {"size": 10, "color": TEXT}, "bgcolor": "rgba(0,0,0,0)"},
        "hoverlabel": {"bgcolor": BLACK, "bordercolor": AMBER, "font": {"family": FONT, "color": AMBER, "size": 11}},
        "hovermode": "x unified",
        "margin": {"l": 50, "r": 12, "t": 28, "b": 30},
    })


LEGEND_ROW_PX = 20   # alto de un renglón de leyenda
LEGEND_PAD_PX = 10   # aire entre la leyenda y el área de datos


def fit_legend(fig: go.Figure, height: int, per_row: int = 2) -> None:
    """Reserva arriba del área de datos el espacio exacto de la leyenda, para que nunca tape las series.

    Cada entrada ocupa 1 / `per_row` del ancho (`entrywidthmode = "fraction"`), así que el número de renglones no
    depende del ancho de la pantalla: renglones = ⌈entradas / per_row⌉. El alto del área de datos queda en `height`
    y la figura crece lo que mida la leyenda.
    """
    entries = sum(1 for t in fig.data if t.showlegend is not False and t.name)
    shown = fig.layout.showlegend if fig.layout.showlegend is not None else entries > 1  # regla de Plotly
    rows = -(-entries // per_row) if shown else 0
    legend_px = rows * LEGEND_ROW_PX + (LEGEND_PAD_PX if rows else 0)
    fig.update_layout(
        height=height + legend_px,
        margin={"t": 12 + legend_px},
        legend={"orientation": "h", "x": 0, "xanchor": "left", "y": 1, "yanchor": "bottom", "yref": "paper",
                "entrywidth": 1 / per_row, "entrywidthmode": "fraction", "tracegroupgap": 0,
                "font": {"size": 9, "color": TEXT}},
    )


def command_bar(command: str, meta: str) -> None:
    """Barra superior tipo línea de comando: `COMANDO <GO>` a la izquierda y metadatos a la derecha."""
    st.markdown(f'<div class="cmdbar"><span><span class="cmd">{command}</span><span class="go">GO</span></span>'
                f'<span class="meta">{meta}</span></div>', unsafe_allow_html=True)


def ticker_tape(cells: list[tuple[str, str, str]]) -> None:
    """Cinta de indicadores. Cada celda es (etiqueta, valor, estilo) con estilo ∈ {"v", "up", "down"}."""
    html = "".join(f'<span class="cell"><span class="k">{k}</span><span class="{c}">{v}</span></span>'
                   for k, v, c in cells)
    st.markdown(f'<div class="tape">{html}</div>', unsafe_allow_html=True)


def panel_title(number: int, title: str, note: str = "") -> None:
    """Barra de título ámbar de un panel (`1) SPREAD Y SEÑALES`) y, opcional, una nota breve debajo."""
    st.markdown(f'<div class="panel-title">{number}) {title.upper()}</div>', unsafe_allow_html=True)
    if note:
        st.markdown(f'<div class="panel-note">{note}</div>', unsafe_allow_html=True)


def shade_splits(fig: go.Figure, split, row: int | None = None, col: int | None = None) -> None:
    """Sombrea en la figura el tramo de fechas de cada partición (train / test / validación)."""
    for name, fill in SPLIT_FILL.items():
        dates = split.index[split == name]
        if len(dates):
            kwargs = {"row": row, "col": col} if row is not None else {}
            fig.add_vrect(x0=dates[0], x1=dates[-1], fillcolor=fill, line_width=0, layer="below", **kwargs)
