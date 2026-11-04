"""Pipeline completo del Lab03: python main.py

Etapas (cada una escribe sus salidas en artifacts/):
    1. data           descarga, limpieza, validación y split 60/20/20
    2. cointegration  universo → correlación → Engle-Granger → Johansen → vector reversivo
    3. kalman         filtro 1 (β_t) y filtro 2 (μ_t, σ_t → z_t)
    4. strategy       VECM, grid search de umbrales en train, señales y sizing
    5. backtest       motor multi-pata con costos, walk-forward, rebalanceo vs banda
    6. performance    métricas por split

Los parámetros globales viven aquí y se pasan como argumentos a cada etapa.
Los parámetros propios de cada módulo (costos, umbrales, split) viven en ese módulo.
"""

from pathlib import Path

import numpy as np

# --- Reproducibilidad: semilla fija para todo el pipeline ---
SEED = 42

# --- Rutas ---
ROOT = Path(__file__).resolve().parent
DATA_RAW = ROOT / "data" / "raw"
ARTIFACTS = ROOT / "artifacts"
FIGURES = ROOT / "docs" / "figuras"

# --- Ventana histórica (10-15 años de precios diarios, fechas fijas para reproducibilidad) ---
START_DATE = "2012-01-01"  # ≈ 14.8 años hasta END_DATE (el enunciado pide 10-15)
END_DATE = "2026-10-30"


def main() -> None:
    np.random.seed(SEED)
    ARTIFACTS.mkdir(exist_ok=True)
    # Las etapas se conectan aquí conforme se implementan.


if __name__ == "__main__":
    main()
