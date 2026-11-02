# Revisión inicial — Lab03_MyST_Equipo6

> Fecha: 2026-11-01 · Base revisada: `09c440f` (rama `main`) · Fuente de verdad: `docs/Lab03.pdf`
> Este archivo **no** se agrega a Git (ver nota al final).

---

## 1. Diagnóstico

**Dónde estamos:** el andamiaje está muy por encima de lo normal para un inicio. La estructura obligatoria
existe casi completa, cada carpeta de código es paquete importable, y `docs/instrucciones/` ya tiene una guía
por parte del proyecto (checklists, contrato de artefactos, trampas, preguntas de exposición) que cubre
prácticamente todo el enunciado. No hay código del pipeline todavía, lo cual es correcto.

**Lo que preocupa de verdad (en orden):**

1. **Juan Manuel tiene 0 commits.** Los 2 commits del repo son de `GonzaloCanoP`. Hoy el repo está 100/0.
   La penalización es 0 en la parte técnica para quien no tenga commits propios. Hay que corregirlo esta misma
   semana (y verificar que `juanm.espinosa@iteso.mx` esté registrado en la cuenta de GitHub
   `juanmanuel-espinosa-iteso`; si no, los commits no se le atribuyen).
2. **`requirements.txt` sin versiones.** Es requisito explícito del enunciado y criterio A de la rúbrica.
3. **La ventana de fechas viola el enunciado.** `START_DATE = "2011-01-01"` a `END_DATE = "2026-10-30"`
   son **≈15.8 años**; el máximo es 15.
4. **Reproducibilidad frágil por `yfinance`.** `data/raw/` está en `.gitignore`, así que en un clon limpio
   `python main.py` depende de que Yahoo responda y devuelva lo mismo. Los precios ajustados cambian
   retroactivamente con cada dividendo nuevo, y `yfinance` falla o cambia de API con frecuencia.
   Si el día de la evaluación falla la descarga: −10 puntos.
5. **Faltan las notas de clase.** Todas las guías dicen que `docs/notas_clase/0X_*.md` son "la fuente de
   verdad para notación y enfoque", pero solo existe el `README.md` de esa carpeta. Hoy esa referencia apunta a nada.
6. **El diseño del split todavía no sirve para la prueba de causalidad** (detalle en §3.4). Conviene
   decidirlo antes de escribir `data/split.py`.

Lo demás son mejoras menores o cosas que conviene dejar preparadas.

---

## 2. Estado actual del repo

```
Lab03_MyST_Equipo6/
├── .gitignore                 14 líneas: .venv, __pycache__, .pytest_cache, checkpoints, data/raw, data/processed
├── README.md                  integrantes, alcance (sin 3.7), instalación, reproducción, semilla, pytest, streamlit; 3 TODO
├── requirements.txt           10 paquetes SIN versión (comentario: "fijar tras pip freeze")
├── main.py                    docstring con las 6 etapas, SEED=42, rutas, START/END_DATE, main() vacío
├── artifacts/.gitkeep
├── backtest/__init__.py       (vacío)
├── cointegration/__init__.py  (vacío)
├── dashboard/__init__.py      (vacío; falta app.py — normal por ahora)
├── data/__init__.py           (vacío)
├── kalman/__init__.py         (vacío)
├── performance/__init__.py    (vacío)
├── strategy/__init__.py       (vacío)
├── tests/__init__.py          (vacío)
├── project_management/
│   ├── charter.md             plantilla: alcance "no hará" lleno; hitos sin fechas; 5 riesgos sin prob/impacto/mitigación; roles TODO
│   ├── sprint_01.md           plantilla vacía
│   └── postmortem.md          encabezados de las 5 secciones exigidas
└── docs/
    ├── Lab03.pdf              enunciado
    ├── decisiones.md          bitácora de decisiones (2 entradas: sin Risk Parity; grupo de 4 activos)
    ├── figuras/.gitkeep
    ├── notas_clase/README.md  índice de 4 notas que NO existen + plantilla
    └── instrucciones/
        ├── CLAUDE.md          reglas del repo: sin look-ahead, z prior, parámetros, contrato de artefactos, Git
        ├── 00_flujo_de_trabajo.md   orden/dependencias, tabla de división 50/50 (vacía), reglas de Git
        ├── 01…12_*.md         una guía por parte: contrato, loop, checklist, trampas, preguntas
        └── 99_checklist_entrega.md  revisión final contra la rúbrica desde un clon limpio
```

