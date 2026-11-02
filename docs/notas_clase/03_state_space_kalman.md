# 03 — Modelos de espacio de estados y filtro de Kalman

> Fuente: Sesión 13, módulo de Arbitraje Estadístico (Prof. Luis Carlos Alvarado Garnica, ITESO 2026;
> material original del Prof. Luis Felipe Gómez Estrada). Referencias: Kalman (1960); Harvey (1989),
> *Forecasting, Structural Time Series Models and the Kalman Filter*; Durbin & Koopman (2012), *Time Series
> Analysis by State Space Methods*; Chan (2013), cap. 3; Elliott, van der Hoek & Malcolm (2005), *Quant. Finance*.
>
> El contenido sigue lo visto en clase. Los bloques **Diferencia con el Lab03** solo señalan dónde el
> enunciado (`docs/Lab03.pdf`) dice algo distinto; la decisión va a `docs/decisiones.md`.

## 1. Ideas clave

- Queremos rastrear algo que (a) no observamos directamente, (b) cambia en el tiempo y (c) solo medimos con
  ruido: el hedge ratio β_t.
- OLS de toda la muestra da un solo número y supone que no hay deriva; OLS móvil usa una ventana arbitraria;
  **ninguno dice qué tan segura es la estimación**. El filtro de Kalman sí.
- La creencia que cargamos es z_t | y_{1:t} ~ 𝒩(ẑ_{t|t}, P_{t|t}): **la media y la covarianza son ambas parte del estado**.
- Ciclo de dos fases: **predecir** (empuja la creencia, aumenta la incertidumbre) y **actualizar** (absorbe y_t, la reduce).
- La ganancia de Kalman es una **tasa de aprendizaje adaptativa**: nueva estimación = vieja + ganancia × sorpresa.
- Q grande → ganancia grande → adaptación rápida y estimación ruidosa. R grande → ganancia pequeña → estimación suave y lenta.
- El diagnóstico es la innovación: si el modelo es correcto, las innovaciones normalizadas son ruido blanco con varianza 1.
- Modelo de nivel local para la media del spread; el **z-score se calcula con estadísticos prior**, nunca posterior.
- Un **suavizador** (RTS) usa todos los datos: sirve para investigación, es look-ahead para trading.
- Un filtro es un problema de decisión secuencial; su política es una PFA con θ = (Q, R).

## 2. Notación

| Símbolo | Significado | Nombre en el código |
|---|---|---|
| z_t | estado oculto (p. ej. (α_t, β_t)) | `state` |
| y_t | observación | `obs` |
| A | matriz de transición (aquí A = I) | `A` |
| C_t | matriz de observación (varía con el tiempo) | `C_t` |
| Q | covarianza del ruido de estado w_t | `Q` |
| R | varianza del ruido de observación v_t | `R` |
| ẑ_{t\|t−1}, P_{t\|t−1} | media y covarianza **prior** (tras predecir) — la diapositiva de la ganancia lo escribe P_t⁻ | `state_prior`, `P_prior` |
| ẑ_{t\|t}, P_{t\|t} | media y covarianza **posterior** (tras actualizar) | `state_post`, `P_post` |
| ỹ_t | innovación y_t − C_t ẑ_{t\|t−1} | `innov` |
| S_t | varianza de la innovación (no es el estado de Powell ni el spread) | `innov_var` |
| K_t | ganancia de Kalman | `gain` |
| μ_t | media latente del spread (nivel local) | `mu` |
| q, r | varianzas de estado y de observación del nivel local | `q`, `r` |
| p_t | varianza posterior de μ̂_t | `p_post` |
| ν_t | innovación del nivel local s_t − μ̂_{t−1} | `innov` |
| λ (EWMA) | factor de decaimiento de la varianza (no es la λ de OU ni un eigenvalor de Johansen) | `ewma_decay` |

> **Nota de notación (para el código).** Aquí P es la covarianza; en la sesión 14 y en el enunciado P_t son los precios.
> En el código: `P_cov` / `P_prior` / `P_post` para la covarianza, `prices` para los precios.

## 3. Ecuaciones centrales

**Forma de espacio de estados**

