# 04 — Filtro de Kalman 2: media y varianza latentes → z-score

**Dueño:** _por asignar_ · **Carpeta:** `kalman/signal_filter.py` · **Depende de:** 03 · **Alimenta a:** 05, 06, 08
**Leer antes:** `docs/notas_clase/03_state_space_kalman.md`, `docs/notas_clase/02_pairs_trading_secuencial.md`

## Objetivo

Estimar en tiempo real μ_t y σ_t² del spread y calcular z_t = (S_t − μ̂_t) / σ̂_t **con estadísticos prior**.

## Parámetros de este módulo

Q, R, inicialización y burn-in como constantes en `kalman/signal_filter.py`; se copian a `artifacts/params.json`. Si cambian, actualizar la tabla de parámetros de `CLAUDE.md`.

## Contrato

- **Lee:** `S_t` de KF1 (o residuales VECM, ver 05).
- **Escribe:** `kf2_signal.parquet` — μ prior, μ posterior, σ prior, innovación, K_t, varianza posterior, z_t.
- **Expone:** `predict()` / `update(obs)` separados; `zscore_prior(obs)` que se calcula **antes** de `update`.

## Loop de trabajo

```
REPETIR hasta cumplir el criterio de terminado:
  1. Toma el primer ítem sin [x].
  2. Implementa con ecuaciones en el docstring.
  3. Verifica causalidad: z_t no cambia si se truncan los datos en t (prueba 1).
  4. Marca [x], registra decisiones, commit.
```

## Checklist

- [ ] Modelo de estado para μ_t (nivel local: μ_t = μ_{t-1} + w_t) y observación S_t = μ_t + v_t.
- [ ] Definir cómo se estima σ_t² (ej. varianza de la innovación F_t = P_prior + R, o EWMA de innovaciones, o estado aumentado) — **confirmar contra notas de clase** y documentar.
- [ ] z_t calculado con μ̂_{t|t-1} y σ̂_{t|t-1} (prior). Comentario explícito en el código.
- [ ] Q y R con justificación; inicialización y burn-in.
- [ ] Ganancia K_t guardada (figura 5, parte KF2) y varianza posterior (diagnóstico).
- [ ] Innovaciones normalizadas con varianza ≈ 1 y autocorrelación no significativa (Ljung-Box) — prueba 4.
- [ ] Figura 6: z-score con líneas de umbral de entrada/salida (umbrales vienen de 05).
- [ ] Ejemplo numérico trabajado de 3–5 periodos para el reporte.
- [ ] Formulación Powell del filtro 2 (ver `09_formulacion_powell.md`).

## Criterio de terminado

z_t causal verificado por prueba, innovaciones bien comportadas, figuras 5 y 6 generadas.

## Trampas

- Normalizar con la media posterior: usa la observación del día para juzgarse a sí misma.
- σ̂ que colapsa a ~0 en tramos tranquilos → z explota. Considerar un piso o justificar.

## Preguntas probables

- ¿Por qué prior y no posterior? Muéstrenlo en el código.
- ¿Qué ventaja tiene el filtro sobre una media móvil de N días?
