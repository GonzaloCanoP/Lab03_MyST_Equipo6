"""Carga de artefactos para el dashboard. El dashboard SOLO lee `artifacts/` (lo escribe `python main.py`) y no
recalcula nada; si falta un archivo, se detiene con un mensaje claro.
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"  # misma carpeta que `main.ARTIFACTS`

PARQUET = ["prices", "kf1_weights", "kf2_signal", "rolling_eigenvector", "signals", "equity_curve"]
CSV = ["trades", "rebalance_comparison", "selection_table", "grid_search"]
JSON = ["params", "metrics", "johansen_summary", "vecm_summary", "split_dates"]


def missing_artifacts(folder: Path = ARTIFACTS) -> list[str]:
    """Nombres de los artefactos que faltan en `folder` (lista vacía si están todos)."""
    expected = [f"{n}.parquet" for n in PARQUET] + [f"{n}.csv" for n in CSV] + [f"{n}.json" for n in JSON]
    return [name for name in expected if not (folder / name).exists()]


@st.cache_data(show_spinner=False)
def load_artifacts(folder: str = str(ARTIFACTS)) -> dict:
    """Lee todos los artefactos del contrato en un dict {nombre: DataFrame o dict}.

    Las series de tiempo conservan su índice `date`; `trades` trae las fechas como datetime.
    """
    root = Path(folder)
    data = {name: pd.read_parquet(root / f"{name}.parquet") for name in PARQUET}
    data.update({name: pd.read_csv(root / f"{name}.csv") for name in CSV})
    data.update({name: json.loads((root / f"{name}.json").read_text()) for name in JSON})
    for col in ("entry_date", "exit_date"):
        data["trades"][col] = pd.to_datetime(data["trades"][col])
    return data


def require_artifacts() -> dict:
    """Carga los artefactos o detiene la app con la instrucción para generarlos."""
    missing = missing_artifacts()
    if missing:
        st.error("Faltan artefactos en `artifacts/`: " + ", ".join(missing)
                 + ". Corre `python main.py` desde la raíz del repositorio y vuelve a abrir el dashboard.")
        st.stop()
    return load_artifacts()
