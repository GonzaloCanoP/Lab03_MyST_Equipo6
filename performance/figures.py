"""Figuras del reporte (1–8 del enunciado, §3.10). Cada función recibe datos ya calculados y solo dibuja.

Se exportan a `docs/figuras/` desde `main.py`; los notebooks llaman a las mismas funciones para mostrarlas.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SPLIT_COLORS = {"train": "#e8f0fe", "test": "#fef7e0", "validation": "#e6f4ea"}
SPLIT_LABELS = {"train": "entrenamiento", "test": "prueba", "validation": "validación"}


def _shade_splits(ax: plt.Axes, split: pd.Series) -> None:
    """Sombrea en `ax` el tramo de fechas de cada partición."""
    for name, color in SPLIT_COLORS.items():
        dates = split.index[split == name]
        if len(dates):
            ax.axvspan(dates[0], dates[-1], color=color, label=SPLIT_LABELS[name], zorder=0)


def plot_normalized_prices(prices: pd.DataFrame, split: pd.Series, title: str, path: Path | None = None) -> plt.Figure:
    """Figura 1: precios ajustados en base 100 al inicio de la muestra, escala log, particiones sombreadas.

    Parámetros:
        prices: precios (no log), una columna por activo, índice de fechas.
        split: etiqueta de partición por fecha (columna `split` de `artifacts/prices.parquet` o `label_split`).
        title: título de la figura.
        path: si se da, guarda la figura ahí (PNG).
    Retorna:
        La figura de matplotlib. La escala log hace comparables los movimientos porcentuales de todos los activos
        (y es la escala en la que se estiman la cointegración y los filtros).
    """
    normalized = 100 * prices / prices.iloc[0]
    fig, ax = plt.subplots(figsize=(12, 5))
    _shade_splits(ax, split)
    for ticker in normalized.columns:
        ax.plot(normalized.index, normalized[ticker], linewidth=1.1, label=ticker)
    ax.set_yscale("log")
    ax.set_title(title)
    ax.set_xlabel("Fecha")
    ax.set_ylabel(f"Precio ajustado, base 100 = {prices.index[0].date()} (escala log)")
    ax.legend(ncol=6, fontsize=8, loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150)
    return fig


def plot_rolling_eigenvector(rolling: pd.DataFrame, tickers: list[str], anchor: str, window: int,
                             path: Path | None = None, clip: float = 3.0) -> plt.Figure:
    """Figura 4: primer eigenvector de Johansen móvil (normalizado sobre la pata ancla) y su significancia.

    Parámetros:
        rolling: salida de `rolling_first_eigenvector` con columna `split`.
        tickers: activos del grupo; anchor: pata ancla (vale +1 en todas las ventanas).
        window: tamaño de ventana en días (para el título).
        path: si se da, guarda la figura ahí (PNG).
        clip: límite del eje y del panel de pesos. Cuando una ventana no tiene cointegración, el peso del ancla
            se acerca a cero y β̃ = β / β_ancla explota; recortar el eje evita que esas ventanas oculten el resto.
    Retorna:
        La figura de matplotlib.
    """
    fig, (ax_beta, ax_trace) = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    for ax in (ax_beta, ax_trace):
        _shade_splits(ax, rolling["split"])
    for ticker in tickers:
        style = "--" if ticker == anchor else "-"
        ax_beta.plot(rolling.index, rolling[ticker], style, linewidth=1.3, label=f"{ticker}" + (" (ancla)" if ticker == anchor else ""))
    ax_beta.axhline(0, color="black", linewidth=0.6)
    ax_beta.set_ylim(-clip, clip)
    ax_beta.set_ylabel("β̃ (pata ancla = +1)")
    ax_beta.set_title(f"Figura 4 — Primer eigenvector de Johansen móvil (ventana de {window} días)")
    ax_beta.legend(ncol=4, fontsize=8, loc="lower left")
    ax_beta.grid(alpha=0.3)

    ratio = rolling["trace_0"] / rolling["trace_cv95_0"]
    ax_trace.plot(rolling.index, ratio, color="tab:purple", linewidth=1.3, label="LR_traza(0) / valor crítico 95 %")
    ax_trace.axhline(1, color="tab:red", linestyle="--", linewidth=1, label="umbral (rechaza r = 0 arriba de 1)")
    ax_trace.set_ylabel("traza / crítico")
    ax_trace.set_xlabel("Fecha final de la ventana")
    ax_trace.legend(fontsize=8, loc="upper left")
    ax_trace.grid(alpha=0.3)
    fig.tight_layout()
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150)
    return fig


def plot_dynamic_weights(kf1: pd.DataFrame, tickers: list[str], anchor: str, static_beta: dict,
                         path: Path | None = None) -> plt.Figure:
    """Figura 3: pesos β̂_t del filtro 1 (posterior), una línea por activo, contra el β̃ estático de Johansen.

    Parámetros:
        kf1: `kf1_weights.parquet` (columnas `beta_<ticker>` y `split`).
        tickers: activos del grupo; anchor: pata ancla (peso fijo +1, se omite del panel).
        static_beta: β̃ de Johansen por ticker (líneas punteadas).
        path: si se da, guarda la figura (PNG).
    """
    others = [t for t in tickers if t != anchor]
    fig, axes = plt.subplots(len(others), 1, figsize=(12, 2.6 * len(others)), sharex=True)
    for ax, ticker in zip(np.atleast_1d(axes), others):
        _shade_splits(ax, kf1["split"])
        line, = ax.plot(kf1.index, kf1[f"beta_{ticker}"], linewidth=1.3, label=f"β̂_t {ticker} (filtro 1)")
        ax.axhline(static_beta[ticker], color=line.get_color(), linestyle=":", linewidth=1.2,
                   label=f"β̃ Johansen (train) = {static_beta[ticker]:+.3f}")
        ax.set_ylabel(f"β {ticker}")
        ax.legend(fontsize=8, loc="best", ncol=3)
        ax.grid(alpha=0.3)
    axes = np.atleast_1d(axes)
    axes[0].set_title(f"Figura 3 — Pesos dinámicos del filtro 1 (pata ancla {anchor} = +1)")
    axes[-1].set_xlabel("Fecha")
    fig.tight_layout()
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150)
    return fig


def plot_kalman_gains(kf1: pd.DataFrame, state_names: list[str], kf2: pd.DataFrame | None = None,
                      kf2_gain_column: str = "gain", path: Path | None = None) -> plt.Figure:
    """Figura 5: ganancia de Kalman en el tiempo de ambos filtros.

    Panel 1 (filtro 1): C_t K_t = 1 − R / S_t, la fracción de cada sorpresa que el filtro absorbe moviendo sus pesos
    (es la versión escalar de K_t; con estado de 4 dimensiones K_t es un vector).
    Panel 2 (filtro 1): componentes de K_t por estado (intercepto y pesos).
    Panel 3 (filtro 2, opcional): ganancia de la media K^μ_t (cuánto de cada sorpresa mueve μ̂) y de la desviación
    K^x_t; se agrega cuando exista `kf2_signal.parquet`.

    Parámetros:
        kf1: `kf1_weights.parquet`; state_names: nombres de estado (`c` y tickers no ancla), columnas `gain_<n>`.
        kf2: `kf2_signal.parquet` (opcional); `kf2_gain_column` es su ganancia de la media y, si existe, se dibuja
            también `gain_x` (ganancia de la desviación del estado aumentado).
        path: si se da, guarda la figura (PNG).
    """
    n_panels = 3 if kf2 is not None else 2
    fig, axes = plt.subplots(n_panels, 1, figsize=(12, 3.2 * n_panels), sharex=True)
    for ax in axes:
        _shade_splits(ax, kf1["split"])
    axes[0].plot(kf1.index, kf1["absorption"], color="tab:purple", linewidth=1.3,
                 label="filtro 1: C_t K_t = 1 − R/S_t (fracción absorbida por día)")
    axes[0].set_ylabel("C_t K_t")
    axes[0].set_title("Figura 5 — Ganancia de Kalman en el tiempo")
    for name in state_names:
        axes[1].plot(kf1.index, kf1[f"gain_{name}"], linewidth=1.1, label=f"K_t[{name}]")
    axes[1].axhline(0, color="black", linewidth=0.6)
    axes[1].set_ylabel("componentes de K_t")
    if kf2 is not None:
        axes[2].plot(kf2.index, kf2[kf2_gain_column], color="tab:green", linewidth=1.3,
                     label="filtro 2: K^μ_t (media)")
        if "gain_x" in kf2:
            axes[2].plot(kf2.index, kf2["gain_x"], color="tab:olive", linewidth=1.0, alpha=0.8,
                         label="filtro 2: K^x_t (desviación)")
        axes[2].set_ylabel("K_t (filtro 2)")
    for ax in axes:
        ax.legend(fontsize=8, loc="best", ncol=4)
        ax.grid(alpha=0.3)
    axes[-1].set_xlabel("Fecha")
    fig.tight_layout()
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150)
    return fig


def plot_ect_comparison(kf1: pd.DataFrame, path: Path | None = None) -> plt.Figure:
    """ECT estático (β̃ y c de Johansen congelados en train) contra ECT dinámico del filtro 1 (pesos prior).

    Comparación sugerida por el profesor: si la relación de train se rompe fuera de muestra, el estático se desplaza
    y el dinámico debería seguir oscilando alrededor de cero.
    Parámetros:
        kf1: `kf1_weights.parquet` (columnas `ect_static`, `ect_dynamic`, `split`).
        path: si se da, guarda la figura (PNG).
    """
    fig, ax = plt.subplots(figsize=(12, 4.5))
    _shade_splits(ax, kf1["split"])
    ax.plot(kf1.index, kf1["ect_static"], color="tab:gray", linewidth=0.9, label="ECT estático (Johansen de train)")
    ax.plot(kf1.index, kf1["ect_dynamic"], color="tab:blue", linewidth=0.9, label="ECT dinámico (filtro 1, pesos prior)")
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_title("ECT estático vs dinámico del filtro 1")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("ECT = β̂ᵀ ln P_t − ĉ")
    ax.legend(fontsize=8, loc="upper left", ncol=5)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150)
    return fig
