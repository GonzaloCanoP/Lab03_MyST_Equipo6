# 09 — Formulación como proceso de decisión secuencial (Powell)

**Dueño:** filtro 1 Juan Manuel Espinosa (JME); filtro 2 Gonzalo Cano (GC); sistema completo ambos
**Destino:** sección del reporte · **Leer antes:** `docs/notas_clase/01_sequential_decision_analytics.md`,
`docs/notas_clase/02_pairs_trading_secuencial.md`

## Objetivo

Tres formulaciones completas: **filtro 1**, **filtro 2** y **sistema completo** (KF1 + KF2 + VECM + trading).

## Loop de trabajo

```
PARA CADA formulación en [filtro 1, filtro 2, sistema completo]:
  REPETIR hasta que su checklist esté completo:
    1. Redacta el elemento con la notación de clase.
    2. Verifica que corresponda 1:1 con el código (nombre de función/variable al lado).
    3. Marca [x].
```

## Plantilla por formulación

**Proceso de 6 pasos:** (1) definir el problema, (2) modelar el estado, (3) modelar la transición,
(4) modelar la observación, (5) regla de decisión / política, (6) mecanismo de aprendizaje / actualización.

**5 elementos del modelo:** variables de estado S_t, variables de decisión x_t, información exógena W_{t+1},
función de transición S^M(S_t, x_t, W_{t+1}), función objetivo.

## Checklist

**Filtro 1** (`docs/powell.md`)
- [x] 6 pasos. - [x] 5 elementos. - [x] Cálculo e interpretación de K_t. - [x] Q y R justificados.
- [x] Ejemplo numérico de varios periodos.

**Filtro 2**
- [ ] 6 pasos. - [ ] 5 elementos. - [ ] Cálculo e interpretación de K_t. - [ ] Q y R justificados.
- [ ] Ejemplo numérico de varios periodos.

**Sistema completo**
- [ ] 6 pasos. - [ ] 5 elementos.
- [ ] Estado separado explícitamente en **físico** (posiciones, efectivo), **información** (precios, S_t, z_t) y **creencia** (β̂_t, P_t, μ̂_t, σ̂_t).
- [ ] Política de trading (umbrales, stop, holding) como decisión x_t; clase de política según Powell (ej. PFA).
- [ ] Función objetivo (ej. maximizar riqueza neta de costos / Sharpe esperado).

## Criterio de terminado

Las tres formulaciones redactadas en `docs/` (borrador `docs/powell.md` → luego al reporte) y revisadas por ambos.
