# Project Charter — Lab03 Equipo 6

> Máximo una página. Entrega: último commit antes del domingo 8 de noviembre de 2026, 23:59.

## Alcance

**Hará:** seleccionar un grupo de 4 activos cointegrados (2 · n integrantes) a partir de dos universos con
justificación económica (petroleras de EE. UU. y Europa; mineras de oro más el metal), documentando todos los
grupos probados; estimar el vector reversivo con Johansen; filtro de Kalman 1 (pesos dinámicos β_t) y filtro 2
(media y escala del ECT → z-score prior); VECM en entrenamiento; señales con entrada, salida, stop y holding
máximo; backtest multi-pata con comisión, préstamo, 80 % del capital y walk-forward 60/20/20; rebalanceo diario
contra banda de no-rebalanceo; métricas y figuras 1–8; 4 pruebas con pytest; dashboard Streamlit (vista
ejecutiva y técnica); reporte PDF; un notebook de demostración por parte.

**No hará:** Risk Parity entre grupos (sección 3.7, excluida por el profesor; tampoco figura 9 ni la prueba
Nivel B); operación en vivo; datos intradía; modelado de impacto de mercado o slippage más allá de la comisión;
corrección del sesgo de supervivencia más allá de excluir empresas adquiridas.

## Plan de hitos

| Hito | Fecha objetivo | Responsable | Estado |
|---|---|---|---|
| Plan, división del trabajo y universos | 2026-11-04 | JME | hecho |
| Pipeline de datos completo (split congelado, snapshot) | 2026-11-04 | JME | hecho |
| Prueba de cointegración completa (grupo elegido) | 2026-11-05 | GC | pendiente |
| Filtro 1 validado | 2026-11-05 | JME | pendiente |
| Filtro 2 + VECM + señales | 2026-11-06 | GC | pendiente |
| Backtest completo (`python main.py` de punta a punta) | 2026-11-06 | JME | pendiente |
| Métricas, figuras 1–8 y 4 pruebas en verde | 2026-11-07 | GC | pendiente |
| Dashboard funcionando | 2026-11-07 | JME / GC | pendiente |
| Reporte PDF en `docs/` y revisión desde clon limpio | 2026-11-08 | ambos | pendiente |

## Registro de riesgos

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|---|
| 1 | Pérdida de cointegración fuera de muestra | Alta | Alto | Selección solo en train; Johansen móvil como alerta; stop y holding máximo; reportarlo honestamente |
| 2 | Divergencia o mala calibración del filtro (β̂ explota, σ̂ → 0) | Media | Alto | Q/R calibrados en train, burn-in, diagnóstico de innovaciones (prueba 4) |
| 3 | Calidad de datos o caída de yfinance el día de la evaluación | Media | Alto | Snapshot de precios versionado, validación automática, ffill limitado |
| 4 | Sesgo de pruebas múltiples en la selección | Alta | Medio | Universos con justificación económica, conteo de todos los grupos evaluados, criterio fijado antes de ver resultados |
| 5 | Look-ahead accidental (z posterior, split que se mueve, parámetros con test) | Media | Alto | Fechas de corte congeladas, z y ECT con estadísticos prior, prueba de causalidad |
| 6 | Ticker reasignado o con historia incompleta (p. ej. GOLD hoy es Gold.com; Barrick es B) | Media | Medio | Verificar historia de cada ticker en el notebook 01 antes de usarlo |
| 7 | Cointegración de un universo explicada por un solo episodio (COVID 2020 en petroleras) | Media | Medio | Revisar estabilidad por subperiodos y sensibilidad al rezago de Johansen |
| 8 | Tiempo insuficiente (entrega en 5 días) | Alta | Alto | Trabajo en paralelo contra el contrato de artefactos; orden de recortes acordado |
| 9 | Commits desbalanceados o integrante que no puede explicar código del otro | Media | Alto | Dueños por parte, PR revisado por el otro, notebooks por parte para estudiar |

## Roles

| Integrante | Responsabilidades | Carpetas / commits esperados |
|---|---|---|
| Juan Manuel Espinosa (JME) | 01 Datos, 03 Filtro 1, 06 Backtest, dashboard vista ejecutiva, Powell filtro 1, charter y sprints; universo de petroleras | `data/`, `kalman/weights_filter.py`, `backtest/`, `dashboard/` (ejecutiva), `tests/test_normalization.py`, `tests/test_accounting.py`, `project_management/`, notebooks 01, 03, 06 |
| Gonzalo Cano (GC) | 02 Cointegración y selección, 04 Filtro 2, 05 VECM y señales, 07 Métricas y figuras, dashboard vista técnica, Powell filtro 2; universo de oro | `cointegration/`, `kalman/signal_filter.py`, `strategy/`, `performance/`, `dashboard/` (técnica), `tests/test_filter.py`, `tests/test_causality.py`, notebooks 02, 04, 05, 07 |
| Ambos | Powell del sistema completo, reporte, exposición, post-mortem; revisión cruzada de PRs | `docs/`, `README.md`, `main.py` |
