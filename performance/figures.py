"""Figuras del reporte (1–8 del enunciado, §3.10). Cada función recibe datos ya calculados y solo dibuja.

Se exportan a `docs/figuras/` desde `main.py`; los notebooks llaman a las mismas funciones para mostrarlas.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sin ventana: main.py corre sin intervención
import matplotlib.pyplot as plt
import pandas as pd

SPLIT_COLORS = {"train": "#e8f0fe", "test": "#fef7e0", "validation": "#e6f4ea"}
SPLIT_LABELS = {"train": "entrenamiento", "test": "prueba", "validation": "validación"}


def _shade_splits(ax: plt.Axes, split: pd.Series) -> None:
    """Sombrea en `ax` el tramo de fechas de cada partición."""
    for name, color in SPLIT_COLORS.items():
        dates = split.index[split == name]
        if len(dates):
            ax.axvspan(dates[0], dates[-1], color=color, label=SPLIT_LABELS[name], zorder=0)


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
