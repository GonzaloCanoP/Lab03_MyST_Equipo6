# Formulación de Powell (borrador para el reporte)

Plantilla de `docs/instrucciones/09_formulacion_powell.md` y notación de `docs/notas_clase/01_sequential_decision_analytics.md`.
Secciones: filtro 1 (JME), filtro 2 (GC) y sistema completo (ambos).

## Filtro 1 — pesos dinámicos del vector cointegrante (JME)

Código: `kalman/weights_filter.py`. Grupo GLD-GDX-B (iteración 2), pata ancla GDX (peso fijo +1), P_t = log-precios.

### Proceso de 6 pasos

1. **Problema.** Estimar cada día el vector de pesos del portafolio estacionario β_t (y su intercepto c_t), que
   puede derivar con el tiempo, a partir de log-precios observados con ruido. De ahí sale el término de corrección
   de error ECT_t que usa el filtro 2.
2. **Estado.** z_t = (c_t, β_t^{GLD}, β_t^{B})ᵀ. GDX no es parte del estado: su peso vale +1 en la
   ecuación de observación (normalización de Johansen), lo que identifica el estado.
3. **Transición.** Caminata aleatoria: z_t = z_{t−1} + w_t, w_t ~ N(0, Q), Q = q·I.
4. **Observación.** P_t^{GDX} = (1, −P_t^{GLD}, −P_t^{B}) z_t + v_t, v_t ~ N(0, R).
5. **Política.** La regla de actualización de Kalman: ẑ_{t|t} = ẑ_{t|t−1} + K_t ỹ_t con
   K_t = P_{t|t−1} C_tᵀ / S_t. Es una **PFA** (función de política paramétrica) con θ = (Q, R); la optimización
   de la regla se hizo una vez, analíticamente, al derivar K_t.
6. **Aprendizaje.** θ se calibra con entrenamiento: R = varianza de los residuales de Johansen; q es el mayor
   valor con el que el filtro absorbe a lo más 20 % de una desviación durante una operación típica (2 vidas medias).
   La creencia (ẑ_t, P_t) se actualiza cada día con el ciclo predecir → actualizar.

### 5 elementos

| Elemento | Definición | En el código |
|---|---|---|
| Variables de estado S_t | Información I_t = log-precios P_t; creencia B_t = (ẑ_{t\|t}, P_{t\|t}). No hay estado físico: el filtro no tiene posiciones | `log_prices`, `WeightsFilter.state`, `WeightsFilter.P_cov` |
| Decisión x_t | La corrección aplicada a la creencia: x_t = K_t ỹ_t | `update()` |
| Información exógena W_{t+1} | El vector de log-precios del día siguiente | fila de `log_prices` |
| Transición S^M(S_t, x_t, W_{t+1}) | Predecir: ẑ_{t+1\|t} = ẑ_{t\|t}, P_{t+1\|t} = P_{t\|t} + Q. Actualizar: ỹ, S, K, ẑ_{t+1\|t+1}, P_{t+1\|t+1} | `predict()`, `update()` |
| Función objetivo | min_π E[Σ ỹ_t²] (error de predicción de un paso), sujeto a que la deriva de los pesos sea lenta frente a la reversión del spread | criterio de `calibrate_q` |

### Ganancia de Kalman: cálculo e interpretación

- K_t es un vector de 3 componentes (una por estado). Su versión escalar es C_t K_t = 1 − R/S_t: la fracción de
  la sorpresa del día que el filtro absorbe moviendo pesos. En train vale ≈ 0.0038 (mediana): el filtro corrige
  0.38 % de cada sorpresa y deja el resto para que la corrijan los precios.
- Q → 0: K_t → 0, el filtro es el vector estático de Johansen. R → ∞: igual, ignora las observaciones. Q grande
  frente a R: K_t grande, los pesos persiguen al spread y el ECT revierte por construcción (sin poder predictivo).
