"""Figuras del reporte (1–8 del enunciado, §3.10). Cada función recibe datos ya calculados y solo dibuja.

Se exportan a `docs/figuras/` desde `main.py`; los notebooks llaman a las mismas funciones para mostrarlas.
"""

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import jarque_bera, kurtosis, norm, skew

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


def plot_zscore_signals(signals: pd.DataFrame, rule: dict, path: Path | None = None, clip: float = 6.0) -> plt.Figure:
    """Figura 6: z-score prior del filtro 2 con los umbrales de entrada, salida y stop elegidos en train.

    Parámetros:
        signals: `signals.parquet` (columnas `zscore`, `signal`, `split`).
        rule: umbrales (`z_entry`, `z_exit`, `z_stop`, `max_holding`), los de `params.json` → `strategy`.
        path: si se da, guarda la figura (PNG).
        clip: límite del eje y; en validación z llega más allá del stop y se recorta para que se lea el resto.
    Retorna:
        La figura: arriba z_t con los umbrales, abajo la dirección decidida (+1 largo el spread, −1 corto).
    """
    fig, (ax, ax_pos) = plt.subplots(2, 1, figsize=(12, 6.5), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    _shade_splits(ax, signals["split"])
    ax.plot(signals.index, signals["zscore"].clip(-clip, clip), color="tab:blue", linewidth=0.7, label="z_t (prior)")
    for level, color, name in ((rule["z_entry"], "tab:green", "entrada"), (rule["z_exit"], "tab:orange", "salida"),
                               (rule["z_stop"], "tab:red", "stop")):
        for sign in (+1, -1) if level > 0 else (+1,):
            ax.axhline(sign * level, color=color, linewidth=1.0, linestyle="--",
                       label=f"{name} ±{level:g}" if sign == +1 else None)
    ax.set_ylim(-clip, clip)
    ax.set_title(f"Figura 6 — z-score del filtro 2 y umbrales elegidos en entrenamiento "
                 f"(h_max = {rule['max_holding']} días)")
    ax.set_ylabel(f"z_t (recortado a ±{clip:g})")
    ax.legend(fontsize=8, loc="upper left", ncol=7)
    ax.grid(alpha=0.3)

    _shade_splits(ax_pos, signals["split"])
    ax_pos.fill_between(signals.index, signals["signal"], step="post", color="tab:purple", alpha=0.6)
    ax_pos.set_yticks([-1, 0, 1], ["corto", "plano", "largo"])
    ax_pos.set_xlabel("Fecha")
    ax_pos.set_ylabel("Dirección")
    ax_pos.grid(alpha=0.3)
    fig.tight_layout()
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150)
    return fig


def plot_grid_heatmap(grid: pd.DataFrame, rule: dict, path: Path | None = None) -> plt.Figure:
    """Heatmap del grid search en train: Sharpe neto por (z_entrada, z_salida), un panel por k (h_max = k · vida media).

    Cada celda toma el z_stop elegido; las combinaciones con menos operaciones que el mínimo se muestran vacías.
    Parámetros:
        grid: `grid_search.csv`.
        rule: umbrales elegidos (marca la celda ganadora).
        path: si se da, guarda la figura (PNG).
    """
    data = grid.loc[(grid["z_stop"] == rule["z_stop"]) & grid["valid"]]
    ks = sorted(grid["holding_k"].unique())
    entries, exits = sorted(grid["z_entry"].unique()), sorted(grid["z_exit"].unique())
    vmin, vmax = data["sharpe_net"].min(), data["sharpe_net"].max()
    fig, axes = plt.subplots(1, len(ks), figsize=(4.2 * len(ks), 4.2), sharey=True)
    for ax, k in zip(np.atleast_1d(axes), ks):
        table = (data.loc[data["holding_k"] == k].pivot(index="z_entry", columns="z_exit", values="sharpe_net")
                 .reindex(index=entries, columns=exits))
        image = ax.imshow(table.to_numpy(), cmap="viridis", vmin=vmin, vmax=vmax, aspect="auto", origin="lower")
        for i, j in np.ndindex(table.shape):
            value = table.iat[i, j]
            if np.isfinite(value):
                ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=8,
                        color="white" if value < (vmin + vmax) / 2 else "black")
        h_max = int(grid.loc[grid["holding_k"] == k, "max_holding"].iloc[0])
        if rule["max_holding"] == h_max:
            ax.add_patch(plt.Rectangle((exits.index(rule["z_exit"]) - 0.5, entries.index(rule["z_entry"]) - 0.5),
                                       1, 1, fill=False, edgecolor="red", linewidth=2))
        ax.set_xticks(range(len(exits)), [f"{e:g}" for e in exits])
        ax.set_yticks(range(len(entries)), [f"{e:g}" for e in entries])
        ax.set_xlabel("z_salida")
        ax.set_title(f"k = {k} (h_max = {h_max} días)")
    np.atleast_1d(axes)[0].set_ylabel("z_entrada")
    fig.colorbar(image, ax=axes, label="Sharpe neto anualizado (train)")
    fig.suptitle(f"Grid search en entrenamiento, z_stop = {rule['z_stop']:g} (celda roja = elegida; vacías: "
                 f"menos operaciones que el mínimo)", fontsize=10)
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150, bbox_inches="tight")
    return fig


