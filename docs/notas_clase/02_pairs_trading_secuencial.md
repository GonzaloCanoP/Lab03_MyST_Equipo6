# 02 — Pairs trading como problema de decisión secuencial

> Fuente: Sesión 12, módulo de Arbitraje Estadístico (Prof. Luis Carlos Alvarado Garnica, ITESO 2026;
> material original del Prof. Luis Felipe Gómez Estrada). Referencias: Engle & Granger (1987), *Econometrica*;
> Gatev, Goetzmann & Rouwenhorst (2006), *RFS*; Vidyamurthy (2004), *Pairs Trading*; Chan (2013),
> *Algorithmic Trading*, cap. 2–3.
>
> El contenido sigue lo visto en clase. Los bloques **Diferencia con el Lab03** solo señalan dónde el
> enunciado (`docs/Lab03.pdf`) dice algo distinto; la decisión va a `docs/decisiones.md`.

## 1. Ideas clave

- Dos activos ligados por la economía (mismo sector, mismos insumos, sustitutos, doble listado): sus precios
  deambulan, pero la brecha entre ellos (el **spread**) regresa a un nivel normal. Si la brecha es inusualmente
  amplia se vende la pata cara y se compra la barata; cuando cierra, se deshace.
- Cada día la decisión es: abrir largo, abrir corto, mantener o cerrar. Depende de lo que tenemos, lo que
  observamos y lo que **creemos** sobre el nivel normal del spread.
- Los precios casi nunca son estacionarios; los retornos casi siempre sí. Pairs trading busca una
  **combinación estacionaria de dos precios no estacionarios**.
- **Correlación ≠ cointegración.** Pueden ser muy correlacionados y no cointegrados, o cointegrados con
  correlación débil. Solo la cointegración implica un spread que revierte.
- Regresión espuria (Granger–Newbold): dos caminatas aleatorias independientes dan R² alto y t significativa
  sin relación real.
- Engle–Granger: OLS en niveles (log-precios) y ADF sobre los residuales, con valores críticos de
  Engle–Granger / MacKinnon.
- La **vida media** del spread informa el periodo natural de tenencia y la ventana para sus estadísticos.
- La regla de bandas sobre z_t es una **PFA** con θ = (L, z_in, z_out, z_stop, h_max).
- **Pruebas múltiples:** cuenta cuántos candidatos pruebas *antes* de buscar.

## 2. Notación

| Símbolo | Significado | Nombre en el código |
|---|---|---|
| y_t = ln P_t^Y, x_t = ln P_t^X | log-precios de las dos patas (x_t aquí no es la decisión de Powell) | `log_prices` |
| α, β (Engle–Granger) | intercepto y hedge ratio de la relación de largo plazo | `eg_intercept`, `hedge_ratio` |
| s_t | spread y_t − α − βx_t | `spread` |
| s̄ | media de largo plazo del spread | `spread_mean` |
| λ (OU) | velocidad de reversión, λ < 0 | `ou_speed` |
| γ (ADF) | coeficiente de y_{t−1} en la regresión ADF | — (lo da `adfuller`) |
| L | ventana de los estadísticos móviles | `lookback` |
| μ̂_t, σ̂_t | media y desviación estándar estimadas con información hasta t−1 | `mu_prior`, `sigma_prior` |
| z_t | z-score (s_t − μ̂_t)/σ̂_t | `zscore` |
| z_in, z_out, z_stop | umbrales de entrada, salida y stop | `z_entry`, `z_exit`, `z_stop` |
| h_t, h_max | días que lleva abierta la operación y máximo permitido | `holding_days`, `max_holding` |
| d_t ∈ {−1, 0, +1} | dirección objetivo del spread | `direction` |
| q_t^Y, q_t^X | acciones de cada pata | `shares` |

> **Nota de notación (para el código).** En esta sesión α y β aparecen dos veces: en la regresión ADF
> (constante α y tendencia βt) y en Engle–Granger (intercepto y hedge ratio). En la sesión 14 α y β son además
> las cargas y los vectores del VECM, y α también es el nivel de significancia. En el código usamos siempre
> nombres explícitos (`eg_intercept`, `hedge_ratio`, `alpha_vecm`, `beta_coint`, `pvalue_threshold`).

