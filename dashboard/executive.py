"""Vista ejecutiva del dashboard (dueño: JME). Espacio reservado con el mismo estilo que la vista técnica.

Pendiente (checklist de `docs/instrucciones/08_dashboard.md`): curva de capital con drawdown, tarjeta de métricas,
atribución de costos, bitácora filtrable y histograma de rendimientos por operación con la normal. Usar
`dashboard.theme` (`panel_title`, `shade_splits`, plantilla de Plotly ya registrada) y los datos de `data`.
"""

import pandas as pd
import streamlit as st

from dashboard import theme


def render(data: dict, start: pd.Timestamp, end: pd.Timestamp) -> None:
    """Dibuja la vista ejecutiva para el rango de fechas [start, end]."""
    theme.panel_title(1, "Vista ejecutiva", "en construcción (JME)")
    st.markdown("Curva de capital, métricas, costos, bitácora y distribución de rendimientos por operación.")