**Git:** 2 commits, ambos de Gonzalo (`first commit` + `chore: estructura inicial del proyecto Lab03`, este
último con 35 archivos / 1 030 líneas). Solo existe `main`; no hay ramas `feat/*` todavía. Identidad local en
esta máquina: `juanmanuel-espinosa-iteso <juanm.espinosa@iteso.mx>`, configurada correctamente.

---

## 3. Tabla de revisión

| Elemento | Estado | Qué cambiar | Prioridad |
|---|---|---|---|
| Balance de commits | ❌ | JME con 0 commits. Que los siguientes 3–4 commits de la semana sean de JME (ver §5). Confirmar que el email esté verificado en GitHub. | **ahora** |
| `requirements.txt` | ❌ | Fijar versiones (`==`). Agregar `kaleido` si las figuras del reporte se exportan desde Plotly (si se usa matplotlib, no hace falta). Declarar la versión de Python (3.12) en el README. | **ahora** |
| Ventana de fechas (`main.py`) | ❌ | 15.8 años > 15. P. ej. `START_DATE="2012-01-01"`, `END_DATE="2026-10-30"` (≈14.8 años), o 2016–2026 para tener 10. Registrar en `decisiones.md`. | **ahora** |
| Snapshot de datos | ❌ | Versionar un snapshot de precios crudos (un parquet de ~1–3 MB) y que `main.py` use la caché si existe y solo descargue si falta. Quita la dependencia de Yahoo al evaluar. Requiere quitar `data/raw/` del `.gitignore` o guardar el snapshot en otra ruta. | **ahora** |
| `docs/notas_clase/` | ❌ | Faltan las 4 notas a las que apuntan todas las guías. Generarlas de las presentaciones antes de implementar Kalman/Johansen, o quitar la referencia. | pronto |
| Estructura obligatoria | ✅ | Todas las carpetas existen con el nombre exacto y son paquetes. Faltan `dashboard/app.py` y `docs/reporte.pdf` (normal por ahora). | — |
| `dashboard/__init__.py` | ⚠️ | No hace falta: `streamlit run dashboard/app.py` lo ejecuta como script. Es inofensivo; solo hay que resolver `artifacts/` con `Path(__file__).resolve().parents[1]` y no importar módulos del pipeline. | después |
| Diseño del split / causalidad | ⚠️ | Hoy `split_data(df)` calcula 60/20/20 sobre lo que recibe. Al truncar en *t* para la prueba 1, el corte de train se mueve y todo se reajusta → la prueba falla por diseño. Ver §4.4: fechas de corte congeladas. | **ahora** (antes de `data/split.py`) |
| Parámetros dispersos | ⚠️ | `CLAUDE.md` decide "sin config global; cada constante en su módulo + tabla índice". Riesgo: la tabla se desincroniza, y la prueba de causalidad y el dashboard necesitan exactamente los mismos parámetros. Propuesta de config central en §4.3; **es decisión del equipo** (pregunta 1). | ahora |
| `main.py` | ⚠️ | Bien planteado (solo orquesta). Mejoras: (a) `np.random.default_rng(SEED)` pasado explícito en vez de `np.random.seed` global; en realidad el pipeline casi no tiene aleatoriedad, así que basta con documentarlo; (b) la lista de etapas no incluye "figuras" ni "escribir manifest"; (c) agregar un flag `--from-cache` / `--offline`. | pronto |
| `README.md` | ⚠️ | Buena base. Falta: versión de Python, explicación de "nivel de alcance" con referencia a la indicación del profesor, tiempo esperado de `main.py`, árbol de artefactos, y los 3 TODO (descripción, guía del dashboard, uso de IA). | después (TODO) / pronto (Python) |
| `.gitignore` | ⚠️ | Agregar: `venv/`, `env/`, `.env`, `.vscode/`, `.idea/`, `*.egg-info/`, `.coverage`, `htmlcov/`, `notebooks/` (si se decide no evaluarlos), y `revision_inicial.md` (o mover este archivo). Revisar `data/raw/` según la decisión del snapshot. | ahora |
| `artifacts/` versionado | ✅ | Correcto: el dashboard corre sin `main.py`. Cuidar el tamaño (parquet comprimido; nada mayor a ~20 MB). | — |
| Contrato de artefactos (`CLAUDE.md`) | ✅ | Muy completo. Agregar `split_dates.json`, `run_manifest.json` y `kf1/kf2` con las columnas *prior* y *posterior* separadas (§4.6). | pronto |
| `docs/instrucciones/CLAUDE.md` | ⚠️ | Claude Code solo carga `CLAUDE.md` automáticamente si está en la raíz o en `.claude/`; en `docs/instrucciones/` hay que referenciarlo a mano en cada prompt. La regla "sin archivos sueltos en la raíz" es autoimpuesta: el enunciado exige un **mínimo** de estructura y no prohíbe extras. Decidir (pregunta 6). | después |
| `docs/Lab03.pdf` en repo público | ⚠️ | Es material del profesor en un repo público. Probablemente no hay problema, pero conviene confirmarlo (pregunta 7). | después |
| `project_management/charter.md` | ⚠️ | Plantilla correcta y alineada con §3.8. Falta: "hará", fechas de hitos, prob/impacto/mitigación de los 5 riesgos, roles con carpetas. Propuesta en §6. | **ahora** |
| `sprint_01.md` | ⚠️ | Vacío. Llenarlo con el plan de esta semana (§5). | **ahora** |
| `postmortem.md` | ✅ | Encabezados correctos. Se llena al final. | después |
| `decisiones.md` | ✅ | Buena práctica, ya sirve para el reporte. Agregar la de la ventana de fechas y la fuente de datos. | pronto |
| Configuración de pytest | ⚠️ | Hoy funciona por el modo `prepend` de pytest (sube hasta la raíz porque `tests/` tiene `__init__.py`). Agregar `tests/conftest.py` con fixtures compartidos (precios sintéticos cointegrados con semilla) para que las 4 pruebas corran en < 1 min sin red. | pronto |
| Mensajes de commit | ⚠️ | `first commit` es genérico; el segundo es bueno (convencional, en español). Desde ahora: commits pequeños con prefijo, como ya dice `00_flujo_de_trabajo.md`. Un commit de 1 030 líneas se acepta para el bootstrap, pero que no se repita. | ahora |
| Flujo de ramas/PR | ⚠️ | Definido pero aún no usado. Empezar desde el primer commit de código; los PR también le dan visibilidad al revisor (criterio E/H). | ahora |
| Diseño multi-grupo | ⚠️ | El alcance excluye Risk Parity. Aun así, conviene que el pipeline reciba un `group` explícito (tickers + id) en vez de asumir "el grupo" global; cuesta casi nada y deja la puerta abierta (§4.5). | pronto |

