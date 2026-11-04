"""Validación de la serie de precios limpia antes de cualquier estimación."""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# Un rendimiento logarítmico diario mayor a este valor absoluto (≈ ±40 %) se reporta como salto anómalo.
# No se elimina: puede ser un evento real (p. ej. marzo de 2020), pero hay que revisarlo a mano.
JUMP_THRESHOLD = 0.40


@dataclass
class ValidationReport:
    """Resultado de `validate_prices`. `is_valid` exige sin NaN, precios positivos, sin duplicados y orden."""

    n_rows: int
    start: pd.Timestamp
    end: pd.Timestamp
    n_nan: int
    n_nonpositive: int
    n_duplicates: int
    is_sorted: bool
    jumps: pd.DataFrame = field(repr=False)

    @property
    def is_valid(self) -> bool:
        return self.n_nan == 0 and self.n_nonpositive == 0 and self.n_duplicates == 0 and self.is_sorted

    def to_dict(self) -> dict:
        """Versión serializable (para `artifacts/validation_report.json`)."""
        return {
            "n_rows": self.n_rows,
            "start": self.start.strftime("%Y-%m-%d"),
            "end": self.end.strftime("%Y-%m-%d"),
            "n_nan": self.n_nan,
            "n_nonpositive": self.n_nonpositive,
            "n_duplicates": self.n_duplicates,
            "is_sorted": self.is_sorted,
            "is_valid": self.is_valid,
            "jumps": [
                {"date": d.strftime("%Y-%m-%d"), "ticker": t, "log_return": round(float(r), 4)}
                for d, t, r in self.jumps.itertuples(index=False)
            ],
        }


def validate_prices(prices: pd.DataFrame, jump_threshold: float = JUMP_THRESHOLD) -> ValidationReport:
    """Revisa NaN, precios no positivos, fechas duplicadas, orden del índice y saltos anómalos.

    Retorna:
        ValidationReport; los saltos vienen en un DataFrame con columnas `date`, `ticker`, `log_return`.
    """
    log_returns = np.log(prices).diff()
    jumps = log_returns.stack()
    jumps = jumps[jumps.abs() > jump_threshold].reset_index()
    jumps.columns = ["date", "ticker", "log_return"]
    return ValidationReport(
        n_rows=len(prices),
        start=prices.index.min(),
        end=prices.index.max(),
        n_nan=int(prices.isna().sum().sum()),
        n_nonpositive=int((prices <= 0).sum().sum()),
        n_duplicates=int(prices.index.duplicated().sum()),
        is_sorted=bool(prices.index.is_monotonic_increasing),
        jumps=jumps,
    )


def assert_valid(report: ValidationReport) -> None:
    """Detiene el pipeline si la validación falla; así ninguna etapa estima con datos corruptos."""
    if not report.is_valid:
        raise ValueError(f"Precios inválidos: {report.to_dict()}")