$$\text{Estado: } z_t = A z_{t-1} + w_t,\ \ w_t\sim\mathcal N(0,Q)\qquad
\text{Observación: } y_t = C_t z_t + v_t,\ \ v_t\sim\mathcal N(0,R).$$

Estado oculto arriba (no observado, Markov), observaciones abajo.

**Hedge ratio dinámico (log-precios)**

$$z_t = \begin{pmatrix}\alpha_t\\ \beta_t\end{pmatrix},\quad C_t = (1,\ x_t),\quad y_t = \ln P_t^Y,\quad x_t = \ln P_t^X.$$

A = I: los coeficientes siguen una caminata aleatoria. Q: qué tan rápido deriva el estado. R: qué tan ruidosa
es una observación. C_t variable: es una regresión con coeficientes que cambian.

**Predecir**

$$\hat z_{t|t-1} = A\,\hat z_{t-1|t-1},\qquad P_{t|t-1} = A\,P_{t-1|t-1}A^\top + Q.$$

**Actualizar**

$$\begin{aligned}
\tilde y_t &= y_t - C_t\,\hat z_{t|t-1} && \text{innovación}\\
S_t &= C_t P_{t|t-1} C_t^\top + R && \text{varianza de la innovación}\\
K_t &= P_{t|t-1} C_t^\top S_t^{-1} && \text{ganancia de Kalman}\\
\hat z_{t|t} &= \hat z_{t|t-1} + K_t\,\tilde y_t && \text{estimación corregida}\\
P_{t|t} &= (I - K_t C_t)\,P_{t|t-1} && \text{incertidumbre reducida}
\end{aligned}$$

**Lectura de la ganancia**

$$K_t = \frac{P_t^-}{P_t^- + R} = \frac{\text{incertidumbre de mi estimación}}{\text{incertidumbre de mi estimación} + \text{incertidumbre de la medición}}$$

| Situación | K_t | Comportamiento |
|---|---|---|
| R → 0 (datos limpios) | → C⁻¹ | confía totalmente en la medición |
| R → ∞ (datos ruidosos) | → 0 | ignora la medición, se queda con el prior |
| P → 0 (confiado) | → 0 | el dato nuevo casi no mueve la estimación |
| P grande (incierto) | grande | aprende rápido de lo que llegue |

**Optimalidad**

1. Modelo lineal, ruidos gaussianos independientes y A, C, Q, R correctos: el filtro da el **posterior bayesiano exacto** p(z_t | y_{1:t}).
2. Sin gaussianidad: es el **mejor estimador lineal insesgado**.

En datos financieros (colas pesadas, dinámica mal especificada) Q y R son **parámetros de ajuste**, no constantes físicas.

**El trade-off Q / R**

- Q grande ⇒ ganancia grande ⇒ adaptación rápida, estimación ruidosa.
- R grande ⇒ ganancia pequeña ⇒ estimación suave y lenta.

**Solo importa la razón:** la ganancia depende de Q/R, no de sus niveles absolutos.

**Inicialización:** el filtro necesita un prior (ẑ₀, P₀) y un **burn-in** hasta que P_t se estabilice.

**Diagnóstico — la innovación es el estadístico de prueba:** si el modelo es correcto, las innovaciones normalizadas ỹ_t/√S_t son ruido blanco con varianza 1.

| Observación | Diagnóstico | Corrección |
|---|---|---|
| Innovaciones autocorrelacionadas | el filtro va rezagado | aumentar Q |
| Varianza ≫ 1 | sobreconfiado, P demasiado pequeño | aumentar Q o R |
| Varianza ≪ 1 | subconfiado | disminuir Q |
| Estimación muy brincona | Q/R demasiado grande | disminuir Q |

**Modelo de nivel local (media del spread)**

$$\mu_t = \mu_{t-1} + w_t,\ \ w_t\sim\mathcal N(0,q),\qquad s_t = \mu_t + v_t,\ \ v_t\sim\mathcal N(0,r)\qquad (A = 1,\ C = 1)$$

$$\hat\mu_t = \hat\mu_{t-1} + K_t\,(s_t - \hat\mu_{t-1}),\qquad K_t = \frac{p_{t-1}+q}{p_{t-1}+q+r}.$$

