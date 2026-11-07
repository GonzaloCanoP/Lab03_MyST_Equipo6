# Sprint 02 — 4 al 8 de noviembre de 2026 (entrega)

## Objetivo (2–3 oraciones)

Implementar el pipeline completo, de los datos al backtest, de modo que `python main.py`, `pytest` y el
dashboard corran desde un clon limpio. Cada parte se muestra en su notebook de demostración y el reporte PDF
queda en `docs/` antes del domingo 8 a las 23:59.

## Tareas

| Tarea | Responsable | Estado |
|---|---|---|
| División del trabajo, charter y sprints | JME | hecho |
| Universos candidatos con justificación económica | JME (petroleras) / GC (oro) | hecho |
| Entorno: versiones fijadas, ventana de fechas ≤ 15 años, `.gitignore` | JME | hecho |
| 01 Datos: descarga con snapshot, limpieza, validación, split congelado + notebook 01 + figura 1 | JME | hecho |
| 02 Embudo de selección sobre ambos universos + tabla de grupos + notebook 02 | GC | hecho (en `main`; revisado por JME, 2026-11-04) |
| 03 Filtro 1 + `test_normalization` + notebook 03 | JME | hecho |
| 04 Filtro 2 + `test_filter` + notebook 04 | GC | hecho (figura 6 generada con la parte 05); revisado por JME |
| 05 VECM, señales, grid search + notebook 05 | GC | hecho: VECM, regla con stop/holding/rearme, grid en train, `signals.parquet`, figura 6, heatmap, comparación estático vs dinámico; revisado por JME |
| 06 Backtest + `test_accounting` + notebook 06 | JME | hecho: walk-forward, `equity_curve.parquet`, `trades.csv`, `rebalance_comparison.csv`, figuras 2 y 7, notebook 06 |
| 07 Métricas, figuras 1–8, `test_causality` + notebook 07 | GC | hecho: `performance/metrics.py`, `metrics.json`, figura 8, Sharpe móvil, `test_metrics` y notebook 07; revisado por JME |
| 08 Dashboard: vista ejecutiva / vista técnica | JME / GC | base común (tema tipo terminal, carga de artefactos, app con F1/F2) y vista técnica hechas por GC; vista ejecutiva (6 paneles y cinta) y correcciones de leyendas, selector y tecla activa por JME |
| Iteración 2 de la selección: pruebas fuera del repo, tercia GLD-GDX-B, pipeline, notebooks 01–06, guías y Powell | JME | hecho |
| Reporte, formulación Powell, README final | ambos | pendiente |
| Revisión desde clon limpio (`99_checklist_entrega.md`) y post-mortem | ambos | pendiente |

## Bloqueos y desviaciones

- La prueba exploratoria de los universos (fuera del repo) mostró que el ticker `GOLD` hoy pertenece a
  Gold.com, Inc.; Barrick cotiza como `B`. Se corrige en el universo de oro.
- La misma prueba mostró que el universo de petroleras no pasa el filtro de correlación > 0.7 y que su
  cointegración depende del rezago de Johansen y del episodio de 2020; se documenta en la parte 02.
- Revisión de la parte 02 (JME): el spread estático con β de train pierde la estacionariedad en prueba y validación
  (media desplazada ≈ 10 desviaciones estándar en validación). No cambia la selección; la Q del filtro 1 se
  calibra en train y la comparación estático vs dinámico (parte 05) pasa a ser un resultado central.
- Filtro 1: q se calibra por separación de escalas (no por máxima verosimilitud). El ECT dinámico corrige el
  desplazamiento de prueba pero en validación también se abre (+0.11 de media; el estático +0.44).
- Parte 05: el óptimo del grid (z_entrada = 1) cae en el borde inferior de la rejilla registrada; no se amplió.
  En train el stop nunca se activa, así que z_stop = 3 sale del desempate declarado. Las comisiones son el 26 % del
  P&L bruto en train con rebalanceo diario; la comparación contra la banda (parte 06) importa.
- Backtest: la estrategia gana fuera de muestra pero se degrada (Sharpe neto 0.77 → 0.33 / 0.39); los costos son
  27–54 % del P&L bruto. La banda de rebalanceo de 20 % gana también en train: decidir en equipo si se incluye en el grid.
  (Iteración 1. Con la tercia la banda ya no mejora el Sharpe de train: se mantiene el rebalanceo diario y la banda
  queda como escenario de ahorro de comisiones; ver `docs/decisiones.md`.)
- Iteración 2: GLD-GDX-AEM-FNV perdió la cointegración en validación; tras el proceso de búsqueda (anidado,
  hiperparámetros, recalibración, un solo sector) se cambió a la tercia GLD-GDX-B con autorización del profesor.
