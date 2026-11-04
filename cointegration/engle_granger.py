"""Engle–Granger en dos pasos (sesión 12): OLS en log-precios + ADF de los residuales.

En este proyecto Engle–Granger **prioriza, no elimina** (decisión en `docs/decisiones.md`): el criterio definitivo
es Johansen. Por eso este módulo solo calcula y reporta; las reglas de descarte viven en `selection.py`.

Detalles que importan en la exposición:
- El p-value usa los valores críticos de MacKinnon para residuales de una regresión con N series (no los de un
  ADF común): `statsmodels.tsa.stattools.coint` ya los aplica.
- El resultado depende de qué activo es el dependiente; por eso se corre en todas las direcciones.
- Diagnóstico de regresión espuria (Granger–Newbold): R² > Durbin–Watson es señal de alerta.
"""

from dataclasses import dataclass
from itertools import combinations

import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.stattools import durbin_watson
from statsmodels.tsa.stattools import coint


@dataclass(frozen=True)
class EngleGrangerResult:
    """Regresión de largo plazo y ADF de sus residuales.

    Atributos:
        dependent: activo del lado izquierdo (y_t).
        regressors: activos del lado derecho.
        intercept, hedge_ratios: coeficientes OLS de y_t = intercept + Σ hedge_ratio_i x_t^{(i)} + s_t.
        r_squared, durbin_watson: diagnóstico de regresión espuria.
        adf_stat, pvalue: estadístico ADF de los residuales y su p-value de MacKinnon.
    """

    dependent: str
    regressors: tuple[str, ...]
    intercept: float
    hedge_ratios: tuple[float, ...]
    r_squared: float
    durbin_watson: float
    adf_stat: float
    pvalue: float

    @property
    def spurious_flag(self) -> bool:
        """True si R² > DW: el ajuste "bueno" puede venir de dos tendencias, no de una relación real."""
        return self.r_squared > self.durbin_watson


def engle_granger(log_prices: pd.DataFrame, dependent: str) -> EngleGrangerResult:
    """Corre Engle–Granger con `dependent` como y_t y el resto de las columnas como regresores.

    Parámetros:
        log_prices: log-precios de entrenamiento (una columna por activo, sin NaN).
        dependent: columna que va del lado izquierdo.
    Retorna:
        EngleGrangerResult con la regresión completa y el ADF de los residuales (constante, rezagos por AIC).
    """
    y = log_prices[dependent]
    x = log_prices.drop(columns=dependent)
    ols = sm.OLS(y, sm.add_constant(x)).fit()
    adf_stat, pvalue, _ = coint(y, x, trend="c", autolag="aic")
    return EngleGrangerResult(
        dependent=dependent,
        regressors=tuple(x.columns),
        intercept=float(ols.params["const"]),
        hedge_ratios=tuple(float(ols.params[c]) for c in x.columns),
        r_squared=float(ols.rsquared),
        durbin_watson=float(durbin_watson(ols.resid)),
        adf_stat=float(adf_stat),
        pvalue=float(pvalue),
    )


def best_engle_granger(log_prices: pd.DataFrame) -> EngleGrangerResult:
    """Corre Engle–Granger con cada activo como dependiente y devuelve la dirección con menor p-value.

    Tomar el mínimo sobre direcciones es optimista; se acepta porque Engle–Granger solo prioriza.
    """
    results = [engle_granger(log_prices, col) for col in log_prices.columns]
    return min(results, key=lambda r: r.pvalue)


def pairwise_engle_granger(log_prices: pd.DataFrame) -> pd.DataFrame:
    """Engle–Granger para cada par de columnas, en ambas direcciones.

    Retorna:
        DataFrame con una fila por par: `asset_1`, `asset_2`, `pvalue_1_on_2` (asset_1 dependiente),
        `pvalue_2_on_1` y `pvalue_min`.
    """
    rows = []
    for a, b in combinations(log_prices.columns, 2):
        p_ab = engle_granger(log_prices[[a, b]], a).pvalue
        p_ba = engle_granger(log_prices[[a, b]], b).pvalue
        rows.append({"asset_1": a, "asset_2": b, "pvalue_1_on_2": p_ab, "pvalue_2_on_1": p_ba,
                     "pvalue_min": min(p_ab, p_ba)})
    return pd.DataFrame(rows)
