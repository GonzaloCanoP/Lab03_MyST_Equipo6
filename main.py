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

import json
from pathlib import Path

import numpy as np
import pandas as pd

from cointegration.universe import all_tickers
from data.clean import clean_prices
from data.download import load_prices
from data.split import SplitDates, compute_split_dates, save_split_dates
from data.validate import JUMP_THRESHOLD, assert_valid, validate_prices

# --- Reproducibilidad: semilla fija para todo el pipeline ---
SEED = 42

# --- Rutas ---
ROOT = Path(__file__).resolve().parent
DATA_SNAPSHOT = ROOT / "data" / "snapshot" / "prices_raw.parquet"  # versionado en Git
ARTIFACTS = ROOT / "artifacts"
FIGURES = ROOT / "docs" / "figuras"

# --- Ventana histórica (10-15 años de precios diarios, fechas fijas para reproducibilidad) ---
START_DATE = "2012-01-01"  # ≈ 14.8 años hasta END_DATE (el enunciado pide 10-15)
END_DATE = "2026-10-30"


def run_data_stage() -> tuple[pd.DataFrame, SplitDates]:
    """Etapa 1: precios limpios y validados de todos los universos + fechas de corte congeladas."""
    raw = load_prices(all_tickers(), START_DATE, END_DATE, DATA_SNAPSHOT)
    prices, clean_report = clean_prices(raw)
    report = validate_prices(prices)
    assert_valid(report)
    split_dates = compute_split_dates(prices.index)

    save_split_dates(split_dates, ARTIFACTS / "split_dates.json")
    (ARTIFACTS / "validation_report.json").write_text(
        json.dumps({"cleaning": clean_report, "validation": report.to_dict()}, indent=2)
    )
    print(f"[data] {report.n_rows} días × {prices.shape[1]} activos, {report.start.date()} → {report.end.date()}")
    print(f"[data] rellenados: {clean_report['filled_cells'] or 'ninguno'}; fechas eliminadas: {clean_report['rows_dropped']}")
    print(f"[data] saltos anómalos (|rend. log| > {JUMP_THRESHOLD}): {len(report.jumps)} (detalle en el notebook 01)")
    for name in ("train", "test", "validation"):
        start, end = split_dates.bounds(name)
        print(f"[data] {name:<10} {start.date()} → {end.date()}")
    return prices, split_dates


def main() -> None:
    np.random.seed(SEED)
    ARTIFACTS.mkdir(exist_ok=True)
    prices, split_dates = run_data_stage()
    # Las siguientes etapas se conectan aquí conforme se implementan.


if __name__ == "__main__":
    main()
