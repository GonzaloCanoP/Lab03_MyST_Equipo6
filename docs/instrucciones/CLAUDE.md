# CLAUDE.md — Lab03 MyST Equipo 6

Arbitraje estadístico multi-activo con cointegración (Johansen), dos filtros de Kalman, VECM y backtest
con costos. Materia: Microestructuras y Sistemas de Trading (ITESO). Enunciado original: `docs/Lab03.pdf`.

- **Equipo:** Gonzalo Cano y Juan Manuel Espinosa (2 integrantes → grupo de **4 activos**, justificado como 2·n).
- **Alcance:** todo el Lab03 **excepto la sección 3.7 Risk Parity** (el profesor indicó ignorarla).
  Por lo tanto también se omiten los incisos "Nivel B": figura 9 y la parte Nivel B de la prueba 4.
- **Repositorio:** público, `Lab03_MyST_Equipo6`. Se evalúa el último commit antes de las 23:59 del día previo a la exposición.

## Cómo trabajar en este repo (leer primero)

1. Antes de implementar una parte, lee su archivo en `docs/instrucciones/` y las notas de clase que ese archivo
   indica en `docs/notas_clase/`. La implementación debe seguir la notación y el enfoque vistos en clase.
2. Cada archivo de instrucciones es un **loop de trabajo**: implementar → verificar → marcar checklist → repetir
   hasta que el "Criterio de terminado" se cumpla. Marca `[x]` en el checklist conforme se avance.
3. Respeta el **contrato de artefactos** (abajo). Es lo que permite que cada integrante trabaje en paralelo.
4. Ambos integrantes deben poder explicar **cualquier línea** en la exposición. Al escribir código, prioriza
   claridad sobre astucia y explica el porqué en docstrings; si algo no es obvio, dilo en el reporte.
5. Si una decisión de modelado no está definida en las notas de clase, regístrala en `docs/decisiones.md`
   (fecha, decisión, alternativa descartada, justificación) en vez de decidir en silencio.

## Reglas duras (romperlas invalida resultados)

- **Sin look-ahead.** Selección de activos, Johansen, VECM, grid search de umbrales y calibración de Q/R se hacen
  **solo con la partición de entrenamiento**. Prueba y validación se tocan únicamente para evaluar.
- **z-score con estadísticos previos (prior) a la actualización del filtro 2.** Nunca con la media posterior.
- **Split cronológico 60/20/20** = entrenamiento / prueba / validación, en ese orden temporal.
- **Normalización de β:** se fija la escala sobre una pata (activo con mayor |peso| en el vector de entrenamiento)
  y una convención de signo; ambas declaradas en `cointegration/johansen.py` y en el reporte.
- **Semilla fija: `SEED = 42`**, definida en `main.py` y aplicada con `np.random.seed(SEED)` al inicio del pipeline.
  Toda función con aleatoriedad recibe la semilla como argumento. Documentada en el README.
- **Sin archivos sueltos en la raíz:** solo `README.md`, `requirements.txt`, `.gitignore` y `main.py`
  (estructura obligatoria). Todo lo demás va dentro de su carpeta.
- `python main.py` corre todo el pipeline de punta a punta sin intervención. El dashboard **no** recalcula nada:
  solo lee `artifacts/`.

## Parámetros (cada uno vive en el módulo que lo usa)

No hay archivo de configuración global. Los parámetros globales están arriba de `main.py` y se pasan como
argumentos; los demás son constantes en mayúsculas al inicio de su módulo. Esta tabla es el índice único:
si cambias un valor o lo mueves, actualízala.

| Parámetro | Valor | Dónde vive |
|---|---|---|
| Semilla | `SEED = 42` | `main.py` |
| Rutas (`ARTIFACTS`, `DATA_RAW`, `FIGURES`) | — | `main.py` |
| Ventana histórica | 10–15 años, precios diarios (`START_DATE`, `END_DATE`) | `main.py` |
| Activos por grupo | 4 (2·n, n = 2) | `data/split.py` |
| División | 60 / 20 / 20 cronológica | `data/split.py` |
| Correlación mínima / ventana | 0.7 / 252 días | `cointegration/selection.py` |
| p-value (EG, ADF) | 0.05 | `cointegration/selection.py` |
| Pata de normalización y signo | se decide tras Johansen | `cointegration/johansen.py` |
| Comisión | 0.125 % por operación, entrada y salida, **por pata** | `backtest/costs.py` |
| Tasa de préstamo | 0.25 % anual sobre nocional corto, devengo diario | `backtest/costs.py` |
| Capital inicial | $1,000,000 | `strategy/sizing.py` |
| Tamaño de posición | 80 % del capital disponible, repartido según β̂_t | `strategy/sizing.py` |
| Umbrales z, stop, holding máx. | grid search en train | `strategy/optimization.py` → `artifacts/params.json` |

## Estructura (obligatoria por el enunciado + extras marcados con *)