Con ganancia constante esto es una EWMA; aquí la ganancia se adapta.

**Escala del z-score.** La innovación ν_t = s_t − μ̂_{t−1} tiene varianza S_t = p_{t−1} + q + r (implícita en el
modelo), o se estima recursivamente: σ̂²_t = λσ̂²_{t−1} + (1 − λ)ν²_t.

**z-score causal (con estadísticos de t − 1)**

$$z_t = \frac{s_t - \hat\mu_{t|t-1}}{\hat\sigma_{t|t-1}},\qquad z_t^{post} = (1-K_t)\,z_t^{prior}.$$

**Prior, no posterior:** μ̂_{t|t} ya absorbió s_t; por eso z_t^{post} = (1 − K_t) z_t^{prior}.

> **Diferencia con el Lab03 — estado del filtro 2.** El enunciado (§3.4) dice que el estado es la media latente
> μ_t **y la varianza σ²_t**. En clase el estado es solo μ_t (nivel local) y la escala se obtiene de la varianza
> de la innovación S_t = p_{t−1} + q + r o de la EWMA de innovaciones.

## 4. Algoritmo / pasos

**Ciclo de dos fases**

La creencia que se carga es z_t | y_{1:t} ~ 𝒩(ẑ_{t|t}, P_{t|t}).

1. **Predecir** (empuja la creencia hacia adelante): posterior de t−1 → prior ẑ_{t|t−1}, P_{t|t−1}. Te vuelve menos seguro.
2. **Actualizar** (absorbe y_t): innovación, su varianza, ganancia → posterior ẑ_{t|t}, P_{t|t}. Te vuelve más seguro.

Nueva estimación = estimación anterior + ganancia × sorpresa, con la ganancia calculada a partir de la propia
incertidumbre del modelo.

**Ejemplo trabajado 1 — hedge ratio dinámico, 4 días**

Hedge ratio escalar sin intercepto, precios estandarizados: y_t = β_t x_t + v_t;
β̂₀ = 1.00, P₀ = 0.50, Q = 0.01, R = 0.25.

Cómo se calcula: P⁻ = P + Q; ŷ = β̂x; ỹ = y − ŷ; S = x²P⁻ + R; K = P⁻x/S; β̂ ← β̂ + Kỹ; P ← (1 − Kx)P⁻.

| t | (x_t, y_t) | P⁻ | ŷ | ỹ | S | K | β̂_t | P_t |
|---|---|---|---|---|---|---|---|---|
| 1 | (1.0, 1.30) | 0.510 | 1.000 | +0.300 | 0.760 | 0.671 | 1.201 | 0.168 |
| 2 | (1.2, 1.40) | 0.178 | 1.442 | −0.042 | 0.506 | 0.422 | 1.184 | 0.088 |
| 3 | (0.9, 1.20) | 0.098 | 1.065 | +0.135 | 0.329 | 0.267 | 1.220 | 0.074 |
| 4 | (1.1, 1.25) | 0.084 | 1.342 | −0.092 | 0.352 | 0.263 | 1.196 | 0.060 |

Lectura: la ganancia cae conforme P se encoge, pero P no llega a cero porque Q se suma en cada predicción.

**Ejemplo trabajado 2 — media del spread, 6 días**

μ̂₀ = 0, p₀ = 4×10⁻⁴, q = 10⁻⁵, r = 2.5×10⁻³; σ̂ implícita en el modelo (√(p + q + r)); z_in = 2, z_out = 0.5.

| t | s_t | μ̂_{t\|t−1} | σ̂_{t\|t−1} | z_t (prior) | K_t | μ̂_{t\|t} | z_t (posterior) |
|---|---|---|---|---|---|---|---|
| 1 | 0.020 | 0.0000 | 0.0539 | 0.37 | 0.141 | 0.0028 | 0.32 |
| 2 | 0.060 | 0.0028 | 0.0535 | 1.07 | 0.127 | 0.0101 | 0.93 |
| 3 | 0.115 | 0.0101 | 0.0532 | 1.97 | 0.115 | 0.0222 | 1.75 |
| 4 | 0.130 | 0.0222 | 0.0529 | 2.04 → abrir corto | 0.107 | 0.0337 | 1.82 |
| 5 | 0.070 | 0.0337 | 0.0527 | 0.69 → mantener | 0.100 | 0.0373 | 0.62 |
| 6 | 0.015 | 0.0373 | 0.0525 | −0.42 → cerrar | 0.094 | 0.0352 | −0.38 |

