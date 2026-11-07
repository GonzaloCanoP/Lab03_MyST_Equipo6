"""Dashboard del Lab03 (Streamlit): `streamlit run dashboard/app.py` desde la raíz del repositorio.

Solo lee `artifacts/` (lo escribe `python main.py`); no recalcula nada. Dos vistas como "teclas de función":
F1 ejecutiva (JME) y F2 técnica (GC). El rango de fechas de arriba aplica a todas las gráficas.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # para importar `dashboard.*` desde la raíz

from dashboard import executive, technical, theme  # noqa: E402
from dashboard.data import require_artifacts  # noqa: E402

RANGES = {"TODO": None, "TRAIN": "train", "TEST": "test", "VALID": "validation"}


def select_range(data: dict) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Selector de rango común: partición (TODO / TRAIN / TEST / VALID) y un ajuste fino de fechas dentro de ella."""
    signals = data["signals"]
    left, right = st.columns([1, 3], gap="small")
    with left:
        choice = st.segmented_control("Partición", list(RANGES), default="TODO", key="range") or "TODO"
    dates = signals.index if RANGES[choice] is None else signals.index[signals["split"] == RANGES[choice]]
    lo, hi = dates[0].to_pydatetime(), dates[-1].to_pydatetime()
    with right:
        start, end = st.slider("Rango de fechas", min_value=lo, max_value=hi, value=(lo, hi), format="YYYY-MM-DD",
                               key=f"dates_{choice}")
    return pd.Timestamp(start), pd.Timestamp(end)


def main() -> None:
    st.set_page_config(page_title="Lab03 · Arbitraje estadístico", layout="wide", initial_sidebar_state="collapsed")
    theme.apply_page_style()
    data = require_artifacts()
    summary = data["johansen_summary"]
    group = "-".join(summary["tickers"])
    theme.command_bar(f"{group} EQUITY STAT-ARB",
                      f"ITESO · MyST · Equipo 6 · datos al {data['signals'].index[-1]:%Y-%m-%d}")
    start, end = select_range(data)
    tab_exec, tab_tech = st.tabs(["F1 EJECUTIVA", "F2 TÉCNICA"])
    with tab_exec:
        executive.render(data, start, end)
    with tab_tech:
        technical.render(data, start, end)


main()