## 3. Ecuaciones centrales

**Estacionariedad débil (covarianza):** para toda t, 𝔼[y_t] = μ, Var(y_t) = σ² < ∞,
Cov(y_t, y_{t−k}) = γ_k (depende solo de k).

**Orden de integración:** y_t ~ I(d) si se vuelve estacionaria tras diferenciar d veces.
I(0): estacionaria (retornos). I(1): caminata aleatoria (precios, log-precios).

**Caminata aleatoria con deriva**

$$y_t = \mu + y_{t-1} + \varepsilon_t \ \Rightarrow\ y_t = y_0 + \mu t + \sum_{i=1}^{t}\varepsilon_i,\qquad \operatorname{Var}(y_t) = t\sigma^2.$$

La varianza crece sin límite y los choques son permanentes.

**ADF**

$$\Delta y_t = \alpha + \beta t + \gamma\,y_{t-1} + \sum_{i=1}^{p}\delta_i\,\Delta y_{t-i} + \varepsilon_t,\qquad
H_0:\gamma = 0\ \text{(raíz unitaria)},\quad H_a:\gamma < 0\ \text{(estacionaria)}.$$

- Valores críticos de la distribución Dickey–Fuller, no de la t.
- No rechazar ≠ aceptar: ADF tiene poca potencia cerca de la raíz unitaria.
- Los términos deterministas (constante, tendencia) cambian los valores críticos.

**Diagnóstico de regresión espuria:** R² alto con Durbin–Watson cercano a cero. Si R² > DW, sospechar.

**Cointegración de un par:** y_t, x_t ~ I(1) son cointegradas si existen α, β con
s_t = y_t − α − βx_t ~ I(0). Con log-precios, Δs_t ≈ r_t^Y − β r_t^X: **los pesos son pesos en dólares**.

**Engle–Granger en dos pasos**

1. OLS en niveles: y_t = α + βx_t + s_t. Bajo cointegración β̂ es **superconsistente** (converge a tasa T, no √T).
2. ADF sobre ŝ_t: H₀: ŝ_t ~ I(1) (no cointegración) vs H_a: ŝ_t ~ I(0), con valores críticos de Engle–Granger / MacKinnon.

Limitaciones: el orden (y sobre x vs x sobre y) importa; un solo β̂ fijo; solo dos series y a lo más una relación.

**Vida media (Ornstein–Uhlenbeck en tiempo discreto)**

$$\Delta s_t = \lambda\,(s_{t-1} - \bar s) + \varepsilon_t,\quad \lambda < 0
\qquad\Rightarrow\qquad \text{vida media} = -\frac{\ln 2}{\lambda}.$$

Es el número esperado de periodos para que una desviación se reduzca a la mitad. Informa el periodo natural de
tenencia y una ventana razonable para los estadísticos del spread.

**z-score con estadísticos móviles hasta t−1**

$$\hat\mu_t = \frac1L\sum_{k=1}^{L}s_{t-k},\qquad
\hat\sigma_t = \sqrt{\frac{1}{L-1}\sum_{k=1}^{L}(s_{t-k}-\hat\mu_t)^2},\qquad
z_t = \frac{s_t-\hat\mu_t}{\hat\sigma_t}.$$

La ventana termina en t−1: s_t no entra en sus propios estadísticos (misma idea que el z prior del filtro 2).

**Regla de trading** (h_t = días que lleva abierta la operación)

$$d_t = \begin{cases}
+1\ \text{(largo spread)} & \text{plano y } z_t < -z_{in}\\
-1\ \text{(corto spread)} & \text{plano y } z_t > +z_{in}\\
0\ \text{(cerrar)} & |z_t| < z_{out}\ \text{o}\ |z_t| > z_{stop}\ \text{o}\ h_t \ge h_{max}\\
d_{t-1}\ \text{(mantener)} & \text{en otro caso}
\end{cases}$$