- En validación C_t K_t sube a ≈ 0.004–0.006: crece la incertidumbre P_t.

### Q y R justificados

- R = 3.31 × 10⁻³: varianza de β̃ᵀ ln P_t − c en train (lo que el vector de Johansen no explica).
- q = 1.6 × 10⁻⁹ (q/R ≈ 4.8 × 10⁻⁷) por separación de escalas: con w̄ = 0.0038 diario, en 58 días (2 vidas medias)
  se absorbe 1 − (1 − 0.0038)^{58} ≈ 20 %. Se descartó máxima verosimilitud porque elige q mucho mayor (en la
  iteración 1, q ≈ 10⁻⁶ con un ECT de vida media de 3–4 días que revierte por el filtro, no por los precios).
- P₀ = 252·Q y burn-in de 252 días (2012).

### Ejemplo numérico

En el notebook 03: (a) el ejemplo 1 de la sesión 13 reproducido por `WeightsFilter` (4 periodos: P⁻, ỹ, S, K, β̂, P);
(b) 5 días reales después del burn-in (prior, innovación, S_t, K_t, C_tK_t, posterior).

## Filtro 2 — media y escala del ECT → z-score (GC)

Código: `kalman/signal_filter.py`. Entrada: ECT dinámico del filtro 1 (pesos prior), desde 2013-01-04.

### Proceso de 6 pasos

1. **Problema.** Estimar cada día la media latente del ECT y su escala para convertir el ECT en un z-score que diga
   qué tan lejos está el portafolio de su equilibrio, sin usar información del día para juzgar al día (z prior).
2. **Estado.** z_t = (μ_t, x_t)ᵀ: μ_t es la media lenta del ECT (nivel local de clase) y x_t la desviación que revierte.
   Se agrega x_t porque el ECT revierte en semanas (vida media ≈ 21 días en train) y el nivel local supone que toda
   desviación es ruido de un día: o persigue al spread o deja innovaciones autocorrelacionadas (`docs/decisiones.md`).
3. **Transición.** μ_t = μ_{t−1} + w^μ_t, x_t = φ x_{t−1} + w^x_t; A = diag(1, φ), Q = diag(q_μ, q_x).
4. **Observación.** ECT_t = μ_t + x_t + v_t, v_t ~ N(0, r); C = (1, 1).
5. **Política.** La regla de Kalman ẑ_{t|t} = ẑ_{t|t−1} + K_t ν_t, K_t = P_{t|t−1} Cᵀ / S_t: una **PFA** con
   θ = (φ, q_μ, q_x, r). La señal que sale es z_t = (ECT_t − μ̂_{t|t−1}) / σ̂_{t|t−1} con
   σ̂²_{t|t−1} = q_x / (1 − φ²) + p^μ_{t|t−1} + r, calculada **antes** de actualizar.
6. **Aprendizaje.** θ se calibra con entrenamiento: φ del AR(1)/OU del ECT; q_x y r por máxima verosimilitud;
   q_μ por separación de escalas (μ̂ absorbe a lo más 20 % de un desplazamiento en 2 vidas medias, el mismo criterio
   del filtro 1). La creencia se actualiza cada día con predecir → actualizar.

### 5 elementos

| Elemento | Definición | En el código |
|---|---|---|
| Variables de estado S_t | Información I_t = ECT_t; creencia B_t = (μ̂_{t\|t}, x̂_{t\|t}, P_{t\|t}). No hay estado físico | `SignalFilter.state`, `SignalFilter.P_cov` |
| Decisión x_t | La corrección aplicada a la creencia: K_t ν_t | `update()` |
| Información exógena W_{t+1} | El ECT del día siguiente (lo produce el filtro 1 con los precios de t + 1) | `ect_dynamic` |
| Transición S^M(S_t, x_t, W_{t+1}) | Predecir: ẑ_{t+1\|t} = A ẑ_{t\|t}, P_{t+1\|t} = A P_{t\|t} Aᵀ + Q. Actualizar: ν, S, K, ẑ_{t+1\|t+1}, P_{t+1\|t+1} | `predict()`, `update()` |
| Función objetivo | min_π E[Σ ν_t²] (verosimilitud de las innovaciones para q_x y r), sujeto a que la media se mueva lento frente a la reversión del ECT (q_μ) | `fit_noise_mle`, `calibrate_q_mu` |

