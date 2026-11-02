# 01 — Sequential Decision Analytics (marco de Powell)

> Fuente: Sesión 11, módulo de Arbitraje Estadístico (Prof. Luis Carlos Alvarado Garnica, ITESO 2026;
> material original del Prof. Luis Felipe Gómez Estrada). Referencias: Powell, *Sequential Decision Analytics
> and Modeling* (cap. 1–2, 7); Powell (2022), *Reinforcement Learning and Stochastic Optimization*; Powell (2019), EJOR.
>
> El contenido sigue lo visto en clase. Los bloques **Diferencia con el Lab03** solo señalan dónde el
> enunciado (`docs/Lab03.pdf`) dice algo distinto; la decisión va a `docs/decisiones.md`.

## 1. Ideas clave

- Market making, estrategias técnicas, RL y filtros de Kalman tienen **la misma estructura**: hay un estado,
  se toma una decisión, llega información nueva, el estado cambia y se acumula una recompensa o costo.
- Programación dinámica, programación estocástica, control óptimo, optimización por simulación y RL difieren
  en **cómo diseñan la política**, no en la estructura del problema.
- No se optimiza una secuencia de decisiones x₀, x₁, …, sino una **función** X^π(·) que mapea cualquier estado
  a una decisión.
- El estado tiene tres componentes: **físico** R_t, **información** I_t y **creencia** B_t.
- Preferir **estadísticos suficientes recursivos** (p. ej. actualizar una media) en vez de cargar el historial crudo.
- El subíndice de W_{t+1} **es la regla de causalidad**: una regla X^π(S_t, W_{t+1}) no es una política, es look-ahead.
- Toda política cae en una de **cuatro clases** (PFA, CFA, VFA, DLA) o en un híbrido.
- Primero se describe el problema (pasos 1–4), después se propone la solución (pasos 5–6).

## 2. Notación

| Símbolo | Significado | Nombre en el código |
|---|---|---|
| S_t | estado del sistema en t (**no** confundir con el spread ni con la varianza de la innovación) | `state` |
| R_t | estado físico / de recursos: efectivo, inventario, posiciones | `cash`, `shares` |
| I_t | estado de información: precios, volúmenes, indicadores observados | `prices`, `spread` |
| B_t | estado de creencia: estimación de parámetros desconocidos + su incertidumbre | `beta_hat`, `P_cov`, `mu_hat`, `sigma_hat` |
| x_t | decisión en t, x_t ∈ 𝒳_t | `decision` / `target_shares` |
| X^π(S_t \| θ) | política π con parámetros θ | `policy(state, params)` |
| θ | parámetros ajustables de la política | `params` (→ `artifacts/params.json`) |
| W_{t+1} | información exógena que llega entre t y t+1 | — |
| S^M(·) | función de transición | `step(...)` |
| C(S_t, x_t, W_{t+1}) | contribución (o costo) del periodo | `pnl_t` |
| F̄^π(θ) | desempeño promedio estimado de la política | `objective(...)` |

## 3. Ecuaciones centrales

**Forma canónica**

$$\max_{\pi\in\Pi}\ \mathbb{E}\Big\{\sum_{t=0}^{T} C\big(S_t, X^\pi(S_t), W_{t+1}\big)\ \Big|\ S_0\Big\}
\quad \text{s.a.}\quad S_{t+1} = S^M(S_t, x_t, W_{t+1}).$$

Ciclo: S_t → x_t = X^π(S_t) → W_{t+1} → S_{t+1}, y t ← t+1.

**Ejemplo de transición (estrategia de un activo)**

$$\text{cash}_{t+1} = \text{cash}_t - x_t\,p_{t+1} - \text{cost}(x_t),\qquad
\text{pos}_{t+1} = \text{pos}_t + x_t,\qquad
\sigma^2_{t+1} = \lambda\sigma^2_t + (1-\lambda)\,r^2_{t+1}.$$

Notar que la decisión tomada en t **se ejecuta al precio p_{t+1}**: esta es la convención del curso
(relevante para el backtest: señal en t, ejecución en t+1).

