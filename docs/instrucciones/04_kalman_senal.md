# 04 — Filtro de Kalman 2: media y varianza latentes → z-score

**Dueño:** Gonzalo Cano (GC) · **Revisor:** Juan Manuel Espinosa (JME) · **Notebook:** `notebooks/04_filtro2_senal.ipynb` · **Carpeta:** `kalman/signal_filter.py` · **Depende de:** 03 · **Alimenta a:** 05, 06, 08
**Leer antes:** `docs/notas_clase/03_state_space_kalman.md`, `docs/notas_clase/02_pairs_trading_secuencial.md`

## Objetivo

Estimar en tiempo real μ_t y σ_t² del spread y calcular z_t = (S_t − μ̂_t) / σ̂_t **con estadísticos prior**.

## Parámetros de este módulo

Q, R, inicialización y burn-in como constantes en `kalman/signal_filter.py`; se copian a `artifacts/params.json`. Si cambian, actualizar la tabla de parámetros de `CLAUDE.md`.

## Contrato

- **Lee:** el ECT dinámico que produce KF1 día a día (`kf1_weights.parquet`). Es lo que el enunciado llama "residuales del VECM" (aclarado por el profesor, 2026-11-02; ver 05 y `docs/decisiones.md`).
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

- [x] Modelo de estado: **estado aumentado** (μ_t nivel local + desviación AR(1) x_t), observación ECT_t = μ_t + x_t + v_t; el nivel local es el caso x ≡ 0. Motivo en `docs/decisiones.md`.
- [x] σ̂²_{t|t−1} = q_x / (1 − φ²) + p^μ_{t|t−1} + r (se reduce a p + q + r, la de clase, con x ≡ 0); documentado.
- [x] z_t calculado con μ̂_{t|t-1} y σ̂_{t|t-1} (prior) en `zscore_prior()`, antes de `update`. Comentario explícito en el código.
- [x] Q y R con justificación (φ por OU, q_x y r por MV, q_μ por separación de escalas); inicialización y burn-in de 63 días.
- [x] Ganancia K_t guardada (`gain_mu`, `gain_x`; figura 5 completa) y varianza posterior (`var_post_mu`, `var_post_x`).
- [x] Innovaciones normalizadas con varianza ≈ 1 (0.995 en train con la tercia, tolerancia [0.9, 1.1]) y Ljung–Box del rezago 1 no significativo — `tests/test_filter.py`. A 5–20 rezagos rechaza por el ECT (limitación documentada).
- [x] Figura 6: z-score con líneas de umbral de entrada/salida (umbrales vienen de 05). *(se genera en la parte 05: `docs/figuras/fig06_zscore_umbrales.png`)*
- [x] Ejemplo numérico: ejemplo 2 de la sesión 13 reproducido (6 periodos) y 5 días reales (notebook 04).
- [x] Formulación Powell del filtro 2 en `docs/powell.md`.

## Criterio de terminado

z_t causal verificado por prueba, innovaciones bien comportadas, figuras 5 y 6 generadas.

## Trampas

- Normalizar con la media posterior: usa la observación del día para juzgarse a sí misma.
- σ̂ que colapsa a ~0 en tramos tranquilos → z explota. Considerar un piso o justificar.

## Preguntas probables

- ¿Por qué prior y no posterior? Muéstrenlo en el código.
- ¿Qué ventaja tiene el filtro sobre una media móvil de N días?
