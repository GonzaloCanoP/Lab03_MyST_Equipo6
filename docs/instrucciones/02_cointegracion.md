# 02 — Selección del grupo: universo, correlación, Engle-Granger, Johansen

**Dueño:** Gonzalo Cano (GC) · **Revisor:** Juan Manuel Espinosa (JME) · **Notebook:** `notebooks/02_seleccion_grupo.ipynb` · **Carpeta:** `cointegration/` · **Depende de:** 01 · **Alimenta a:** 03, 05, 08
**Leer antes:** `docs/notas_clase/04_johansen_vecm_kalman_multiactivo.md`, `docs/notas_clase/02_pairs_trading_secuencial.md`

## Objetivo

Encontrar y defender un grupo de **4 activos** con tendencia estocástica común y obtener el vector β ∈ ℝ⁴ del
portafolio más reversivo S_t = βᵀP_t. **Todo sobre la partición de entrenamiento.**

## Parámetros de este módulo

`CORR_THRESHOLD = 0.70`, `CORR_WINDOW = 252`, `PVALUE_THRESHOLD = 0.05`, `HALF_LIFE_RANGE = (5, 60)`, `GROUP_SIZE = 4` en `cointegration/selection.py`; `DET_ORDER = 0`, `MAX_VAR_LAGS = 10`, `ROLLING_WINDOW = 504`, `ROLLING_STEP = 21`, `ANCHOR_TICKER = "GLD"` y `SIGN_CONVENTION` en `cointegration/johansen.py`. Si cambian, actualizar la tabla de parámetros de `CLAUDE.md`.

## Contrato

- **Lee:** particiones de `data/`.
- **Escribe:** `selection_table.csv`, `johansen_summary.json`, `vector_comparison.csv`, `rolling_eigenvector.parquet`.
- **Expone:** `run_funnel(train_prices, universes) -> selection_table`, `describe_chosen_group(train_prices, tickers, universe) -> (summary, comparison)`, `compute_half_life(spread) -> float`, `normalize_beta(beta, anchor)`, `build_spread(log_prices, beta)`. `main.run_cointegration_stage` devuelve `(tickers, beta_normalizado)`; las demás partes leen `johansen_summary.json`.

## Loop de trabajo

```
REPETIR hasta cumplir el criterio de terminado:
  1. Toma el primer ítem sin [x].
  2. Implementa y corre solo con datos de entrenamiento.
  3. Verifica: compara contra statsmodels / valores críticos; revisa que el conteo de grupos cuadre en la tabla.
  4. Marca [x], registra en docs/decisiones.md, commit.
```

## Checklist

**Paso 1 — Universo**
- [x] Universo definido con justificación económica (mismo sector, cadena de suministro o doble listado).
- [x] Justificación escrita como defensa contra pruebas múltiples (va al reporte) — `universe.py` y discusión del notebook 02.

**Paso 2 — Correlación**
- [x] Matriz de correlación **móvil** (ventana `CORR_WINDOW` = 252) sobre entrenamiento — rendimientos log.
- [x] Filtro inicial correlación > 0.7 → media de los pares (cada uno promediado en el tiempo); el % de tiempo se reporta (`corr_frac_above`).

**Paso 3 — Engle-Granger**
- [x] OLS + ADF sobre residuales (MacKinnon) para pares y grupo, con R², DW y bandera espuria. **Prioriza, no elimina** (`docs/decisiones.md`).

**Paso 4 — Johansen**
- [x] `coint_johansen` con `det_order = 0` y `k_ar_diff` por BIC sobre el VAR en log-niveles.
- [x] Reportar estadísticos de **traza** y **máximo eigenvalor** con valores críticos (90/95/99 %).
- [x] Número de relaciones de cointegración (rango r̂ = 1 por ambas pruebas).
- [x] Spread de **cada** vector, ADF + vida media → `vector_comparison.csv` (se hace aunque r̂ = 1); elección empírica en `choose_vector`.

**Paso 5 — Validación del vector**
- [x] ADF del spread elegido (p = 0.0001) y vida media 25.3 días (OU de clase: `−ln 2 / λ`, ≈ `−ln 2 / ln(φ)`).
- [x] Normalización sobre la pata de mayor |peso| (GLD) y convención de signo → constantes en `cointegration/johansen.py`.

**Paso 6 — Documentación**
- [x] `selection_table.csv`: **todos** los grupos probados, estadísticos, etapa de descarte y motivo.
- [x] Número total de grupos evaluados reportado: 196 (`johansen_summary.json` → `multiple_testing`).
- [x] Johansen móvil (504 días, paso 21, sin look-ahead) → `rolling_eigenvector.parquet` y `docs/figuras/fig04_eigenvector_movil.png`.
- [x] Discusión: ¿la relación es estructural o artefacto de haber probado muchos grupos? — notebook 02 (esperados por azar, 99 %, Bonferroni, mitades de train, Johansen móvil). El desempeño fuera de muestra se completa con el backtest.

## Criterio de terminado

Existe un β normalizado para 4 activos, con spread estacionario en train (ADF p < 0.05), vida media razonable
para operar, tabla completa de selección y figura 4 generada.

## Trampas

- Correr Johansen con todo el histórico (look-ahead en la selección).
- Olvidar que el eigenvector no tiene escala: sin normalizar, los pesos "saltan" entre reestimaciones (rompe la prueba 2).
- Elegir el grupo con mejor backtest en test → eso es data snooping.

## Preguntas probables

- ¿Qué diferencia hay entre traza y max-eigen? ¿Por qué el eigenvalor mayor es el más reversivo?
- ¿Cuántos grupos probaron y por qué su resultado no es suerte?
- ¿Cómo calcularon la vida media y para qué la usan?