El mismo día, dos respuestas: el día 4 el z prior (2.04) cruza z_in; el posterior (1.82) no.

**El filtro como problema de decisión secuencial**

- Estado: S_t = (y_t, x_t [información I_t], ẑ_t, P_t [creencia B_t]). La covarianza es parte del estado.
- Decisión: x_t = K_t ỹ_t, la corrección a la estimación.
- Información exógena: la siguiente observación.
- Transición: las ecuaciones de predecir/actualizar.
- Objetivo: min_π 𝔼[ỹ²_t].
- Clase de política: **PFA con θ = (Q, R)**; la optimización se hizo una vez, analíticamente, al derivar K_t.

> **Nota de notación (para el código).** En esta diapositiva x_t es a la vez el log-precio de X y la decisión, y
> S_t es el estado de Powell además de la varianza de la innovación. En el código: `innov_var` para la varianza de
> la innovación y `state` para el estado.

**Extensiones:** EKF (linealiza con jacobianos), UKF (puntos sigma a través de la no linealidad real), filtro
de partículas (muestras ponderadas; ruido no gaussiano), suavizador RTS (usa todos los datos; solo investigación).

## 5. Cómo aplica al Lab03

| Concepto | Dónde aparece en el Lab03 |
|---|---|
| Predecir / actualizar separados | `kalman/weights_filter.py` y `kalman/signal_filter.py`: métodos `predict()` y `update(obs)` |
| Hedge ratio dinámico | Filtro 1 generalizado a n patas (ver nota 04) |
| Nivel local + z prior | Filtro 2: `zscore_prior(obs)` **antes** de `update` |
| Q, R, P₀, burn-in | Calibrados en entrenamiento; documentados en `params.json` y `docs/decisiones.md` |
| K_t y P_{t\|t} en el tiempo | Figura 5 y diagnósticos de convergencia del dashboard (`kf1_weights.parquet`, `kf2_signal.parquet`) |
| Innovaciones normalizadas | `tests/test_filter.py`: varianza ≈ 1 y sin autocorrelación (Ljung–Box) |
| Filtro vs suavizador | Nunca usar un suavizador para señales (look-ahead) |
| Ejemplos trabajados | Modelo para el ejemplo numérico que pide §3.5 para cada filtro |
| Filtro como PFA θ = (Q, R) | Formulaciones Powell del filtro 1 y del filtro 2 |

## 6. Decisiones que la clase deja abiertas (→ `docs/decisiones.md`)

- Cómo obtener σ̂_t para el filtro 2: S_t implícita, EWMA (¿qué λ?) o estado aumentado.
- Cómo calibrar Q y R en entrenamiento: varianza de residuales para R y razón δ/(1−δ) para Q, máxima verosimilitud, o búsqueda.
- P₀ y duración del burn-in (criterio: cuándo P_t "se estabiliza").
- Piso para σ̂ si colapsa en tramos tranquilos.
- Tolerancia para "varianza cercana a uno" en la prueba 4.

## 7. Preguntas tipo quiz / exposición

- ¿Por qué la covarianza P_t es parte del estado?
- ¿Qué hace la predicción con la incertidumbre y qué hace la actualización?
- Interpreten K_t. ¿Qué pasa si R → 0? ¿Si R → ∞? ¿Si Q → 0?
- ¿Qué garantiza el filtro bajo gaussianidad y qué sin ella?
- ¿Cómo diagnostican que un filtro está bien calibrado? ¿Qué cambian si las innovaciones están autocorrelacionadas?
- ¿Por qué el z-score usa el prior y no el posterior? Muestren el día 4 del ejemplo.
- ¿Qué relación hay entre el filtro de nivel local y una EWMA?
- ¿Por qué un suavizador es look-ahead?
- Formulen el filtro como problema de decisión secuencial. ¿Qué clase de política es?