---

## 4. Propuesta de arquitectura (sin código)

### 4.1 Árbol objetivo

```
Lab03_MyST_Equipo6/
├── README.md · requirements.txt · .gitignore · main.py
├── config.py                       ← propuesta (pregunta 1): parámetros centrales, frozen dataclasses
├── data/
│   ├── __init__.py
│   ├── download.py                 descarga + caché (sin lógica de limpieza)
│   ├── clean.py                    alineación de calendario, faltantes (ffill limitado)
│   ├── validate.py                 chequeos → ValidationReport
│   ├── split.py                    fechas de corte CONGELADAS + slicing por fecha
│   └── snapshot/prices_raw.parquet ← versionado (si se aprueba)
├── cointegration/
│   ├── universe.py                 universo candidato + justificación económica (dict documentado)
│   ├── correlation.py              correlación móvil y filtro
│   ├── engle_granger.py            OLS + ADF por subgrupo
│   ├── johansen.py                 Johansen, elección de vector, NORMALIZACIÓN y signo
│   ├── half_life.py                vida media AR(1)/OU
│   ├── rolling.py                  Johansen móvil (figura 4)
│   └── selection.py                orquesta pasos 1–6 → SelectionResult + tabla de grupos
├── kalman/
│   ├── base.py                     (opcional) ecuaciones genéricas predict/update lineales
│   ├── weights_filter.py           KF1: β_t
│   └── signal_filter.py            KF2: μ_t, σ_t² → z_t (prior)
├── strategy/
│   ├── vecm.py                     ajuste VECM en train, α, residuales
│   ├── signals.py                  máquina de estados de la posición (entrada/salida/stop/holding)
│   ├── sizing.py                   z/β̂_t → acciones objetivo por activo
│   └── optimization.py             grid search en train → params congelados
├── backtest/
│   ├── costs.py                    comisión por pata, devengo de préstamo
│   ├── engine.py                   simulación diaria multi-pata, identidad contable
│   └── walk_forward.py             corre train→test→validación con params congelados; rebalanceo vs banda
├── performance/
│   ├── metrics.py                  funciones puras por métrica
│   └── figures.py                  figuras 1–8 del reporte → docs/figuras/
├── pipeline/                       ← opcional, ver 4.2 (o vive en main.py)
├── dashboard/app.py                solo lee artifacts/
├── artifacts/                      salidas (versionadas)
├── tests/
│   ├── conftest.py                 datos sintéticos cointegrados con semilla
│   ├── test_causality.py · test_normalization.py · test_accounting.py · test_filter.py
├── project_management/ charter.md · sprint_01..NN.md · postmortem.md
└── docs/ reporte.pdf · Lab03.pdf · decisiones.md · figuras/ · notas_clase/ · instrucciones/
```

