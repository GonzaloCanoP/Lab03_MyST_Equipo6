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
- [x] VECM estimado en train con el β de Johansen (statsmodels `VECM`, rango r y k_ar_diff consistentes con 02): `deterministic="co"`, r = 1, k_ar_diff = 1; su β coincide con β̃ (tolerancia 1e-6) → `vecm_summary.json`.
- [x] Reportar α (velocidades de ajuste): ¿qué activos corrigen hacia el equilibrio? → con la tercia, GDX (α = −0.039, t = −4.1) y B (α = −0.034, t = −3.4) son significativos y el oro no. Solo GDX corrige (β·α = −0.039); B se mueve con GDX y abre el spread (β·α = +0.015). βᵀα = −0.021, vida media 33.3 días (iteración 1: solo GLD, βᵀα = −0.026).
- [x] Definir claramente qué "residual del VECM" alimenta a KF2 → **ECT dinámico del filtro 1** (respuesta del profesor, 2026-11-02; `docs/decisiones.md`).
- [x] El ECT de t usa los pesos **prior** β̂_{t|t−1} (equivale a la innovación de KF1; causal) — decidido 2026-11-04, `docs/decisiones.md`.
- [x] Comparar el ECT **estático** (β de Johansen fijo, βᵀP_t − c) contra el **dinámico** del filtro 1: gráfica de ambos, ADF y vida media de cada uno; si da tiempo, backtest de ambos (sugerencia del profesor). → `compare_static_dynamic`, notebook 05 §9: con el mismo θ, Sharpe neto prueba / validación 0.74 / 1.01 (dinámico) contra 0.20 / 1.31 (estático) con la tercia; el dinámico es más consistente entre particiones (iteración 1: 0.33 / 0.39 contra 0.10 / −0.59).

**Señales**
- [x] Largo spread si z_t < −z_entrada; corto si z_t > +z_entrada; salida si |z_t| < z_salida (salida direccional: el largo cierra en z_t ≥ −z_salida; `docs/decisiones.md`).
- [x] Stop sobre |z_t| (z_stop), con rearme: tras un stop o holding la dirección no reentra hasta |z_t| < z_entrada.
- [x] Holding máximo calibrado a la vida media (ej. k · half-life): h_max = k · 29.1 días, k en el grid → k = 3 (87 días) con la tercia (iteración 1: k = 2, 51 días).
- [x] Señal en t se ejecuta al cierre de t+1: lo hace el motor (`backtest/engine.py`), la estrategia solo entrega la señal de t (`docs/decisiones.md`).

**Sizing**
- [x] Tamaño por activo ∝ β̂_t, signo por dirección; nocional bruto total = 80 % del capital disponible (`strategy/sizing.py`, lo escribió JME porque el motor lo necesita; revisado por GC el 2026-11-07: nocional bruto = 80 % verificado en el notebook 05 §4).
- [x] Rebalanceo diario conforme evoluciona β̂_t **y** política alternativa de banda de no-rebalanceo: parámetro `rebalance_band` del motor (0 = diario).

**Optimización**
- [x] Grid search de (z_entrada, z_salida, z_stop, k) en **train**; métrica objetivo declarada (ej. Sharpe neto de costos). Incluir z_entrada < 2: en train solo ≈ 5 % de los días tienen |z| > 2 con la tercia (1.8 % en la iteración 1).
- [x] `grid_search.csv` completo y heatmap para el reporte (`docs/figuras/grid_search_heatmap.png`).
- [x] Parámetros finales congelados en `params.json` antes de evaluar test/validación: θ = (1.0, 0.0, 2.5, 87 días), Sharpe neto train 0.66, 24 operaciones con la tercia (iteración 1: θ = (1.0, 0.5, 3.0, 51 días), 0.77, 35 operaciones).

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
