# 08 — Dashboard (Streamlit)

**Dueño:** _por asignar_ · **Carpeta:** `dashboard/` · **Depende de:** artefactos de 02–07 · **Alimenta a:** 11

## Objetivo

Dashboard interactivo con dos vistas que **solo lee `artifacts/`** (no recalcula nada).
Se puede empezar en paralelo usando artefactos dummy con el esquema del contrato.

## Loop de trabajo

```
REPETIR hasta cumplir el criterio de terminado:
  1. Toma el primer ítem sin [x].
  2. Implementa la gráfica con Plotly (interactiva: zoom, hover, filtros).
  3. Verifica: streamlit run dashboard/app.py, revisar título, ejes, leyenda.
  4. Marca [x], commit.
```

## Checklist — Vista ejecutiva

- [ ] Curva de capital train / test / validación con drawdown superpuesto.
- [ ] Tarjeta: Sharpe, Sortino, Calmar, Max Drawdown, Win Rate, Profit Factor.
- [ ] Atribución de costos: P&L bruto → neto, comisiones totales, préstamo total.
- [ ] Bitácora de operaciones filtrable por periodo, dirección (largo/corto) y resultado.
- [ ] Histograma de retornos por operación con normal superpuesta.

## Checklist — Vista técnica

- [ ] Spread S_t con señales de entrada y salida anotadas.
- [ ] β̂_t por activo en el tiempo.
- [ ] Primer eigenvector de Johansen móvil en el tiempo.
- [ ] Ganancia de Kalman en el tiempo, ambos filtros.
- [ ] z-score con líneas de umbral de entrada y salida.
- [ ] Varianza posterior (incertidumbre) de ambos filtros.
- [ ] Sharpe móvil 252 días.

## Checklist — Requisitos

- [ ] Corre con `streamlit run dashboard/app.py`.
- [ ] Todas las gráficas interactivas.
- [ ] Carga desde `artifacts/` y falla con mensaje claro si faltan ("corre python main.py").
- [ ] Guía de uso de una página en el README.

## Criterio de terminado

Las 12 gráficas presentes, interactivas y con etiquetas; guía en README.