**Criterios de agregación del objetivo:** recompensa acumulada (todo periodo cuenta), recompensa final
(solo importa el resultado terminal), o ajustado por riesgo (reemplazar 𝔼 por una medida de riesgo o
penalizar varianza / drawdown).

**Cuatro clases de políticas**

- Búsqueda de política (ajustar una función para que funcione bien en promedio):
  - **PFA**: X^{PFA}(S_t | θ) = f(S_t, θ). Función analítica, sin optimización embebida.
    Ej.: "comprar si RSI < 30", red neuronal π_θ(s_t).
  - **CFA**: X^{CFA}(S_t | θ) = argmax_{x ∈ 𝒳_t(θ)} C̄^π(S_t, x | θ). Optimización determinista con objetivo o
    restricciones modificadas y ajustadas. Ej.: media-varianza con λ ajustado, inventario de seguridad.
- Lookahead (aproximar las consecuencias de la decisión y optimizar contra esa aproximación):
  - **VFA**: X^{VFA}(S_t) = argmax_{x ∈ 𝒳_t} ( C(S_t, x) + 𝔼[ V̄_{t+1}(S_{t+1}) ] ). Ej.: Bellman, Q-learning, DQN.
  - **DLA**: X^{DLA}(S_t) = argmax_{x_t} ( C(S_t, x_t) + 𝔼[ max_{π̃} Σ_{t'=t+1}^{t+H} C(S̃_{t'}, X̃^{π̃}(S̃_{t'})) ] ).
    Se optimiza sobre un modelo aproximado de los siguientes H periodos, se implementa solo la primera
    decisión y se re-planea. Ej.: control predictivo (MPC), Monte Carlo tree search.

## 4. Algoritmo / pasos

**Los cinco elementos del modelo**

1. **Estado** S_t = (R_t, I_t, B_t): toda la información necesaria en t, junto con la política y el modelo,
   para calcular la decisión, el costo y la transición.
2. **Decisión** x_t = X^π(S_t), sujeta a x_t ∈ 𝒳_t. Ejemplos: par de cotizaciones (B_t, A_t) en market
   making; posición objetivo en acciones en una estrategia técnica; la corrección K_t(y_t − ŷ_t) en un filtro
   de Kalman; una acción del espacio de acciones en RL.
3. **Información exógena** W_{t+1}: precios, volúmenes, ejecuciones, noticias. No se conoce al elegir x_t.
   Se modela como distribución de la que se muestrea (simulación) o como secuencia histórica que se
   reproduce (backtest).
4. **Transición** S_{t+1} = S^M(S_t, x_t, W_{t+1}): el modelo del sistema.
5. **Objetivo**: contribución por periodo + criterio de agregación en el tiempo y en la aleatoriedad.

**Proceso de modelado de seis pasos (versión de la clase)**

1. Narrativa: el problema en lenguaje llano.
2. Elementos centrales: métricas, decisiones, fuentes de incertidumbre.
3. Modelo matemático: los cinco elementos formalmente.
4. Modelo de incertidumbre: el proceso que genera W.
5. Diseño de políticas: elegir y parametrizar X^π.
6. Evaluación de políticas: simular, ajustar θ, comparar.

> **Diferencia con el Lab03 — los seis pasos.** El enunciado (§3.5) enumera otros seis pasos: (1) definir el
> problema, (2) modelar el estado, (3) modelar la transición, (4) modelar la observación, (5) definir la regla
> de decisión y (6) definir el mecanismo de aprendizaje o actualización. Correspondencia aproximada con los de clase:
>
> | Paso Lab03 | Paso de clase (Powell) |
> |---|---|
> | 1. Definir el problema | 1. Narrativa + 2. Elementos centrales |
> | 2. Modelar el estado | 3. Modelo matemático (elemento S_t) |
> | 3. Modelar la transición | 3. Modelo matemático (elemento S^M) |
> | 4. Modelar la observación | 4. Modelo de incertidumbre (W_{t+1}) |
> | 5. Regla de decisión | 5. Diseño de políticas (X^π) |
> | 6. Aprendizaje / actualización | 6. Evaluación de políticas + actualización de B_t |

**Ejemplo de apertura de Powell (inventario de salchicha de una pizzería)**

- Narrativa: al final del día t se decide cuántas libras pedir; el pedido llega la mañana siguiente; lo
  que sobra se guarda. Costo c y precio p conocidos; la demanda no.
- S₀ = (p, c, D̄, σ̄^D); S_t = R_t^{inv}; x_t = cantidad pedida; W_{t+1} = D̂_{t+1}.
- Transición: R^{inv}_{t+1} = max(0, R^{inv}_t + x_t − D̂_{t+1}).
- Contribución: C = −c·x_t + p·min(R^{inv}_t + x_t, D̂_{t+1}).
- Política *order-up-to* (PFA): X^π(S_t | θ) = θ^{max} − R_t si R_t < θ^{min}; 0 en otro caso; θ = (θ^{min}, θ^{max}).
- Evaluación por simulación con N trayectorias D̂ⁿ ~ 𝒩(D̄, (σ̄^D)²):
  F̄^π(θ) = (1/N) Σ_{n=1}^{N} Σ_{t=0}^{T} C(S_t, X^π(S_t | θ), D̂ⁿ_{t+1}), θ* = argmax_θ F̄^π(θ).

- Mismo problema, cuatro clases (los cinco elementos no cambian, solo X^π):

  | Clase | Política | Qué se ajusta / aprende |
  |---|---|---|
  | PFA | Pedir hasta θ^{max} cuando R_t < θ^{min} | θ^{min}, θ^{max} |
  | CFA | Cubrir la demanda pronosticada + colchón de seguridad | colchón θ (en desviaciones estándar) |
  | VFA | Maximizar la ganancia de hoy + valor de lo que sobra | coeficientes de V(R) |
  | DLA | Planear H días sobre escenarios de demanda, aplicar el primero | nada por adelantado; modelo + H |

## 5. Cómo aplica al Lab03

| Concepto | Dónde aparece en el Lab03 |
|---|---|
| Cinco elementos + seis pasos | Reporte: tres formulaciones (filtro 1, filtro 2, sistema completo) — `docs/instrucciones/09_formulacion_powell.md` |
| Estado = (R_t, I_t, B_t) | Sistema completo: físico = efectivo y acciones por activo (`backtest/engine.py`); información = precios, S_t, z_t; creencia = β̂_t, P_t (filtro 1), μ̂_t, σ̂_t (filtro 2) |
| W_{t+1} y causalidad | `tests/test_causality.py`; ejecución de la señal en t al precio de t+1 (`backtest/engine.py`) |
| Política PFA con θ | Regla de bandas sobre z_t: θ = (z_entrada, z_salida, z_stop, h_max), ajustada en train (`strategy/optimization.py`) |
| Evaluación por simulación/backtest | Grid search en entrenamiento, evaluación en prueba y validación (`backtest/walk_forward.py`) |
| Objetivo ajustado por riesgo | Métrica del grid search (p. ej. Sharpe neto de costos) declarada en `params.json` |

## 6. Decisiones que la clase deja abiertas (→ `docs/decisiones.md`)

- Qué criterio de agregación usar como función objetivo del sistema completo (riqueza final neta, Sharpe,
  penalización por drawdown).
- Cómo escribir el estado del sistema completo sin redundancia (qué es estadístico suficiente).
- En qué clase cae la política completa (PFA pura, o híbrido si el sizing incorpora una optimización).

## 7. Preguntas tipo quiz / exposición

- ¿Cuáles son los cinco elementos de un problema de decisión secuencial?
- ¿Por qué se optimiza sobre funciones X^π y no sobre secuencias de decisiones?
- ¿Qué distingue al estado físico, de información y de creencia? Den un ejemplo de cada uno en su estrategia.
- ¿Por qué X^π(S_t, W_{t+1}) no es una política?
- Clasifiquen su regla de trading en PFA / CFA / VFA / DLA y justifiquen.
- ¿Qué diferencia hay entre los pasos 1–4 y los pasos 5–6 del proceso de modelado?
- En el ejemplo de la pizzería, ¿qué cambia entre las cuatro clases de políticas y qué no?