### Ganancia de Kalman: cálculo e interpretación

- K_t = (K^μ_t, K^x_t): de cada sorpresa ν_t, qué fracción mueve la media y cuál la desviación. Con parámetros fijos y
  C constante converge a su estado estable: K^μ ≈ 0.09 y K^x ≈ 0.87 (figura 5, panel 3).
- K^μ es sobre la **sorpresa de un día**, no sobre la desviación: si el ECT queda desplazado de forma permanente, x̂
  absorbe primero y μ̂ solo toma ≈ 20 % del desplazamiento en 42 días.
- q_μ → 0: la media queda fija y z mide distancia a una constante. q_μ grande: μ̂ persigue al ECT y z deja de tener señal.

### Q y R justificados

- φ = 0.967 (vida media 21.2 días, AR(1)/OU del ECT en train).
- q_x = 9.7 × 10⁻⁵ y r = 4.7 × 10⁻⁶ por máxima verosimilitud en train: casi todo el ruido diario es de la desviación
  (√(q_x / (1 − φ²)) ≈ 0.039, la dispersión del ECT) y muy poco es ruido de medición.
- q_μ = 8.6 × 10⁻⁷ por separación de escalas (la verosimilitud casi no depende de q_μ: no lo identifica).
- P₀ = diag(v_x, v_x), μ̂₀ = x̂₀ = 0; burn-in de 63 días.

### Ejemplo numérico

En el notebook 04: (a) el ejemplo 2 de la sesión 13 reproducido por `SignalFilter` (caso φ = 0, q_x = 0), con el día 4
donde el z prior (2.04) abre la operación y el posterior (1.82) no; (b) 5 días reales después del burn-in.

## Política de trading — regla de bandas sobre z_t (GC, parte 05)

Código: `strategy/signals.py`, `strategy/optimization.py`. Insumo para el sistema completo.

- **Decisión.** d_t ∈ {−1, 0, +1}, la dirección del spread decidida al cierre de t. Se ejecuta al cierre de t + 1 con
  q_i = d_t · sgn(β̂_i) · 0.8 V_t |β̂_i| / (Σ|β̂_j| P_i).
- **Estado que usa la política.** z_t (sale de la creencia del filtro 2), la posición actual d_{t−1}, los días en la
  operación h_t y si cada dirección está armada. Estos dos últimos son parte del estado físico: sin ellos la regla
  no sabe cuándo cerrar por holding ni si puede reentrar.
- **Política.** PFA con θ = (z_entrada, z_salida, z_stop, h_max):
  - abre si z_entrada < |z_t| < z_stop;
  - cierra por stop, por holding o por salida direccional, con esa prioridad;
  - después de un stop o un holding, esa dirección se rearma cuando |z_t| < z_entrada.
- **Aprendizaje.** θ se elige con un grid search **en train** que maximiza el Sharpe neto de costos de la simulación
  completa (motor de la parte 06). Resultado: θ = (1.0, 0.5, 3.0, 51 días). La rejilla y el objetivo se registraron
  antes de ver resultados (`docs/decisiones.md`).
- **Objetivo.** max_θ Sharpe(rendimientos netos de comisiones y préstamo) en train, con al menos 10 operaciones. Es la
  versión ajustada por riesgo de max E[Σ P&L neto] de la sesión 11.

## Sistema completo (ambos)

*Pendiente.* Estado físico (posiciones, efectivo), información (precios, ECT_t, z_t) y creencia (β̂_t, P_t, μ̂_t, σ̂_t).
