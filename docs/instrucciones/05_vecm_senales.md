# 05 — VECM, señales, sizing y búsqueda de umbrales

**Dueño:** Gonzalo Cano (GC) · **Revisor:** Juan Manuel Espinosa (JME) · **Notebook:** `notebooks/05_vecm_senales.ipynb` · **Carpeta:** `strategy/` · **Depende de:** 02, 03, 04 · **Alimenta a:** 06, 08
**Leer antes:** `docs/notas_clase/04_johansen_vecm_kalman_multiactivo.md`, `docs/notas_clase/02_pairs_trading_secuencial.md`

## Objetivo

Estimar el VECM con el vector de Johansen como término de corrección de error, derivar el z-score de sus residuales
normalizados por KF2, y traducirlo en posiciones por activo.

> **Aclarado por el profesor (2026-11-02):** los "residuales del VECM" son el **término de corrección de error**
> que el filtro 1 produce día a día (ECT_t = β̂_tᵀP_t − ĉ_t), no el residual ε_t de la ecuación del VECM. Esa es la
> serie que normaliza KF2. El VECM en train aporta α, la condición −2 < βᵀα < 0 y la vida media.
> Ver `docs/decisiones.md`.

## Parámetros de este módulo

`INITIAL_CAPITAL = 1_000_000`, `POSITION_FRACTION = 0.80` en `strategy/sizing.py`; rejilla del grid search en `strategy/optimization.py`. Si cambian, actualizar la tabla de parámetros de `CLAUDE.md`.

## Contrato

- **Lee:** precios, β (Johansen), β̂_t (KF1), salida de KF2.
- **Escribe:** `signals.parquet`, `params.json`, `grid_search.csv`.
- **Expone:** `fit_vecm(train)`, `generate_signals(z, params) -> posición ∈ {-1,0,1}`, `target_positions(signal, beta_t, capital)`.

## Loop de trabajo

```
REPETIR hasta cumplir el criterio de terminado:
  1. Toma el primer ítem sin [x].
  2. Implementa; ajustes y grid search solo en entrenamiento.
  3. Verifica: posiciones con signo correcto, nocional = 80 % del capital, sin señales en burn-in.
  4. Marca [x], registra decisiones, commit.
```

## Checklist

**VECM**
- [ ] VECM estimado en train con el β de Johansen (statsmodels `VECM`, rango r y k_ar_diff consistentes con 02).
- [ ] Reportar α (velocidades de ajuste): ¿qué activos corrigen hacia el equilibrio?
- [x] Definir claramente qué "residual del VECM" alimenta a KF2 → **ECT dinámico del filtro 1** (respuesta del profesor, 2026-11-02; `docs/decisiones.md`).
- [x] El ECT de t usa los pesos **prior** β̂_{t|t−1} (equivale a la innovación de KF1; causal) — decidido 2026-11-04, `docs/decisiones.md`.
- [ ] Comparar el ECT **estático** (β de Johansen fijo, βᵀP_t − c) contra el **dinámico** del filtro 1: gráfica de ambos, ADF y vida media de cada uno; si da tiempo, backtest de ambos (sugerencia del profesor).

**Señales**
- [ ] Largo spread si z_t < −z_entrada; corto si z_t > +z_entrada; salida si |z_t| < z_salida.
- [ ] Stop sobre |z_t| (z_stop).
- [ ] Holding máximo calibrado a la vida media (ej. k · half-life).
- [ ] Señal en t se ejecuta en t+1 (o al cierre de t, decidir y documentar) — sin usar información futura.

**Sizing**
- [ ] Tamaño por activo ∝ β̂_t, signo por dirección; nocional bruto total = 80 % del capital disponible.
- [ ] Rebalanceo diario conforme evoluciona β̂_t **y** política alternativa de banda de no-rebalanceo (para comparar en 06).

**Optimización**
- [ ] Grid search de (z_entrada, z_salida, z_stop) en **train**; métrica objetivo declarada (ej. Sharpe neto de costos).
- [ ] `grid_search.csv` completo y heatmap para el reporte.
- [ ] Parámetros finales congelados en `params.json` antes de evaluar test/validación.

## Criterio de terminado

`signals.parquet` y `params.json` generados por `main.py`; parámetros elegidos solo con train y documentados.

## Trampas

- Grid search sobre test o validación (overfitting que el profesor va a preguntar).
- Confundir dirección: "largo spread" = comprar activos con peso positivo y vender los de peso negativo.

## Preguntas probables

- ¿Qué aporta el VECM si ya tienen el spread de Kalman? ¿Qué dicen los α?
- ¿Qué es exactamente el "residual del VECM" que usan para el z-score? ¿Por qué no es ε_t?
- ¿Qué cambia entre el ECT estático y el dinámico? ¿Cuál revierte más rápido y cuál opera mejor?
- ¿Por qué esos umbrales? ¿Qué tan sensibles son los resultados a ellos?