### 4.2 Firmas principales (entra → sale)

Tipos de retorno como `@dataclass(frozen=True)` sencillos; así se puede serializar cada etapa y probarla por separado.

**data/**
- `download_prices(tickers, start, end, cache_path) -> pd.DataFrame` — precios ajustados crudos; lee de la caché si existe.
- `clean_prices(raw, max_ffill=…) -> pd.DataFrame` — intersección de calendario, ffill limitado, nunca bfill.
- `validate_prices(df) -> ValidationReport` — NaN, ≤0, duplicados, orden, saltos anómalos; lanza error si algo es crítico.
- `compute_split_dates(index, fractions) -> SplitDates` — **se llama una sola vez sobre el calendario completo** y se guarda.
- `slice_split(df, dates, name) -> pd.DataFrame` y `label_split(index, dates) -> pd.Series` (columna `split`).

**cointegration/**
- `candidate_groups(universe, k) -> list[tuple[str, ...]]`
- `rolling_correlation_filter(train_prices, window, threshold) -> pd.DataFrame` (estadístico por grupo + pasa/no pasa)
- `engle_granger_test(train_prices, group) -> EGResult`
- `johansen_test(train_prices, group, det_order, k_ar_diff) -> JohansenResult` (traza, max-eig, críticos, rango, eigvecs)
- `compare_vectors(train_prices, johansen) -> pd.DataFrame` (ADF + vida media por columna)
- `normalize_beta(beta, anchor) -> np.ndarray` — escala 1 en la pata ancla, signo fijo.
- `half_life(spread) -> float`
- `select_group(train_prices, cfg) -> SelectionResult` (tickers, β normalizado, ancla, tabla de todos los grupos, n_evaluados)
- `rolling_first_eigenvector(prices, group, window, anchor) -> pd.DataFrame` (causal, para la figura 4)

**kalman/** — clases con estado, pero sin E/S:
- `WeightsFilter(beta0, P0, Q, R, anchor)` con `.predict()`, `.update(prices_t) -> KF1Step` y `run(prices) -> pd.DataFrame`
  (β prior/post, K_t, diag P_t, innovación y su varianza, S_t calculado con **β prior**).
- `SignalFilter(mu0, P0, Q, R)` con `.predict()`, `.zscore_prior(s_t)`, `.update(s_t) -> KF2Step` y `run(spread) -> pd.DataFrame`.
- `calibrate_kf1(train_prices, …) -> KF1Params` y `calibrate_kf2(train_spread, …) -> KF2Params` — **solo train**.

**strategy/**
- `fit_vecm(train_prices, beta, k_ar_diff) -> VECMResult` (α, Γ, residuales de train)
- `vecm_residual(prices, vecm, beta_t) -> pd.Series` — la serie que alimenta a KF2 (definición pendiente, pregunta 4).
- `generate_positions(z, params, half_life) -> pd.DataFrame` (dirección ∈ {-1,0,1}, motivo, días en posición) — recursiva, sin mirar adelante.
- `target_shares(direction, beta_t, prices, equity, fraction) -> pd.DataFrame`
- `grid_search(train_inputs, grid, objective) -> (pd.DataFrame, TradingParams)`

**backtest/**
- `commission(traded_notional_per_leg, rate) -> float`; `borrow_accrual(short_notional, annual_rate, day_count) -> float`
- `run_backtest(prices, targets, costs_cfg, rebalance_policy) -> BacktestResult` (equity_curve, trades, ledger por pata)
- `run_walk_forward(...) -> BacktestResult` (un solo recorrido continuo con columna `split`)
- `compare_rebalance(prices, targets, policies) -> pd.DataFrame`

**performance/**
- `sharpe(r, rf, periods)`, `sortino(...)`, `calmar(...)`, `max_drawdown(equity) -> (mdd, duración)`, `win_rate(trades)`,
  `profit_factor(trades)`, `rolling_sharpe(r, window=252)`, `metrics_by_split(equity, trades) -> dict`

**Orquestación** — una función pura y truncable, distinta de la E/S:
- `run_pipeline(prices, cfg, split_dates, end=None) -> PipelineResult` — todo en memoria, **sin escribir disco**.
- `write_artifacts(result, out_dir)` — la única función que escribe en `artifacts/`.
- `main()` = cargar datos → `compute_split_dates` (una vez) → `run_pipeline` → `write_artifacts` → `figures`.

Separar `run_pipeline` de `write_artifacts` es lo que hace trivial la prueba de causalidad:
`run_pipeline(prices.loc[:t], cfg, split_dates).z[t] == full.z[t]`.

### 4.3 Configuración central (recomendación, sujeta a la pregunta 1)

Un `config.py` en la raíz con dataclasses congeladas, agrupadas por dominio:

```
DataConfig       tickers_universe, start_date, end_date, split=(0.6,0.2,0.2), max_ffill, cache_path
SelectionConfig  n_assets=4, corr_window=252, corr_threshold=0.70, pvalue=0.05, det_order, k_ar_diff
KalmanConfig     burn_in, kf1(Q,R,P0 o "calibrar"), kf2(Q,R,P0 o "calibrar"), sigma_floor
StrategyConfig   initial_capital=1_000_000, position_fraction=0.80, grid (z_in, z_out, z_stop, k_half_life), objective
CostConfig       commission=0.00125, borrow_rate_annual=0.0025, day_count=252 (o 360), execution_lag=1
Config           seed=42, paths, data, selection, kalman, strategy, costs
```

- `main.py` construye `Config()` y lo pasa hacia abajo; ningún módulo lee constantes globales de otro módulo.
- Lo que se **ajusta** (β, Q/R calibrados, umbrales) no va en `config.py`: va en `artifacts/params.json`,
  producido por el pipeline, y se carga como `FittedParams` congelados.
- `write_artifacts` vuelca `Config` completo a `run_manifest.json`, así el dashboard y el reporte muestran
  exactamente los parámetros con los que se corrió.
- Ventaja frente al diseño actual: una sola fuente; la tabla de `CLAUDE.md` pasa a ser "ver `config.py`".
  Si prefieren no tener un archivo extra en la raíz, la alternativa equivalente es definir las dataclasses en
  `main.py` (pero entonces los tests importan `main`, que es menos limpio).

### 4.4 Anti-look-ahead desde el diseño

1. **Fechas de corte congeladas.** `compute_split_dates` corre una vez sobre el calendario completo y se guarda
   en `artifacts/split_dates.json`. Todo lo demás corta **por fecha**, nunca por porcentaje del df que recibe.
   Con eso, truncar en *t* ≥ fin de train deja train intacto y la prueba 1 tiene sentido.
2. **Dos fases explícitas en el código:**
   - `fit(train_prices) -> FittedParams` (selección, Johansen, VECM, calibración Q/R, grid search). Su firma
     solo recibe train; no hay forma de pasarle test por accidente.
   - `run_online(prices, fitted) -> series` (KF1, KF2, señales, backtest). Recursivo: el valor en *t* solo usa
     `prices[:t]` y `fitted`.
3. **Convención de tiempos única** (documentarla en `decisiones.md` y en los docstrings):
   en el cierre de *t* se observa P_t → KF1 predice β_{t|t-1} → S_t = β_{t|t-1}ᵀP_t → KF2 predice μ_{t|t-1}, σ_{t|t-1}
   → z_t (prior) → señal_t → **ejecución a precio de t+1** (o al cierre de t, pero declarado) → luego los `update`.
4. **Grid search** evalúa sobre train con el mismo `run_online` (mismo código, no una versión "rápida").
5. **Burn-in** dentro de train: no se opera durante el burn-in; los filtros sí corren.
6. **Johansen móvil** (figura 4) usa ventana que termina en *t*; es diagnóstico y no alimenta decisiones.
7. **Prueba 1** (causalidad): elegir 3 fechas en test/validación (y opcionalmente en train después del burn-in,
   con `fitted` fijo), comparar `z_t` y además `position_t` de la corrida truncada vs la completa con `np.allclose`.
8. **Guardia barata:** en `run_online`, `assert` de que `fitted.train_end < primera fecha evaluada fuera de muestra`.

### 4.5 Varios grupos sin duplicar (aunque hoy sea uno)

- Que todo reciba un `Group(id, tickers, rationale)` en vez de asumir "el grupo".
- `fit` y `run_online` ya son por grupo; un portafolio multigrupo sería
  `{g.id: run_group(g) for g in groups}` + una capa `portfolio/allocate.py` (Risk Parity) que solo combina
  retornos de spreads. El 80 % aplicaría a nivel consolidado.
- Artefactos con `group_id` como columna (no carpetas por grupo) para que el dashboard filtre igual con 1 o con N.
- Con eso, si el profesor cambia de opinión sobre 3.7, el costo es un módulo nuevo, no una reescritura.
  No recomiendo implementar más que eso mientras 3.7 siga fuera de alcance.

### 4.6 Formatos en `artifacts/`

El contrato actual de `CLAUDE.md` es bueno (parquet para series, csv para tablas, json para escalares). Agregados:

| Archivo | Etapa | Contenido adicional |
|---|---|---|
| `split_dates.json` | data | fin de train, fin de test, fin de validación; nº de días de cada uno |
| `validation_report.json` | data | filas, faltantes tratados, saltos detectados |
| `run_manifest.json` | main | `Config` completo, git hash, fecha de corrida, versiones de paquetes, semilla |
| `kf1_weights.parquet` | kalman | separar `beta_prior_*` / `beta_post_*`, `K_*`, `P_diag_*`, `innov`, `innov_var`, `S_t`, `group_id`, `split` |
| `kf2_signal.parquet` | kalman | `mu_prior`, `mu_post`, `sigma_prior`, `K`, `P_post`, `innov_std`, `z`, `group_id`, `split` |
| `vecm_summary.json` | strategy | α, Γ, k_ar_diff, det_order, residual usado |
| `positions.parquet` | backtest | acciones y valor por activo por día (para la prueba 3 y la vista técnica) |

Regla: el dashboard **solo** lee estos archivos; si falta uno, muestra "corre `python main.py`".

---

## 5. Siguientes pasos de esta semana (sprint 01)

Ordenados por dependencia, cargados hacia JME para nivelar commits. Cada uno es un PR pequeño revisado por el otro.

| # | Paso | Quién | Por qué |
|---|---|---|---|
| 1 | Responder las preguntas de §7 (30 min juntos) y anotarlas en `docs/decisiones.md` | ambos (commit: **JME**) | desbloquea todo lo demás |
| 2 | Llenar `charter.md` (hará/no hará, hitos con fechas, prob/impacto/mitigación, roles) y `sprint_01.md` | **JME** | entregable de gestión + primer commit propio |
| 3 | Llenar la tabla de división 50/50 en `00_flujo_de_trabajo.md` (propuesta abajo) | **GC** | |
| 4 | `requirements.txt` con versiones fijadas + versión de Python en README + `.gitignore` ampliado | **JME** | criterio A, inmediato |
| 5 | Corregir ventana de fechas; crear `config.py` (si se aprueba) y conectarlo en `main.py` | **JME** | base para todo |
| 6 | Definir el universo candidato con justificación económica (`cointegration/universe.py` + texto para el reporte) | **GC** | defensa contra pruebas múltiples |
| 7 | `data/download.py` + snapshot versionado + `clean.py` + `validate.py` | **JME** | parte 01 |
| 8 | `data/split.py` con fechas congeladas + `split_dates.json` | **GC** | clave para causalidad |
| 9 | `tests/conftest.py` con generador de precios sintéticos cointegrados (semilla) | **GC** | lo usan las 4 pruebas |
| 10 | Generar las 4 notas de `docs/notas_clase/` (2 cada uno) | ambos | fuente de notación para KF1/KF2 |

Propuesta de dueños para todo el proyecto (alternando en la cadena para que ambos toquen teoría y backtest):

| Parte | Dueño | Revisor |
|---|---|---|
| 01 Datos | JME | GC |
| 02 Cointegración y selección | GC | JME |
| 03 KF1 pesos | JME | GC |
| 04 KF2 señal | GC | JME |
| 05 VECM, señales, grid search | GC | JME |
| 06 Backtest | JME | GC |
| 07 Métricas + figuras | GC | JME |
| 08 Dashboard | JME (ejecutiva) / GC (técnica) | cruzado |
| 09 Powell | dueño de cada filtro; sistema completo juntos | — |
| 10 Tests | causalidad + filtro: GC · normalización + contabilidad: JME | cruzado |
| 12 PM | sprints alternados | — |

Revisar `git shortlog -sn --no-merges` al cierre de cada sprint.

---

## 6. Gestión del proyecto — contenido sugerido

**Charter (1 página):**
- *Hará:* un grupo de 4 activos, selección completa con tabla, KF1, KF2, VECM, backtest con costos y
  walk-forward, comparación rebalanceo diario vs banda, 8 figuras, 4 pruebas, dashboard Streamlit, reporte PDF.
- *No hará:* 3.7 Risk Parity (indicación del profesor; **pedirla por escrito**), operación en vivo, intradía,
  modelado de impacto de mercado/slippage más allá de la comisión, corrección del sesgo de supervivencia.
- *Hitos* (fechas en función de la expo, ver pregunta 2): ver plan de sprints abajo.
- *Riesgos (≥5, sugeridos):*

| # | Riesgo | P | I | Mitigación |
|---|---|---|---|---|
| 1 | Cointegración se rompe fuera de muestra | Alta | Alto | Selección solo en train; reportarlo honestamente; stop y holding máximo; Johansen móvil como alerta |
| 2 | Divergencia / mala calibración de Kalman (β explota, σ→0) | Media | Alto | Calibrar Q/R en train, piso de σ, prueba 4 de innovaciones, burn-in |
| 3 | Calidad de datos / caída de `yfinance` | Media | Alto | Snapshot versionado, validación automática, ffill limitado |
| 4 | Sesgo de pruebas múltiples en la selección | Alta | Medio | Universo con justificación económica, contar grupos evaluados, referencia Bonferroni |
| 5 | Look-ahead accidental | Media | Alto | Fechas de corte congeladas, separación fit/online, prueba 1 desde el sprint 2 |
| 6 | Commits desbalanceados / integrante sin commits | Alta (hoy) | Alto | Dueños asignados, revisión semanal de `shortlog` |
| 7 | Integrante no puede explicar código del otro | Media | Alto | PR obligatorio con revisor; sesión de preguntas cruzadas |
| 8 | `main.py` no corre en clon limpio | Media | Alto (−10) | Checklist 99 cada viernes desde un clon limpio |

- *Roles:* tabla de §5 con las carpetas de cada quien.

**Plan de sprints** (suponiendo 4 semanas hasta la entrega; ajustar con la fecha real):

| Sprint | Semana | Objetivo | Hito |
|---|---|---|---|
| 01 | 2–8 nov | Base: decisiones, config, datos, split congelado, universo, charter | Pipeline de datos completo |
| 02 | 9–15 nov | Selección completa (corr → EG → Johansen → tabla) + KF1 + pruebas 1 y 2 en esqueleto | Cointegración completa; KF1 validado |
| 03 | 16–22 nov | KF2 + VECM + señales + grid search + backtest + pruebas 3 y 4 | Backtest completo |
| 04 | 23–29 nov | Métricas, figuras, dashboard, reporte, Powell, ensayos, checklist 99 desde clon limpio | Dashboard + reporte en `docs/` |
| — | día previo a la expo, 23:59 | Último commit evaluado; post-mortem | Entrega |

---

## 7. Preguntas para el equipo

1. **Parámetros:** ¿aceptan un `config.py` central (recomendado) o mantienen "constantes por módulo + tabla índice" como dice `CLAUDE.md`?
2. **Fechas:** ¿cuál es la fecha de la exposición? (define la fecha límite real y los hitos).
3. **Universo y fuente:** ¿qué sector/relación económica? (p. ej. bancos regionales de EE. UU., energía integrada, ETFs de doble listado, minoristas). ¿`yfinance` o otra fuente? ¿Aceptan versionar un snapshot de precios?
4. **Spread que alimenta a KF2:** ¿S_t de KF1, el término de corrección βᵀP_{t-1} del VECM, o el residual de la ecuación del VECM? El enunciado dice "residuales del VECM normalizados con KF2"; conviene confirmarlo con la nota de clase o con el profesor.
5. **Walk-forward:** ¿basta con train → test → validación usando parámetros congelados, o quieren reestimar periódicamente (ventanas que avanzan)? Lo segundo es más defendible, pero también más trabajo y complica la prueba de causalidad.
6. **Ejecución y convenciones:** ¿ejecución en t+1 o al cierre de t? ¿Devengo /252 o /360? ¿80 % sobre equity actual o sobre capital inicial?
7. **Dashboard:** el repo ya asume Streamlit; ¿confirmado? (recomendado: menos código que Dash para dos vistas).
8. **Repo:** ¿mantener `Lab03.pdf` en un repo público? ¿Mover `CLAUDE.md` a la raíz para que Claude Code lo cargue solo?
9. **Risk Parity:** ¿tienen la exclusión de 3.7 por escrito (correo o mensaje)? Si la rúbrica la evalúa, es lo único que protege esos puntos.

---

> **Nota:** este archivo vive en la raíz y no está en `.gitignore`. Para que no se agregue por accidente con
> `git add .`, conviene agregar `revision_inicial.md` al `.gitignore` o moverlo fuera del repo cuando ya no se use.