Largo el spread (s_t = y_t − α − βx_t demasiado bajo, Y barata frente a X): comprar Y, vender β de X.
Corto el spread invierte ambas patas.

**Pruebas múltiples:** con m activos hay C(m, 2) pares. Para m = 20: 190 pares; al 5 % se esperan ≈ 9.5
falsos positivos aunque nada esté cointegrado.

## 4. Algoritmo / pasos

1. Definir el universo con justificación económica (sector, insumos, sustitutos, doble listado) y contar los candidatos.
2. Verificar que cada serie es I(1) (ADF en niveles no rechaza; ADF en diferencias sí rechaza).
3. Engle–Granger: OLS en log-precios → ADF sobre residuales con valores críticos de MacKinnon.
4. Vida media del spread vía regresión AR(1)/OU sobre Δs_t.
5. z-score con ventana L terminada en t−1.
6. Regla de bandas → d_t; posiciones q^Y, q^X según el hedge ratio.
7. Formular todo como problema de decisión secuencial (estado, decisión, W, transición, objetivo).

**El par en el marco de Powell**

- Estado inicial S₀: parámetros fijos durante el trading: α̂, β̂, θ de la regla, costos.
- Estado dinámico:

  $$S_t = \big(\underbrace{\text{cash}_t,\ q_t^Y,\ q_t^X,\ h_t}_{R_t:\ \text{físico}},\ \underbrace{P_t^Y,\ P_t^X,\ s_t}_{I_t:\ \text{información}},\ \underbrace{\hat\mu_t,\ \hat\sigma_t}_{B_t:\ \text{creencia}}\big)$$

  μ̂_t y σ̂_t son **creencias** sobre el nivel y el ancho del spread, no observaciones.
- Política: PFA con θ = (L, z_in, z_out, z_stop, h_max).
- Límites de este modelo: hedge ratio congelado en S₀; la ventana móvil es una creencia burda; solo dos patas y una relación.
  (Los tres los resuelven las sesiones 13 y 14: Kalman para β_t y μ_t, Johansen para n patas.)

## 5. Cómo aplica al Lab03

| Concepto | Dónde aparece en el Lab03 |
|---|---|
| ADF, orden de integración | `cointegration/` (validación I(1) y ADF del spread); prueba ADF del spread elegido |
| Correlación ≠ cointegración | Filtro de correlación > 0.7 solo como heurística (§3.2 paso 2) |
| Engle–Granger | Pre-filtro sobre subgrupos (`cointegration/engle_granger.py`) |
| Vida media | `cointegration/half_life.py`; calibra el holding máximo h_max |
| z-score causal | Lo reemplaza el filtro 2 con estadísticos prior (`kalman/signal_filter.py`) |
| Regla de bandas | `strategy/signals.py` |
| Estado (R, I, B) | Formulación del sistema completo en el reporte |
| Pruebas múltiples | `selection_table.csv` con el total de grupos evaluados |

## 6. Decisiones que la clase deja abiertas (→ `docs/decisiones.md`)

- Prioridad entre abrir / cerrar / stop y regla de reentrada tras un stop.
- Términos deterministas del ADF (constante, tendencia) y número de rezagos p (criterio de información).
- Si el holding máximo es k · vida media, cuál k.
- Si se requiere comprobar que cada serie es I(1) antes de cointegrar.

## 7. Preguntas tipo quiz / exposición

- Definan estacionariedad débil. ¿Por qué los precios no son estacionarios y los retornos sí?
- ¿Qué es una regresión espuria y cómo se detecta?
- ¿Por qué la correlación no basta para pairs trading?
- ¿Qué significa que β̂ sea superconsistente?
- ¿Por qué "no rechazar H₀" en ADF no significa aceptar la raíz unitaria?
- Calculen la vida media dado λ. ¿Para qué la usan?
- ¿Por qué los estadísticos del z-score usan información solo hasta t−1?
- ¿Qué son R_t, I_t y B_t en una estrategia de pares? ¿Por qué μ̂_t es creencia y no información?
- Con m = 20 activos, ¿cuántos falsos positivos esperan al 5 %?
