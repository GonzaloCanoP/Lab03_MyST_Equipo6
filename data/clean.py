"""Limpieza de precios: calendario común y faltantes sin look-ahead."""

import pandas as pd

# Máximo de días hábiles consecutivos que se rellenan hacia adelante. Cubre feriados locales y suspensiones
# breves sin inventar tendencias largas; nunca se rellena hacia atrás (eso usaría precios futuros).
MAX_FFILL = 3


def clean_prices(raw: pd.DataFrame, max_ffill: int = MAX_FFILL) -> tuple[pd.DataFrame, dict]:
    """Ordena, quita duplicados, rellena huecos cortos hacia adelante y alinea los calendarios.

    Pasos:
        1. Ordena por fecha y elimina fechas duplicadas (se queda con la primera).
        2. Forward-fill con límite `max_ffill`: usa solo el último precio conocido, nunca uno posterior.
        3. Intersección de calendarios: elimina las fechas donde algún activo sigue sin precio.

    Retorna:
        (precios limpios sin NaN, reporte con lo que se tocó: duplicados, celdas rellenadas por ticker y
        fechas eliminadas).
    """
    prices = raw.sort_index()
    n_duplicates = int(prices.index.duplicated().sum())
    prices = prices[~prices.index.duplicated(keep="first")]

    filled = prices.ffill(limit=max_ffill)
    filled_cells = (prices.isna() & filled.notna()).sum()

    clean = filled.dropna(how="any")
    report = {
        "rows_raw": len(raw),
        "duplicates_removed": n_duplicates,
        "filled_cells": {t: int(n) for t, n in filled_cells.items() if n > 0},
        "rows_dropped": len(filled) - len(clean),
        "rows_clean": len(clean),
        "max_ffill": max_ffill,
    }
    return clean, report
