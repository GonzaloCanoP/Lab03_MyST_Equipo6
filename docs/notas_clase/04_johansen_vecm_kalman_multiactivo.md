# 04 — Johansen, VECM y arbitraje multi-activo con Kalman

> Fuente: Sesión 14, módulo de Arbitraje Estadístico (Prof. Luis Carlos Alvarado Garnica, ITESO 2026;
> material original del Prof. Luis Felipe Gómez Estrada). Referencias: Johansen (1991), *Econometrica*;
> Lütkepohl (2005), *New Introduction to Multiple Time Series Analysis*, cap. 6–7; Chan (2013), cap. 2–3;
> Avellaneda & Lee (2010), *Quantitative Finance*.
>
> El contenido sigue lo visto en clase. Los bloques **Diferencia con el Lab03** solo señalan dónde el
> enunciado (`docs/Lab03.pdf`) dice algo distinto; la decisión va a `docs/decisiones.md`.

## 1. Ideas clave

- Un grupo puede hacer lo que un par no: (1) ver relaciones que necesitan tres o más patas (ningún par es
  estacionario pero el trío sí); (2) promediar el ruido idiosincrático; (3) encontrar más de una relación,
  hasta n − 1 portafolios estacionarios independientes.
- Lo que cuesta: más patas = más comisiones; el número de grupos candidatos explota; los pesos son más difíciles de estimar.
- β ∈ ℝⁿ es un **vector de pesos de portafolio**; el signo indica el lado. El par es el caso β = (1, −β).
- Todo depende del **rango de Π** en el VECM: r relaciones de cointegración, Π = αβᵀ.
- **Columnas de β** = vectores cointegrantes; **filas de α** = velocidades de ajuste de cada activo.
- Johansen estima el rango por máxima verosimilitud: estadísticos de **traza** y de **máximo eigenvalor**.
- Eigenvalor más grande = corrección de error más fuerte = **combinación más reversiva**.
- Los eigenvectores no tienen escala ni signo: hay que **normalizar** para comparar estimaciones en el tiempo.
- El vector de pesos se vuelve el **estado** de un filtro de Kalman en ℝⁿ.
- La estrategia pierde dinero por **una posición que deja de revertir**, no por muchas pérdidas pequeñas.

## 2. Notación

| Símbolo | Significado | Nombre en el código |
|---|---|---|
| P_t = (P_t^{(1)}, …, P_t^{(n)})ᵀ | vector de **log-precios** (en esta sesión; no es la covarianza del filtro) | `log_prices` |
| β ∈ ℝⁿ (r = 1) o ℝ^{n×r} | vector(es) cointegrante(s) / pesos del portafolio reversivo | `beta_coint` |
| β̃ | β normalizado (pata ancla = +1) | `beta_norm` |
| j | índice de la pata ancla (mayor \|β_i\| en entrenamiento) | `anchor` |
| S_t = βᵀP_t | spread del portafolio (no es el estado de Powell ni la varianza de innovación) | `spread` |
| Π | matriz de largo plazo del VECM | `Pi` |
| α ∈ ℝ^{n×r} | velocidades de ajuste (cargas) | `alpha_vecm` |
| Γ_i | coeficientes de corto plazo del VECM | `gamma_vecm` |
| c | constante dentro del término de corrección de error | `ect_const` |
| ECT_{t−1} | término de corrección de error βᵀP_{t−1} − c | `ect` |
| λ̂_1 ≥ … ≥ λ̂_n | eigenvalores de Johansen (no son la λ de OU ni la de EWMA) | `eigvals` |
| r, r̂ | rango de cointegración y su estimación | `coint_rank` |
| β_t, z_t | pesos dinámicos / estado del filtro 1 | `beta_t`, `state` |
| c_t | intercepto dinámico del filtro 1 | `intercept_t` |
| V_t | valor del portafolio (equity) | `equity` |
| N_i, q_i | nocional y acciones del activo i | `notional`, `shares` |
| d_t ∈ {−1, 0, +1} | dirección del spread | `direction` |

## 3. Ecuaciones centrales

**Cointegración para n series:** P_t (log-precios, I(1)) es cointegrado si existe β ∈ ℝⁿ, β ≠ 0, con
S_t = βᵀP_t ~ I(0).

**De VAR a VECM.** VAR(p) en niveles: P_t = A₁P_{t−1} + … + A_pP_{t−p} + ε_t. Reescrito como VECM:

$$\Delta P_t = \Pi P_{t-1} + \sum_{i=1}^{p-1}\Gamma_i\,\Delta P_{t-i} + \varepsilon_t,\qquad \Pi = \sum_{i=1}^{p}A_i - I.$$

ΔP_t es estacionario, así que ΠP_{t−1} también debe serlo aunque P_{t−1} sea I(1).

**Condición de rango**

- rank(Π) = 0: no hay cointegración.
- rank(Π) = n: todas las series ya son estacionarias.
- 0 < rank(Π) = r < n: r relaciones de cointegración, Π = αβᵀ con α, β ∈ ℝ^{n×r}.

