"""Partición cronológica 60/20/20 (entrenamiento / prueba / validación) con fechas de corte congeladas.

Las fechas de corte se calculan UNA vez sobre el calendario completo y se guardan en
`artifacts/split_dates.json`. Todas las etapas cortan por fecha, nunca por porcentaje del DataFrame que reciben:
así, al recalcular el pipeline con datos truncados en t (prueba de causalidad), la partición de entrenamiento
no se mueve y nada de lo ajustado en ella cambia.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

SPLIT = (0.60, 0.20, 0.20)
SPLIT_NAMES = ("train", "test", "validation")
N_ASSETS = 4  # activos por grupo: 2 · n integrantes, n = 2


@dataclass(frozen=True)
class SplitDates:
    """Primera y última fecha (inclusivas) de cada partición."""

    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    validation_start: pd.Timestamp
    validation_end: pd.Timestamp

    def bounds(self, name: str) -> tuple[pd.Timestamp, pd.Timestamp]:
        """(inicio, fin) de la partición `name` ∈ SPLIT_NAMES."""
        return getattr(self, f"{name}_start"), getattr(self, f"{name}_end")


def compute_split_dates(index: pd.DatetimeIndex, split: tuple[float, float, float] = SPLIT) -> SplitDates:
    """Calcula las fechas de corte sobre el calendario completo (se llama una sola vez en `main.py`).

    Con n fechas, entrenamiento son las primeras ⌊0.6·n⌋, prueba las siguientes hasta ⌊0.8·n⌋ y validación el
    resto, en orden cronológico.
    """
    index = pd.DatetimeIndex(index).sort_values()
    n = len(index)
    i_train = int(n * split[0])
    i_test = int(n * (split[0] + split[1]))
    return SplitDates(
        train_start=index[0],
        train_end=index[i_train - 1],
        test_start=index[i_train],
        test_end=index[i_test - 1],
        validation_start=index[i_test],
        validation_end=index[-1],
    )


def slice_split(df: pd.DataFrame, dates: SplitDates, name: str) -> pd.DataFrame:
    """Devuelve las filas de `df` dentro de la partición `name`, cortando por fecha."""
    start, end = dates.bounds(name)
    return df.loc[start:end]


def label_split(index: pd.DatetimeIndex, dates: SplitDates) -> pd.Series:
    """Columna `split` ∈ {train, test, validation} para cada fecha de `index` (la exige el contrato de artefactos)."""
    labels = pd.Series(pd.NA, index=index, dtype="string", name="split")
    for name in SPLIT_NAMES:
        start, end = dates.bounds(name)
        labels[(index >= start) & (index <= end)] = name
    return labels


def save_split_dates(dates: SplitDates, path: Path) -> None:
    """Guarda las fechas de corte en JSON (`artifacts/split_dates.json`)."""
    payload = {k: v.strftime("%Y-%m-%d") for k, v in asdict(dates).items()}
    Path(path).write_text(json.dumps(payload, indent=2))


def load_split_dates(path: Path) -> SplitDates:
    """Lee las fechas de corte congeladas que escribió `save_split_dates`."""
    payload = json.loads(Path(path).read_text())
    return SplitDates(**{k: pd.Timestamp(v) for k, v in payload.items()})