EXIT_MARKERS = {"salida": ("o", "tab:green"), "stop": ("X", "tab:red"), "holding": ("s", "tab:orange"),
                "fin_particion": ("D", "tab:gray")}


def plot_spread_signals(kf2: pd.DataFrame, trades: pd.DataFrame, path: Path | None = None) -> plt.Figure:
    """Figura 2: ECT dinámico del filtro 1 con su media prior del filtro 2 y las operaciones marcadas.

    Entradas: ▲ largo el spread, ▼ corto (en la fecha de ejecución). Salidas con el marcador de su motivo.
    Parámetros:
        kf2: `kf2_signal.parquet` (`ect`, `mu_prior`, `split`).
        trades: `trades.csv` (`entry_date`, `exit_date`, `direction`, `exit_reason`).
        path: si se da, guarda la figura (PNG).
    """
    fig, ax = plt.subplots(figsize=(13, 5))
    _shade_splits(ax, kf2["split"])
    ax.plot(kf2.index, kf2["ect"], color="tab:blue", linewidth=0.8, label="ECT dinámico (filtro 1)")
    ax.plot(kf2.index, kf2["mu_prior"], color="black", linewidth=1.0, linestyle="--", label="μ̂ prior (filtro 2)")
    entries = pd.to_datetime(trades["entry_date"])
    for direction, marker, color, label in ((1, "^", "tab:green", "entrada largo"), (-1, "v", "tab:red", "entrada corto")):
        dates = entries[trades["direction"] == direction]
        ax.scatter(dates, kf2["ect"].reindex(dates), marker=marker, color=color, s=40, zorder=3, label=label)
    exits = pd.to_datetime(trades["exit_date"])
    for reason, (marker, color) in EXIT_MARKERS.items():
        dates = exits[trades["exit_reason"] == reason]
        if len(dates):
            ax.scatter(dates, kf2["ect"].reindex(dates), marker=marker, facecolor="none" if marker == "o" else color,
                       edgecolor=color, s=35, zorder=3, label=f"salida: {reason}")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_title("Figura 2 — Spread del portafolio (ECT dinámico) con las operaciones")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("ECT = β̂ᵀ ln P_t − ĉ")
    ax.legend(fontsize=8, loc="upper left", ncol=4)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150)
    return fig


def plot_equity_curves(equity: pd.DataFrame, path: Path | None = None) -> plt.Figure:
    """Figura 7: curva de capital neta de costos por partición, junto con la curva antes de costos.

    Cada partición arranca con el capital inicial (walk-forward con parámetros congelados desde train). La distancia
    entre las dos curvas es lo acumulado en comisiones y préstamo.
    Parámetros:
        equity: `equity_curve.parquet` (`equity`, `gross_pnl`, `split`).
        path: si se da, guarda la figura (PNG).
    """
    splits = list(dict.fromkeys(equity["split"]))
    fig, axes = plt.subplots(1, len(splits), figsize=(15, 4.5), sharey=True,
                             gridspec_kw={"width_ratios": [(equity["split"] == s).sum() for s in splits]})
    for ax, split in zip(np.atleast_1d(axes), splits):
        part = equity.loc[equity["split"] == split]
        start = part["equity"].iloc[0] + part["commission"].iloc[0]
        before_costs = start + part["gross_pnl"].cumsum()
        ret = part["equity"].iloc[-1] / start - 1
        ax.set_facecolor(SPLIT_COLORS[split])
        ax.plot(part.index, before_costs, color="tab:gray", linewidth=1.0, linestyle="--", label="antes de costos")
        ax.plot(part.index, part["equity"], color="tab:blue", linewidth=1.4, label="neta de costos")
        ax.axhline(start, color="black", linewidth=0.6)
        ax.set_title(f"{SPLIT_LABELS[split]}: {ret:+.1%} neto")
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.grid(alpha=0.3)
    axes = np.atleast_1d(axes)
    axes[0].set_ylabel("Capital ($)")
    axes[0].legend(fontsize=8, loc="upper left")
    fig.suptitle("Figura 7 — Curvas de capital por partición (cada una arranca con $1,000,000)")
    fig.tight_layout()
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150)
    return fig