**Estadísticos de Johansen** (eigenvalores λ̂₁ ≥ … ≥ λ̂_n)

$$LR_{trace}(r_0) = -T\sum_{i=r_0+1}^{n}\ln(1-\hat\lambda_i),\qquad H_0: r\le r_0\ \ \text{vs}\ \ H_a: r > r_0$$

$$LR_{max}(r_0) = -T\ln(1-\hat\lambda_{r_0+1}),\qquad H_0: r = r_0\ \ \text{vs}\ \ H_a: r = r_0+1$$

Se prueba r₀ = 0, 1, … hasta no rechazar; el **primer no-rechazo** da r̂.

**Normalización (escala y signo)**

$$j = \arg\max_i |\beta_i|\ \text{(en el vector de entrenamiento)},\qquad \tilde\beta = \frac{\beta}{\beta_j}\ \Rightarrow\ \tilde\beta_j = +1.$$

Una sola división fija escala y signo.

**Lo que agrega el VECM** (el vector de Johansen como término de corrección de error)

$$\Delta P_t = \alpha\,\underbrace{(\beta^\top P_{t-1} - c)}_{ECT_{t-1}} + \sum_{i=1}^{p-1}\Gamma_i\,\Delta P_{t-i} + \varepsilon_t.$$

Premultiplicando por βᵀ: ΔS_t ≈ (βᵀα)·ECT_{t−1} + …

- Hay corrección si **−2 < βᵀα < 0**.
- Vida media implícita en el modelo: **−ln 2 / ln(1 + βᵀα)**.

**Pruebas múltiples con grupos:** grupos de tamaño 3 a 5 de m activos = C(m,3) + C(m,4) + C(m,5).
Para m = 20: 1 140 + 4 845 + 15 504 = 21 489 grupos → al 5 %, más de mil falsos positivos aunque nada esté
cointegrado. Defensas: racional económico primero, estabilidad entre submuestras, y **revelar el número de
grupos probados**.

**Pesos dinámicos (filtro 1 multi-activo)**

$$\beta_t = \beta_{t-1} + w_t,\quad w_t\sim\mathcal N(0,Q).$$

Identificación: β y cβ describen el mismo portafolio; el estado no está identificado hasta fijar la escala,
p. ej. β_t^{(1)} ≡ 1. Ecuación de observación:

$$\underbrace{P_t^{(1)}}_{y_t} = \underbrace{\big(1,\ -P_t^{(2)},\ \dots,\ -P_t^{(n)}\big)}_{C_t}\ \underbrace{\begin{pmatrix}c_t\\ \beta_t^{(2)}\\ \vdots\\ \beta_t^{(n)}\end{pmatrix}}_{z_t} + v_t,\quad v_t\sim\mathcal N(0,R).$$


**Posiciones con n patas.** Largo el spread: comprar todo activo con β_i > 0 y vender todo activo con β_i < 0,
en proporción a |β_i|. Corto el spread invierte todos los signos.

$$N_i = 0.8\,V_t\cdot\frac{|\beta_t^{(i)}|}{\sum_j|\beta_t^{(j)}|},\qquad
q_i = d_t\cdot\operatorname{sgn}(\beta_t^{(i)})\cdot\frac{N_i}{P_t^{(i)}},\qquad
V_t = \text{cash}_t + \sum_i q_t^{(i)}P_t^{(i)}.$$

Con β = (1, −β) las mismas fórmulas dan las dos patas de un par.

> **Diferencia con el Lab03 — log-precios.** En clase P_t es el vector de **log-precios** (S_t = βᵀP_t sobre
> logs). El enunciado (§3.2) define S_t = βᵀP_t con "P_t el vector de precios", sin decir si son logs.

**Costos que escalan con n:** comisión en cada pata, préstamo en cada pata corta, y **cada cambio de β_t vuelve
a operar las patas**. El beneficio de diversificación no escala igual.

## 4. Algoritmo / pasos

**Ejemplo trabajado — Johansen con eigenvalores supuestos**

n = 3, T = 500, λ̂ = (0.060, 0.025, 0.004); valores críticos al 95 % con término constante.

Primera línea a mano: LR_trace(0) = −500[ln 0.940 + ln 0.975 + ln 0.996] = 30.94 + 12.66 + 2.00 = 45.60.

| H₀ | LR_trace | v.c. | Decisión | LR_max | v.c. | Decisión |
|---|---|---|---|---|---|---|
| r ≤ 0 | 45.60 | 29.80 | rechazar | 30.94 | 21.13 | rechazar |
| r ≤ 1 | 14.66 | 15.49 | no rechazar | 12.66 | 14.26 | no rechazar |
| r ≤ 2 | 2.00 | 3.84 | no rechazar | 2.00 | 3.84 | no rechazar |

Conclusión: el primer no-rechazo es en r₀ = 1; ambos estadísticos dan r̂ = 1: un vector cointegrante, el
eigenvector de λ̂₁.

**Embudo de selección (versión de la clase, 7 etapas)**

