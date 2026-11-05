# 03 — Filtro de Kalman 1: pesos dinámicos β_t

**Dueño:** Juan Manuel Espinosa (JME) · **Revisor:** Gonzalo Cano (GC) · **Notebook:** `notebooks/03_filtro1_pesos.ipynb` · **Carpeta:** `kalman/weights_filter.py` · **Depende de:** 02 · **Alimenta a:** 04, 05, 06, 08
**Leer antes:** `docs/notas_clase/03_state_space_kalman.md`, `docs/notas_clase/04_johansen_vecm_kalman_multiactivo.md`,
`docs/notas_clase/01_sequential_decision_analytics.md`

## Objetivo

Rastrear el vector cointegrante β_t en tiempo real y producir el spread variante S_t = β̂_tᵀP_t.

## Parámetros de este módulo

Q, R, P_0 y burn-in como constantes en `kalman/weights_filter.py` (o calibrados en train); se copian a `artifacts/params.json`. Si cambian, actualizar la tabla de parámetros de `CLAUDE.md`.

## Contrato

- **Lee:** precios, β de Johansen (inicialización), pata de normalización.
- **Escribe:** `kf1_weights.parquet` — β̂_t por activo, ganancia K_t, varianza posterior (diag P_t), S_t, innovación.
- **Expone:** clase/función con `predict()` y `update(obs)` separados (necesario para causalidad y para el ejemplo numérico).

## Loop de trabajo

```
REPETIR hasta cumplir el criterio de terminado:
  1. Toma el primer ítem sin [x].
  2. Implementa. Escribe las ecuaciones en el docstring con la notación de clase.
  3. Verifica: innovaciones normalizadas ~ N(0,1), P_t converge, β̂_t no explota, signo estable.
  4. Marca [x], registra Q, R y burn-in en docs/decisiones.md, commit.
```

## Checklist

- [x] Formulación de espacio de estados escrita: estado z_t = (c_t, β_GDX, β_AEM, β_FNV), caminata aleatoria, observación P_GLD = (1, −P_GDX, −P_AEM, −P_FNV) z_t + v_t (log-precios) — docstring de `kalman/weights_filter.py`.
- [x] **Normalización y signo** declarados: la pata ancla (GDX con la tercia; GLD en la iteración 1) fija en +1; el estado son las demás patas y la constante.
- [x] Inicialización: β_0 = β̃ de Johansen en train (leído de `johansen_summary.json`); P_0 = 252·Q.
- [x] Matriz **Q** y valor **R** con justificación: R = varianza de residuales de Johansen en train; Q = q·I con q por separación de escalas (`calibrate_q`); máxima verosimilitud descartada (`docs/decisiones.md`).
- [x] Periodo de **burn-in** de 252 días (columna `burn_in`), documentado.
- [x] Ganancia de Kalman K_t guardada en cada paso (`gain_*` y `absorption` = C_tK_t) → figura 5, panel del filtro 1 (`plot_kalman_gains` acepta el filtro 2).
- [x] Varianza posterior guardada (`var_post_*`, diagonal de P_{t|t}).
- [x] ECT dinámico con pesos **prior** (`ect_dynamic` = ỹ_t) y ECT estático (`ect_static`) para comparar; pesos posteriores para el sizing.
- [x] Figura 3: `docs/figuras/fig03_pesos_dinamicos.png` (+ comparación `ect_estatico_vs_dinamico.png`).
- [x] Ejemplo numérico: ejemplo de clase reproducido por el filtro (4 periodos) y 5 días reales — notebook 03.
- [x] Formulación Powell del filtro 1 → `docs/powell.md`.

## Criterio de terminado

Filtro corre sobre toda la muestra de forma causal, pasa las pruebas de normalización y de filtro (`10_tests.md`),
y las figuras 3 y 5 (parte KF1) existen.

## Trampas

- Estado no identificado: sin fijar una pata, β̂ puede escalar libremente.
- Q demasiado grande → β̂ persigue el ruido y el spread se vuelve estacionario "por construcción" (sin poder predictivo).
- Usar el β̂ posterior de t para construir el spread que decide la operación de t → revisar causalidad.

## Preguntas probables

- ¿Qué significa una ganancia de Kalman alta/baja? ¿Qué pasa si Q → 0? ¿Si R → ∞?
- ¿Por qué normalizaron sobre esa pata?
