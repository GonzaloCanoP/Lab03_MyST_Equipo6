# Formulación de Powell (borrador para el reporte)

Plantilla de `docs/instrucciones/09_formulacion_powell.md` y notación de `docs/notas_clase/01_sequential_decision_analytics.md`.
Secciones: filtro 1 (JME), filtro 2 (GC) y sistema completo (ambos).

## Filtro 1 — pesos dinámicos del vector cointegrante (JME)

Código: `kalman/weights_filter.py`. Grupo GLD-GDX-AEM-FNV, pata ancla GLD (peso fijo +1), P_t = log-precios.

### Proceso de 6 pasos

1. **Problema.** Estimar cada día el vector de pesos del portafolio estacionario β_t (y su intercepto c_t), que
   puede derivar con el tiempo, a partir de log-precios observados con ruido. De ahí sale el término de corrección
   de error ECT_t que usa el filtro 2.
2. **Estado.** z_t = (c_t, β_t^{GDX}, β_t^{AEM}, β_t^{FNV})ᵀ. GLD no es parte del estado: su peso vale +1 en la
   ecuación de observación (normalización de Johansen), lo que identifica el estado.
3. **Transición.** Caminata aleatoria: z_t = z_{t−1} + w_t, w_t ~ N(0, Q), Q = q·I.
4. **Observación.** P_t^{GLD} = (1, −P_t^{GDX}, −P_t^{AEM}, −P_t^{FNV}) z_t + v_t, v_t ~ N(0, R).
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

- K_t es un vector de 4 componentes (una por estado). Su versión escalar es C_t K_t = 1 − R/S_t: la fracción de
  la sorpresa del día que el filtro absorbe moviendo pesos. En train vale ≈ 0.0044 (mediana): el filtro corrige
  0.44 % de cada sorpresa y deja el resto para que la corrijan los precios.
- Q → 0: K_t → 0, el filtro es el vector estático de Johansen. R → ∞: igual, ignora las observaciones. Q grande
  frente a R: K_t grande, los pesos persiguen al spread y el ECT revierte por construcción (sin poder predictivo).
- En validación C_t K_t sube a ≈ 0.006–0.007: las sorpresas son mayores y la incertidumbre P_t crece.

### Q y R justificados

- R = 1.92 × 10⁻³: varianza de β̃ᵀ ln P_t − c en train (lo que el vector de Johansen no explica).
- q = 9.2 × 10⁻¹⁰ (q/R ≈ 4.8 × 10⁻⁷) por separación de escalas: con w̄ = 0.0044 diario, en 50 días se absorbe
  1 − (1 − 0.0044)^{50} ≈ 20 %. Se descartó máxima verosimilitud porque elige q ≈ 10⁻⁶ y deja un ECT con vida
  media de 3–4 días que revierte por el filtro, no por los precios.
- P₀ = 252·Q y burn-in de 252 días (2012).

### Ejemplo numérico

En el notebook 03: (a) el ejemplo 1 de la sesión 13 reproducido por `WeightsFilter` (4 periodos: P⁻, ỹ, S, K, β̂, P);
(b) 5 días reales después del burn-in (prior, innovación, S_t, K_t, C_tK_t, posterior).

## Filtro 2 — media y escala del ECT → z-score (GC)

*Pendiente.*

## Sistema completo (ambos)

*Pendiente.* Estado físico (posiciones, efectivo), información (precios, ECT_t, z_t) y creencia (β̂_t, P_t, μ̂_t, σ̂_t).