def plot_trade_return_distribution(trade_ret: pd.Series, split: pd.Series, path: Path | None = None) -> plt.Figure:
    """Figura 8: distribución de los rendimientos por operación con la normal de misma media y desviación superpuesta.

    Parámetros:
        trade_ret: rendimiento neto de cada operación (`performance.metrics.trade_returns`).
        split: partición de cada operación (mismo orden), para apilar el histograma por color.
        path: si se da, guarda la figura (PNG).
    Las colas gruesas o la asimetría respecto a la normal dicen cómo pierde la estrategia: muchas ganancias chicas
    por reversión y pocas pérdidas grandes cuando el spread no revierte.
    """
    r = 100 * np.asarray(trade_ret, dtype=float)  # en %
    split = np.asarray(split)
    order = [s for s in SPLIT_LABELS if s in set(split)]
    bins = np.histogram_bin_edges(r, bins=min(20, max(8, len(r) // 2)))
    edge_colors = {"train": "#4a7bd0", "test": "#d9a520", "validation": "#3a9a5b"}

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist([r[split == s] for s in order], bins=bins, stacked=True, density=True, rwidth=0.9,
            color=[edge_colors[s] for s in order], alpha=0.75, label=[SPLIT_LABELS[s] for s in order])
    mu, sd = r.mean(), r.std(ddof=1)
    grid = np.linspace(min(bins[0], mu - 3 * sd), max(bins[-1], mu + 3 * sd), 300)
    ax.plot(grid, norm.pdf(grid, mu, sd), color="black", linewidth=1.6, label=f"normal(μ = {mu:.2f} %, σ = {sd:.2f} %)")
    ax.axvline(0, color="tab:gray", linewidth=0.8, linestyle=":")
    stats_text = (f"n = {len(r)} operaciones\nasimetría = {skew(r):.2f}\ncurtosis = {kurtosis(r, fisher=False):.2f}"
                  f"\nJarque–Bera p = {jarque_bera(r).pvalue:.3f}")
    ax.text(0.02, 0.97, stats_text, transform=ax.transAxes, va="top", fontsize=9,
            bbox={"facecolor": "white", "edgecolor": "0.8", "boxstyle": "round"})
    ax.set_xlabel("Rendimiento neto por operación (% del capital al entrar)")
    ax.set_ylabel("Densidad")
    ax.set_title("Figura 8 — Distribución de rendimientos por operación vs normal")
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150)
    return fig


def plot_rolling_sharpe(rolling: pd.Series, split: pd.Series, full_sample: dict, path: Path | None = None) -> plt.Figure:
    """Sharpe neto móvil de 252 días sobre toda la muestra, con las particiones sombreadas.

    Parámetros:
        rolling: `rolling_sharpe_252` (`performance.metrics.rolling_sharpe` sobre los rendimientos encadenados). La
            ventana cruza el inicio de cada partición: sus primeros 251 valores mezclan días de la anterior.
        split: partición de cada fecha.
        full_sample: {partición: Sharpe neto de la partición completa}, se dibuja como referencia horizontal.
        path: si se da, guarda la figura (PNG).
    """
    fig, ax = plt.subplots(figsize=(13, 4.5))
    _shade_splits(ax, split)
    ax.plot(rolling.index, rolling, color="tab:blue", linewidth=1.2, label="Sharpe neto móvil (252 días)")
    for name, value in full_sample.items():
        part = split.index[split == name]
        ax.hlines(value, part[0], part[-1], color="black", linewidth=1.0, linestyle="--")
        ax.annotate(f"{SPLIT_LABELS[name]}: {value:.2f}", (part[0], value), textcoords="offset points",
                    xytext=(4, 5), fontsize=8)
    ax.axhline(0, color="tab:gray", linewidth=0.8)
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Sharpe anualizado")
    ax.set_title("Sharpe neto móvil de 252 días (línea punteada: Sharpe de la partición completa)\n"
                 "En el primer año de prueba y de validación la ventana todavía incluye días de la partición anterior",
                 fontsize=10)
    ax.legend(fontsize=8, loc="upper left", ncol=4)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150)
    return fig