| # | Etapa | Criterio y salida |
|---|---|---|
| 1 | Universo candidato | Racional económico: pares del sector, cadena de suministro, listados cruzados, sustitutos |
| 2 | Filtro de correlación móvil | **Media de ρ por pares > 0.7 sobre retornos**, estable entre subventanas. Solo heurística |
| 3 | Pre-filtro Engle–Granger | Sobre los pares (o subgrupos) dentro del grupo, p < 0.05. **Priorización, no eliminación** |
| 4 | Johansen | Traza y máx-eigenvalor vs valores críticos al 95 %; registrar r̂ y los eigenvalores |
| 5 | Selección del vector | Spread de cada columna de β; quedarse con el mejor ADF y una vida media operable |
| 6 | Validación del spread | ADF sobre S_t (p < 0.05), vida media en rango usable (p. ej. **5–60 días**) |
| 7 | Estabilidad | Repetir las etapas 4–6 en subventanas móviles |

> **Diferencia con el Lab03 — embudo de selección (§3.2):**
>
> - El enunciado tiene 6 pasos; la clase agrega la etapa 7 (estabilidad en subventanas).
> - El enunciado llama a Engle–Granger "pre-filtro" con p-value < 0.05; en clase es "priorización, no eliminación".
> - El enunciado pide "correlación móvil > 0.7" sin más detalle; en clase es la media de las correlaciones por
>   pares, sobre retornos, estable entre subventanas.

**Cómo pierde dinero la estrategia:** la relación se termina (fusión, reestructura, divergencia del modelo de
negocio); el spread sigue abriéndose mientras el modelo insiste en que la reversión es inminente. Defensas
típicas: stop sobre |z_t|, holding máximo, re-probar la relación periódicamente, monitorear la incertidumbre y
las innovaciones del filtro.

## 5. Cómo aplica al Lab03

| Concepto | Dónde aparece en el Lab03 |
|---|---|
| Embudo de selección | `cointegration/selection.py` → `selection_table.csv` (todos los grupos, etapa de descarte, total) |
| Traza / máx-eigen / r̂ | `cointegration/johansen.py` → `johansen_summary.json` |
| Vector más reversivo y comparación si r > 1 | `vector_comparison.csv` (ADF + vida media por columna) |
| Normalización j = argmax \|β_i\| | Constantes de pata ancla y signo en `cointegration/johansen.py`; `tests/test_normalization.py` |
| Estabilidad / Johansen móvil | `rolling_eigenvector.parquet` → figura 4 |
| VECM, α, −2 < βᵀα < 0 | `strategy/vecm.py` → `vecm_summary.json`; interpretación de α en el reporte |
| Filtro 1 en ℝⁿ | `kalman/weights_filter.py` con estado z_t = (c_t, β_t^{(2)}, …, β_t^{(n)}) |
| Sizing N_i, q_i | `strategy/sizing.py`; 80 % de V_t |
| Costos con n patas, costo de rebalancear | `backtest/costs.py`; rebalanceo diario vs banda (`rebalance_comparison.csv`) |
| Cómo pierde dinero | stop, holding máximo y discusión de limitaciones en el reporte |
| Pruebas múltiples | Grupos de tamaño fijo 4 → C(m, 4) candidatos; total evaluado + defensa económica del universo |

## 6. Decisiones que la clase deja abiertas (→ `docs/decisiones.md`)

- Log-precios vs precios en nivel para Johansen, filtro 1 y spread (y su consistencia con el sizing).
- Si Engle–Granger elimina o solo prioriza.
- `det_order` y `k_ar_diff` de Johansen/VECM (k por criterio de información sobre el VAR).
- Qué "residual del VECM" alimenta al filtro 2: ECT_{t−1} = βᵀP_{t−1} − c, el spread del filtro 1, o el residual
  de la ecuación; y cómo se concilia con S_t = β̂_tᵀP_t.
- Si el intercepto c_t va en el estado del filtro 1.
- Ventana y paso del Johansen móvil; rango "operable" de la vida media.
- Política de banda de no-rebalanceo (ancho de la banda) frente al rebalanceo diario.

## 7. Preguntas tipo quiz / exposición

- ¿Qué puede hacer un grupo que un par no? ¿Qué cuesta?
- ¿Por qué todo depende del rango de Π? Expliquen los tres casos.
- ¿Qué representan las columnas de β y las filas de α?
- Diferencia entre traza y máximo eigenvalor; cómo se lee la secuencia de pruebas.
- Calculen LR_trace(0) del ejemplo. ¿Por qué el eigenvalor más grande es el más reversivo?
- ¿Por qué hay que normalizar el eigenvector? ¿Qué rompe si no se hace?
- ¿Qué condición sobre βᵀα garantiza corrección? ¿Cómo sale la vida media del VECM?
- ¿Cuántos grupos probaron y por qué su resultado no es suerte?
- Escriban la ecuación de observación del filtro 1. ¿Por qué el estado no está identificado sin fijar una pata?
- ¿Cómo calculan las acciones de cada activo? ¿Por qué 80 % de V_t?
- ¿Cómo pierde dinero esta estrategia y cómo se defienden?