```
main.py              pipeline completo: python main.py (semilla, rutas y fechas globales)
data/                ingesta, limpieza, validación, split
cointegration/       universo, correlación móvil, Engle-Granger, Johansen, vida media, tabla de selección
kalman/              filtro 1 (pesos β_t) y filtro 2 (μ_t, σ_t² → z_t)
strategy/            VECM, z-score, señales, sizing, grid search de umbrales
backtest/            motor multi-pata con costos, walk-forward, comparación rebalanceo vs banda
performance/         métricas (Sharpe, Sortino, Calmar, MDD, win rate, profit factor, Sharpe móvil 252d)
dashboard/app.py     Streamlit: vista ejecutiva + vista técnica (lee artifacts/)
artifacts/           salidas del backtest (se versionan para que el dashboard corra sin main.py)
tests/               pytest: causalidad, normalización, contabilidad multi-pata, filtro
project_management/  charter.md, sprint_NN.md (uno por semana), postmortem.md
docs/                reporte.pdf, Lab03.pdf, decisiones.md *, instrucciones/ *, notas_clase/ *, figuras/ *
```

Módulos sugeridos (crear al implementar, no antes):
- `data/`: `download.py`, `clean.py`, `validate.py`, `split.py`
- `cointegration/`: `universe.py`, `correlation.py`, `engle_granger.py`, `johansen.py`, `half_life.py`, `selection.py`
- `kalman/`: `weights_filter.py` (KF1), `signal_filter.py` (KF2)
- `strategy/`: `vecm.py`, `signals.py`, `sizing.py`, `optimization.py`
- `backtest/`: `engine.py`, `costs.py`, `walk_forward.py`
- `performance/`: `metrics.py`
- `tests/`: `test_causality.py`, `test_normalization.py`, `test_accounting.py`, `test_filter.py`

## Contrato de artefactos (`artifacts/`)

Formato: `.parquet` para series de tiempo (índice `date`), `.csv` para tablas, `.json` para escalares.
Toda serie de tiempo lleva una columna `split ∈ {train, test, validation}`.

| Archivo | Productor | Contenido |
|---|---|---|
| `prices.parquet` | data | precios limpios de los 4 activos |
| `selection_table.csv` | cointegration | todos los grupos probados, estadísticos, etapa de descarte, motivo |
| `johansen_summary.json` | cointegration | traza, max-eigen, valores críticos, rango, vector elegido, normalización |
| `vector_comparison.csv` | cointegration | por cada vector cointegrante: ADF, p-value, vida media |
| `rolling_eigenvector.parquet` | cointegration | primer eigenvector de Johansen móvil |
| `kf1_weights.parquet` | kalman | β̂_t por activo, ganancia de Kalman, varianza posterior, spread S_t |
| `kf2_signal.parquet` | kalman | μ prior/post, σ prior, innovación, ganancia, varianza posterior, z_t |
| `params.json` | strategy | z_entrada, z_salida, stop, holding máx., Q, R, burn-in, semilla |
| `grid_search.csv` | strategy | resultados de la búsqueda de umbrales en train |
| `signals.parquet` | strategy | z_t, señal, posición objetivo por activo |
| `equity_curve.parquet` | backtest | equity, cash, valor por pata, drawdown, P&L bruto/neto, comisiones, préstamo |
| `trades.csv` | backtest | bitácora: entrada, salida, dirección, días, P&L bruto/neto, costos, motivo de salida |
| `rebalance_comparison.csv` | backtest | rebalanceo diario vs banda de no-rebalanceo |
| `metrics.json` | performance | métricas por split y total |

Si cambias el esquema de un artefacto, actualiza esta tabla **y** avisa al otro integrante.

## Convenciones de código

- Python (versión del `.venv`), dependencias fijadas en `requirements.txt` (`pip freeze` tras instalar).
- Identificadores en inglés (`compute_half_life`), docstrings y comentarios en español.
- Funciones puras y de responsabilidad única; nada de lógica en `main.py` más allá de orquestar.
- Docstring en toda función pública: qué hace, parámetros, retorno, y supuestos (look-ahead, unidades).
- Sin código muerto ni notebooks como entrega (se permiten notebooks de exploración en `notebooks/`, gitignored o no evaluados).
- Figuras: título, ejes etiquetados, leyenda legible. Las del reporte se exportan a `docs/figuras/`.
- Correr `pytest` antes de cada push.

## Flujo de Git (commits balanceados 50/50)

- Rama `main` siempre corre. Trabajo en ramas `feat/<iniciales>-<tema>` (ej. `feat/gc-johansen`, `feat/jme-backtest`).
- Commits pequeños y descriptivos en español: `feat(kalman): filtro 1 con normalización sobre XOM`.
- Cada integrante hace commits **desde su propia cuenta** de GitHub (penalización si alguien no tiene commits).
- Merge vía Pull Request revisado por el otro integrante → ambos conocen todo el código.
- La división de trabajo y dueños de cada parte está en `docs/instrucciones/00_flujo_de_trabajo.md`.

## Mapa de documentación

- `docs/instrucciones/` — una guía por parte del proyecto con pasos, checklist y criterio de terminado.
  `99_checklist_entrega.md` es la revisión final contra la rúbrica.
- `docs/notas_clase/` — resumen de los temas de clase (decisión secuencial de Powell, pairs trading como
  problema secuencial, modelos de espacio de estados y Kalman, Johansen/VECM y arbitraje multi-activo con Kalman).
  **Fuente de verdad para notación y enfoque.**
- `docs/decisiones.md` — bitácora de decisiones de modelado.
