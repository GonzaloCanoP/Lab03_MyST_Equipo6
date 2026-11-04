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

- [ ] Sharpe Ratio (anualizado, tasa libre de riesgo declarada).
- [ ] Sortino Ratio.
- [ ] Calmar Ratio.
- [ ] Maximum Drawdown (y duración).
- [ ] Win Rate (por operación).
- [ ] Profit Factor.
- [ ] Sharpe móvil de 252 días sobre toda la muestra.
- [ ] Distribución de retornos por operación + normal superpuesta (figura 8).
- [ ] Métricas por split (train / test / validación) para discutir degradación fuera de muestra.

## Criterio de terminado

`metrics.json` generado por `main.py`, cada métrica probada contra un caso conocido.
