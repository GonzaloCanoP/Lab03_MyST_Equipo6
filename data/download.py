"""Ingesta de precios diarios ajustados, con snapshot local versionado.

El snapshot (`data/snapshot/prices_raw.parquet`) se versiona en Git para que `python main.py` corra igual en
cualquier máquina aunque Yahoo Finance falle o cambie los precios ajustados retroactivamente (cada dividendo
nuevo reescribe el histórico ajustado). Solo se descarga si el snapshot no existe o no cubre lo pedido.
"""

from pathlib import Path

import pandas as pd
import yfinance as yf


def download_prices(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """Descarga precios de cierre ajustados (splits y dividendos) de Yahoo Finance.

    Parámetros:
        tickers: símbolos a descargar.
        start, end: fechas "YYYY-MM-DD"; ambas inclusivas.

    Retorna:
        DataFrame con índice de fechas (`date`) y una columna por ticker, en el orden de `tickers`.
        Puede contener NaN (días sin cotización de algún activo); la limpieza se hace en `data.clean`.
    """
    # yfinance trata `end` como exclusivo: se suma un día para incluir END_DATE.
    end_exclusive = (pd.Timestamp(end) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    raw = yf.download(tickers, start=start, end=end_exclusive, auto_adjust=True, progress=False)
    prices = raw["Close"]
    if isinstance(prices, pd.Series):
        prices = prices.to_frame(tickers[0])
    prices = prices[tickers]
    prices.index = pd.to_datetime(prices.index).tz_localize(None)
    prices.index.name = "date"
    prices.columns.name = None
    return prices


def load_prices(tickers: list[str], start: str, end: str, snapshot_path: Path, refresh: bool = False) -> pd.DataFrame:
    """Carga precios desde el snapshot local; descarga y lo guarda solo si hace falta.

    Se descarga de nuevo si `refresh=True`, si el snapshot no existe, si le falta algún ticker o si no cubre el
    rango [start, end]. Al descargar se sobrescribe el snapshot completo.

    Retorna:
        Precios crudos (sin limpiar) de `tickers` entre `start` y `end`.
    """
    snapshot_path = Path(snapshot_path)
    if snapshot_path.exists() and not refresh:
        snapshot = pd.read_parquet(snapshot_path)
        has_tickers = set(tickers) <= set(snapshot.columns)
        # El snapshot cubre el rango si empieza a más tardar en `start` y su última fecha no queda antes de `end`
        # por más de una semana (fines de semana y feriados al final de la ventana).
        covers = snapshot.index.min() <= pd.Timestamp(start) + pd.Timedelta(days=7) and snapshot.index.max() >= pd.Timestamp(end) - pd.Timedelta(days=7)
        if has_tickers and covers:
            return snapshot.loc[start:end, tickers]

    prices = download_prices(tickers, start, end)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    prices.to_parquet(snapshot_path)
    return prices
