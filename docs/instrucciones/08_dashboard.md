# 08 — Dashboard (Streamlit)

**Dueño:** vista ejecutiva Juan Manuel Espinosa (JME); vista técnica Gonzalo Cano (GC) · **Carpeta:** `dashboard/` · **Depende de:** artefactos de 02–07 · **Alimenta a:** 11

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

## Checklist — Vista ejecutiva (`dashboard/executive.py`, JME; base común en `theme.py` y `data.py`)

- [ ] Curva de capital train / test / validación con drawdown superpuesto.
- [ ] Tarjeta: Sharpe, Sortino, Calmar, Max Drawdown, Win Rate, Profit Factor.
- [ ] Atribución de costos: P&L bruto → neto, comisiones totales, préstamo total.
- [ ] Bitácora de operaciones filtrable por periodo, dirección (largo/corto) y resultado.
- [ ] Histograma de retornos por operación con normal superpuesta.

## Checklist — Vista técnica (`dashboard/technical.py`, GC)

- [x] Spread S_t con señales de entrada y salida anotadas (panel 1: ECT dinámico, μ prior, ▲▼ y motivo de salida).
- [x] β̂_t por activo en el tiempo (panel 3, contra β̃ de Johansen).
- [x] Primer eigenvector de Johansen móvil en el tiempo (panel 4, con traza / crítico).
- [x] Ganancia de Kalman en el tiempo, ambos filtros (panel 5).
- [x] z-score con líneas de umbral de entrada y salida (panel 2, también stop).
- [x] Varianza posterior (incertidumbre) de ambos filtros (panel 6, escala log).
- [x] Sharpe móvil 252 días (panel 7).

## Checklist — Requisitos

- [x] Corre con `streamlit run dashboard/app.py` (`tests/test_dashboard.py` lo verifica en los 4 rangos).
- [ ] Todas las gráficas interactivas.
- [x] Carga desde `artifacts/` y falla con mensaje claro si faltan ("corre python main.py") — `dashboard/data.py`.
- [ ] Guía de uso de una página en el README.

## Criterio de terminado

Las 12 gráficas presentes, interactivas y con etiquetas; guía en README.
