# 07 — Métricas de desempeño

**Dueño:** Gonzalo Cano (GC) · **Revisor:** Juan Manuel Espinosa (JME) · **Notebook:** `notebooks/07_metricas.ipynb` · **Carpeta:** `performance/` · **Depende de:** 06 · **Alimenta a:** 08, 11

## Parámetros de este módulo

Tasa libre de riesgo, `TRADING_DAYS = 252` y ventana del Sharpe móvil (252) en `performance/metrics.py`. Si cambian, actualizar la tabla de parámetros de `CLAUDE.md`.

## Contrato

- **Lee:** `equity_curve.parquet`, `trades.csv`.
- **Escribe:** `metrics.json` (por split y total), columna de Sharpe móvil 252d.
- **Expone:** una función por métrica, todas puras: `sharpe(returns)`, `sortino(...)`, etc.

## Loop de trabajo

```
REPETIR hasta cumplir el criterio de terminado:
  1. Toma el primer ítem sin [x].
  2. Implementa la métrica con su fórmula en el docstring (anualización, tasa libre de riesgo).
  3. Verifica con una serie sintética de resultado conocido.
  4. Marca [x], commit.
```

## Checklist

- [x] Sharpe Ratio (anualizado, r_f = 0 declarada): 0.66 / 0.74 / 1.01, total 0.75.
- [x] Sortino Ratio (DD sobre todos los días, objetivo 0): 1.01 / 1.12 / 1.61.
- [x] Calmar Ratio (CAGR / |MDD| del mismo tramo): 0.38 / 0.59 / 0.98.
- [x] Maximum Drawdown (y duración): −6.6 % (1 185 días) / −4.5 % (244) / −3.7 % (171).
- [x] Win Rate (por operación, P&L neto): 79 % / 89 % / 91 %.
- [x] Profit Factor: 2.49 / 4.55 / 8.11.
- [x] Sharpe móvil de 252 días sobre toda la muestra: columna `rolling_sharpe_252` de `equity_curve.parquet` y `docs/figuras/sharpe_movil.png`.
- [x] Distribución de retornos por operación + normal superpuesta (figura 8): `docs/figuras/fig08_distribucion_operaciones.png`; asimetría −1.4, curtosis 4.7, Jarque–Bera p < 0.001.
- [x] Métricas por split (train / test / validación) y total en `metrics.json`; discusión de degradación en el notebook 07.

## Criterio de terminado

`metrics.json` generado por `main.py`, cada métrica probada contra un caso conocido.
