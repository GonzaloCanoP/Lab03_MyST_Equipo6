# 02 — Selección del grupo: universo, correlación, Engle-Granger, Johansen

**Dueño:** _por asignar_ · **Carpeta:** `cointegration/` · **Depende de:** 01 · **Alimenta a:** 03, 05, 08
**Leer antes:** `docs/notas_clase/04_johansen_vecm_kalman_multiactivo.md`, `docs/notas_clase/02_pairs_trading_secuencial.md`

## Objetivo

Encontrar y defender un grupo de **4 activos** con tendencia estocástica común y obtener el vector β ∈ ℝ⁴ del
portafolio más reversivo S_t = βᵀP_t. **Todo sobre la partición de entrenamiento.**

## Parámetros de este módulo

`CORR_THRESHOLD = 0.70`, `CORR_WINDOW = 252`, `PVALUE_THRESHOLD = 0.05` en `cointegration/selection.py`; pata de normalización y signo en `cointegration/johansen.py`. Si cambian, actualizar la tabla de parámetros de `CLAUDE.md`.

## Contrato

- **Lee:** particiones de `data/`.
- **Escribe:** `selection_table.csv`, `johansen_summary.json`, `vector_comparison.csv`, `rolling_eigenvector.parquet`.
- **Expone:** `select_group() -> (tickers, beta_normalizado)`, `half_life(spread) -> float`.

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
- [ ] Universo definido con justificación económica (mismo sector, cadena de suministro o doble listado).
- [ ] Justificación escrita como defensa contra pruebas múltiples (va al reporte).

**Paso 2 — Correlación**
- [ ] Matriz de correlación **móvil** (ventana `CORR_WINDOW` = 252) sobre entrenamiento.
- [ ] Filtro inicial correlación > 0.7 (aclarar si es sobre la media de la correlación móvil o sobre % de tiempo).

**Paso 3 — Engle-Granger**
- [ ] OLS + ADF sobre residuales para cada subgrupo candidato; filtro p-value < 0.05.

**Paso 4 — Johansen**
- [ ] `coint_johansen` con `det_order` y `k_ar_diff` justificados (k por criterio de información sobre VAR).
- [ ] Reportar estadísticos de **traza** y **máximo eigenvalor** con valores críticos.
- [ ] Número de relaciones de cointegración (rango r).
- [ ] Si r > 1: construir spread de **cada** vector, ADF + vida media de cada uno → `vector_comparison.csv`; elegir empíricamente.

**Paso 5 — Validación del vector**
- [ ] ADF del spread elegido (estacionario) y vida media (AR(1)/Ornstein-Uhlenbeck: `-ln 2 / ln(φ)`).
- [ ] Normalización sobre la pata de mayor |peso| y convención de signo → constantes en `cointegration/johansen.py`.

**Paso 6 — Documentación**
- [ ] `selection_table.csv`: **todos** los grupos probados, estadísticos, etapa de descarte y motivo.
- [ ] Número total de grupos evaluados reportado (clave para el argumento de pruebas múltiples).
- [ ] Johansen móvil (ventana fija, avanzando sin look-ahead) → primer eigenvector en el tiempo (figura 4).
- [ ] Discusión: ¿la relación es estructural o artefacto de haber probado muchos grupos? (corrección tipo Bonferroni como referencia, estabilidad del eigenvector, desempeño fuera de muestra).

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
