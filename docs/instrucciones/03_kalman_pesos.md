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

- [ ] Formulación de espacio de estados escrita: estado β_t, transición (caminata aleatoria β_t = β_{t-1} + w_t, w ~ N(0,Q)), observación (definir: una pata normalizada vs las demás).
- [ ] **Normalización y signo** declarados: coeficiente de la pata de normalización fijo en 1; el estado son las n−1 restantes (y constante si se usa).
- [ ] Inicialización: β_0 = vector de Johansen en train; P_0 justificado.
- [ ] Matriz **Q** y valor **R** con justificación (ej. R = varianza de residuales en train; Q por razón δ/(1−δ) o máxima verosimilitud en train).
- [ ] Periodo de **burn-in** descartado antes de operar, documentado.
- [ ] Ganancia de Kalman K_t guardada en cada paso (figura 5).
- [ ] Varianza posterior guardada (diagnóstico de convergencia en dashboard).
- [ ] Salida S_t = β̂_tᵀP_t usando β̂ disponible en t (prior si la decisión se toma antes de observar P_t — definir y documentar).
- [ ] Figura 3: evolución de β̂_t, una línea por activo.
- [ ] Ejemplo numérico trabajado de 3–5 periodos (predicción, innovación, K, actualización) para el reporte.
- [ ] Formulación Powell del filtro 1 (ver `09_formulacion_powell.md`).

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
