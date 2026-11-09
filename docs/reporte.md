# Arbitraje estadístico multiactivo con cointegración y filtros de Kalman

**Lab03 · Microestructuras y Sistemas de Trading · ITESO** — Equipo 6: Gonzalo Cano y Juan Manuel Espinosa ·
noviembre de 2026

Fuente de cada cifra: `artifacts/` (lo genera `python main.py`) y `docs/decisiones.md`. Alcance: Lab03 completo sin
la sección 3.7 (Risk Parity), por indicación del profesor.

## Resumen ejecutivo

- **Grupo:** la tercia **GLD-GDX-B** (ETF de oro, ETF de mineras de oro y Barrick), cointegrada en entrenamiento
  (traza 35.8 contra 29.8 al 95 %, rango 1, vida media del spread 29 días).
- **Modelo:** Johansen da el vector inicial; el **filtro de Kalman 1** deja que los pesos deriven despacio; el
  **filtro de Kalman 2** convierte el término de corrección de error (ECT) en un z-score con estadísticos *prior*; una
  regla de bandas con stop y holding máximo decide la dirección; el backtest cobra comisión por pata y préstamo de
  cortos.
- **Resultado (θ congelado desde train, walk-forward):** Sharpe neto **0.66 / 0.74 / 1.01** en entrenamiento /
  prueba / validación, rendimiento +20.5 % / +8.1 % / +11.2 %, drawdown máximo −6.6 % / −4.5 % / −3.7 %. Total
  encadenado 2013–2026: +44.8 %, Sharpe 0.75. Los costos se llevan 21–25 % del P&L bruto.
- **Lectura honesta:** la relación **se debilita sin romperse** fuera de muestra y el filtro 1 absorbe la deriva.
  El grupo se eligió en una segunda iteración, después de que el primero (GLD-GDX-AEM-FNV) perdiera la cointegración
  en validación; corrigiendo por los 19 grupos candidatos, el Sharpe deja de ser estadísticamente concluyente
  (Sharpe deflactado ≈ 0.46). La relación tiene fundamento económico, pero la evidencia de que sea explotable es
  moderada.

## 1. Universo, justificación económica y pruebas múltiples

**Datos.** Precios ajustados diarios de Yahoo Finance del 2012-01-03 al 2026-10-30 (≈ 14.8 años), guardados en un
snapshot versionado (`data/snapshot/`) para que la corrida no dependa de la descarga. Partición 60/20/20 por fecha,
calculada una vez y congelada: **entrenamiento** 2012-01-03 → 2020-11-19, **prueba** 2020-11-20 → 2023-11-08,
**validación** 2023-11-09 → 2026-10-30. Forward-fill de máximo 3 días y nunca back-fill.

**Universos con justificación económica (criterio fijado antes de correr).**

- *Iteración 1:* petroleras de EE. UU. y Europa (126 cuartetos) y oro + mineras (70 cuartetos), grupos de 4 = 2 ×
  integrantes. Resultado: GLD-GDX-AEM-FNV.
- *Iteración 2 (autorizada por el profesor):* solo oro + mineras (GLD, GDX, NEM, AEM, KGC, B, AU, FNV), con pares,
  tercias y cuartetos: 154 grupos. Resultado: **GLD-GDX-B**. El metal, el ETF de mineras y una de sus posiciones más
  grandes comparten la tendencia casi de forma mecánica: las mineras son una opción apalancada sobre el precio del
  oro y GDX es una canasta de ellas. AEM y FNV (regalías) tienen dinámicas propias que pueden separarse del oro por años.

**Pruebas múltiples.** En total se probaron **280 grupos distintos**. En la iteración 2, Johansen rechaza r = 0 al
95 % en 30 de 154 grupos cuando por azar se esperarían 7.7; solo 4 rechazan al 99 % y la corrección de Bonferroni
exigiría α = 0.00032.
Por eso el embudo no se queda en Johansen: exige correlación, un vector con ADF significativo y una vida media
operable, y el reporte declara el sesgo de selección (sección 9).

## 2. Embudo de selección (iteración 2)

| Etapa (eliminatoria) | Criterio | Grupos que siguen |
|---|---|---|
| Universo | pares, tercias y cuartetos de 8 tickers | 154 |
| 2. Correlación | media de correlaciones móviles (252 días) > 0.7 | 136 (18 fuera) |
| 3. Engle–Granger | prioriza, no elimina (6 pares, regresión del grupo, bandera de regresión espuria) | 136 |
| 4. Johansen (traza 95 %) | rechaza r = 0 | 28 (108 fuera) |
| 6. Vector operable | ADF del spread p < 0.05 y vida media en [5, 60] días | **19** (9 fuera) |
| 7. Estabilidad | Johansen en cada mitad de train y móvil: se reporta, no elimina | 19 |

Entre los 19, la regla de la iteración 1 (máxima razón traza / crítico) elegiría KGC-B (1.33); GLD-GDX-B es el 4.º
(1.20). La tabla completa, con la etapa y el motivo de descarte de cada grupo, está en `artifacts/selection_table.csv`.

## 3. Johansen: rango, vector, ADF y vida media

Todas las series son I(1) (ADF en niveles p = 0.69 / 0.19 / 0.20, en diferencias p ≈ 0). Johansen con constante sin
restringir (`det_order = 0`), k_ar_diff = 1 elegido por BIC, 2 237 observaciones de train:

| H₀ | Traza | Crítico 95 % | Máx. eigenvalor | Crítico 95 % | Decisión |
|---|---|---|---|---|---|
| r = 0 | 35.82 | 29.80 | 27.54 | 21.13 | rechaza (traza también al 99 %: 35.46) |
| r ≤ 1 | 8.28 | 15.49 | 7.19 | 14.26 | no rechaza |
| r ≤ 2 | 1.09 | 3.84 | 1.09 | 3.84 | no rechaza |

Rango 1 por traza y por máximo eigenvalor (eigenvalores 0.0122, 0.0032 y 0.0005): solo el primer vector es
estacionario, así que no hay otro con qué competir. **Normalización** sobre la pata de mayor |peso| (GDX = +1):

> ECT_t = ln GDX_t − 0.827 ln GLD_t − 0.448 ln B_t − c, con c = −2.066 (media en train).

**Convención de signo:** largo el spread = comprar los activos con β̃ > 0 (GDX) y vender los de β̃ < 0 (GLD y B).
ADF del spread p = 0.0009; vida media −ln 2 / λ = **29.1 días**. El Johansen móvil de 2 años (figura 4) rechaza
r = 0 solo en 14 % de las ventanas de train: con ventanas cortas tiene poca potencia, y los pesos se mueven aun
dentro de train. Ese es el argumento para el filtro 1.

![Figura 1. Precios normalizados del grupo.](figuras/fig01_precios_grupo.png)

![Figura 4. Primer eigenvector de Johansen móvil y razón traza / crítico.](figuras/fig04_eigenvector_movil.png)

## 4. Formulación como proceso de decisión secuencial (Powell)

La formulación completa (6 pasos y 5 elementos de cada filtro y del sistema) está en `docs/powell.md`. Resumen:

| | Filtro 1 (pesos) | Filtro 2 (z-score) | Sistema completo |
|---|---|---|---|
| Estado | creencia (ĉ, β̂_GLD, β̂_B), P_t | creencia (μ̂, x̂), P_t | físico: acciones, efectivo, d_{t−1}, h_t, rearme · información: P_t, ECT_t, z_t · creencia: la de ambos filtros |
| Transición | caminata aleatoria, Q = q·I | μ caminata aleatoria, x AR(1) con φ | filtros + ejecución en t + 1 con costos |
| Observación | ln GDX_t = (1, −ln GLD_t, −ln B_t) z_t + v_t | ECT_t = μ_t + x_t + v_t | solo precios P_{t+1} (W_{t+1}) |
| Política | regla de Kalman (PFA, θ = Q, R) | regla de Kalman (PFA, θ = φ, q_μ, q_x, r) | regla de bandas (PFA, θ = z_entrada, z_salida, z_stop, h_max) + sizing |
| Objetivo | error de predicción con deriva lenta | verosimilitud de innovaciones con media lenta | máx. Sharpe neto en train |

**Ganancia de Kalman.** En el filtro 1, C_t K_t = 1 − R/S_t es la fracción de la sorpresa del día que se absorbe
moviendo pesos: mediana 0.0038 en train (0.4 %). En el filtro 2 converge a K^μ ≈ 0.08 y K^x ≈ 0.74: casi toda
sorpresa va a la desviación que revierte y muy poca a la media (figura 5).

## 5. Calibración: Q, R, inicialización, burn-in, normalización y signo

**Filtro 1.**

- R = 3.31 × 10⁻³, la varianza del residual de Johansen en train.
- q = 1.6 × 10⁻⁹ (q/R ≈ 4.8 × 10⁻⁷) por **separación de escalas**: es el mayor q con el que el filtro absorbe a lo
  más 20 % de una desviación en 2 vidas medias (58 días).
- Por qué no máxima verosimilitud: elige un q mucho mayor, y entonces el ECT revierte por el filtro y no por los
  precios.
- P₀ = 252·Q. El estado arranca en el β̃ de Johansen. Burn-in de 252 días (2012).
- El ECT de t se calcula con los pesos **prior** β̂_{t|t−1}: es la innovación del filtro y no está encogida por la
  actualización del día.

**Filtro 2.**

- φ = 0.969 (vida media 22.1 días, AR(1)/OU del ECT en train).
- q_x = 1.1 × 10⁻⁴ y r = 2.8 × 10⁻⁵ por máxima verosimilitud.
- q_μ = 9.3 × 10⁻⁷ por el mismo criterio de separación de escalas que el filtro 1.
- μ̂₀ = x̂₀ = 0, P₀ = diag(q_x/(1−φ²)); burn-in de 63 días.
- `z_t = (ECT_t − μ̂_{t|t−1}) / σ̂_{t|t−1}`, con σ̂² = q_x/(1−φ²) + p^μ + r, todo **prior**.
- Prueba 4 en train: varianza de ν/√S = 0.995 y Ljung–Box del rezago 1 con p = 0.62.

**Normalización y signo:** ancla GDX = +1 en Johansen, en el estado del filtro 1 (GDX no es estado: es la variable
observada) y en el sizing (N_i ∝ |β̂_i| con el signo de β̂_i).

![Figura 3. Pesos dinámicos β̂_t del filtro 1 contra el β̃ estático de Johansen.](figuras/fig03_pesos_dinamicos.png)

![Figura 5. Ganancia de Kalman de ambos filtros.](figuras/fig05_ganancia_kalman.png)

## 6. VECM: α y su interpretación

VECM en train con constante sin restringir, rango 1 y k_ar_diff = 1; su β coincide con el de Johansen.

| | GLD | GDX | B |
|---|---|---|---|
| α | −0.003 | **−0.039** | **−0.034** |
| t | −0.9 | −4.1 | −3.4 |

βᵀα = −0.021 cumple −2 < βᵀα < 0 (la relación corrige), con vida media de 33.3 días. Solo GDX corrige: su
contribución β_GDX·α_GDX = −0.039 cierra el spread, mientras que la de Barrick (β_B·α_B = +0.015) lo abre. Cuando
el ETF de mineras se encarece frente al oro y a Barrick, es el ETF el que regresa; el oro casi no participa en el
ajuste. Las tres vidas medias (Johansen 29.1, VECM 33.3, filtro 2 22.1 días) coinciden en orden de magnitud.

## 7. Umbrales y procedimiento de búsqueda

**Regla (PFA).**

- Plano: largo si −z_stop < z_t < −z_entrada; corto si z_entrada < z_t < z_stop.
- Con posición, cierra con esta prioridad: stop (|z_t| ≥ z_stop) > holding (h_t ≥ h_max) > salida direccional.
- Tras un stop o un holding, esa dirección se rearma solo cuando |z_t| < z_entrada.
- Se ejecuta al cierre de t + 1 con N_i = 0.8 V_t |β̂_i| / Σ|β̂_j|.

**Búsqueda.** El grid se registró en `docs/decisiones.md` antes de ver resultados:

- z_entrada ∈ {1, 1.25, 1.5, 1.75, 2, 2.5}, z_salida ∈ {0, 0.25, 0.5}, z_stop ∈ {2.5, 3, 3.5, 4} y
  h_max = k · 29 días con k ∈ {1, 2, 3}.
- Hay 207 combinaciones válidas (z_salida < z_entrada < z_stop); 135 tienen al menos 10 operaciones.
- Objetivo: Sharpe neto anualizado en train, con la simulación completa y los costos.
- Resultado: **θ = (1.0, 0.0, 2.5, 87 días)**, con Sharpe 0.66 y 24 operaciones en train.
- El 83 % de las combinaciones tiene Sharpe positivo en train, y las 5 mejores comparten z_entrada = 1 y z_salida = 0.
- Limitación: el óptimo está en el borde de la rejilla, que no se amplió, y el Sharpe deflactado del grid en train
  es 0.59.
- Fuera de muestra, ese θ es el 13.º de 135 en prueba y el 1.º en validación. La correlación de Spearman entre el
  Sharpe de train y el de fuera de muestra es 0.49 (prueba) y 0.43 (validación).

![Figura 6. z-score prior con los umbrales elegidos.](figuras/fig06_zscore_umbrales.png)

![Superficie del grid search en train.](figuras/grid_search_heatmap.png)

## 8. Resultados por partición, costos y rebalanceo

| Métrica | Entrenamiento | Prueba | Validación | Total (encadenado) |
|---|---|---|---|---|
| Periodo | 2013-04 → 2020-11 | 2020-11 → 2023-11 | 2023-11 → 2026-10 | 2013-04 → 2026-10 |
| Rendimiento neto | +20.5 % | +8.1 % | +11.2 % | +44.8 % |
| CAGR | 2.5 % | 2.7 % | 3.7 % | 2.8 % |
| Sharpe neto | 0.66 | 0.74 | 1.01 | 0.75 |
| Sortino | 1.01 | 1.12 | 1.61 | 1.16 |
| Calmar | 0.38 | 0.59 | 0.98 | 0.42 |
| Max drawdown | −6.6 % | −4.5 % | −3.7 % | −6.6 % |
| Racha más larga bajo el máximo (días hábiles) | 1 185 | 244 | 171 | 1 185 |
| Operaciones / ganadoras | 24 / 79 % | 9 / 89 % | 11 / 91 % | 44 / 84 % |
| Profit factor | 2.49 | 4.55 | 8.11 | 3.26 |

Cada partición arranca con $1,000,000 y el CAGR es bajo porque solo 80 % del capital está invertido y la estrategia
está en el mercado menos de la mitad de los días. En las tres particiones suman $522,687 de P&L bruto, $118,744 de
comisiones y $6,067 de préstamo, para $397,876 netos: los costos son el 24 % del bruto. Por año, 13 de 14 años son
positivos; el único negativo es 2016 (−5.3 %).

**Rebalanceo diario contra banda de no-rebalanceo** (θ fijo; la política oficial es el diario, con el que se eligió θ):

| Banda | Sharpe train | Sharpe prueba | Sharpe validación | Rebalanceos train | Comisiones train |
|---|---|---|---|---|---|
| diario (0) | 0.66 | 0.74 | 1.01 | 697 | $66,527 |
| 5 % | 0.69 | 0.72 | 0.99 | 146 | $59,671 |
| 10 % | 0.66 | 0.83 | 1.07 | 45 | $56,077 |
| 20 % | 0.66 | 0.82 | 1.12 | 9 | $54,579 |

En train la banda casi no cambia el Sharpe, pero ahorra hasta 18 % de comisiones. Elegir la banda de 20 % por lo que
pasa en prueba y validación sería ajustar con esos datos, así que se reporta como escenario.

**Estático contra dinámico** (mismo θ): con el ECT estático de Johansen el Sharpe es 0.72 / 0.20 / 1.31; con el
dinámico, 0.66 / 0.74 / 1.01. El estático se cae en prueba, donde su ECT deja de ser estacionario (ADF p = 0.27).
El dinámico es más consistente entre particiones porque absorbe la deriva de nivel de la relación.

![Figura 2. Spread con las señales de entrada y salida.](figuras/fig02_spread_senales.png)

![Figura 7. Curvas de capital por partición.](figuras/fig07_curvas_capital.png)

![Figura 8. Distribución de rendimientos por operación con la normal superpuesta.](figuras/fig08_distribucion_operaciones.png)

La distribución por operación tiene sesgo −1.38 y curtosis 4.66 (Jarque–Bera p = 7.6 × 10⁻⁵): muchas ganancias
pequeñas por reversión y pocas pérdidas grandes por stop y holding. Ninguna operación cerrada por reversión perdió.

![Sharpe neto móvil de 252 días.](figuras/sharpe_movil.png)

![ECT estático contra dinámico.](figuras/ect_estatico_vs_dinamico.png)

## 9. ¿Relación estructural o artefacto?

**Argumentos a favor de una relación estructural.**

1. **Mecanismo económico directo:** GDX es una canasta de mineras de oro y Barrick está entre sus mayores
   posiciones; las tres series dependen del precio del oro.
2. **El VECM confirma la corrección de error** (βᵀα = −0.021), con el ajuste en el activo esperado (GDX).
3. **Fuera de muestra la relación se debilita pero no se rompe.** El ECT estático se desplaza en promedio
   1.2 / 1.9 desviaciones de train en prueba / validación, contra ≈ 10 del grupo de la iteración 1. El dinámico se
   mantiene centrado (media −0.02 / +0.003; ADF p = 0.055 / 0.011).
4. **La estrategia gana en todos los años fuera de muestra.** Tiene 18 de 20 operaciones ganadoras y +$122 mil aun
   sin sus 3 mejores operaciones. No toca el stop fuera de muestra.

**Argumentos a favor de que parte del resultado es artefacto.**

1. **Pruebas múltiples:** 30 de 154 grupos rechazan r = 0 cuando se esperaban 7.7 por azar, y solo 4 rechazan al
   99 % (Bonferroni exigiría α = 0.00032).
2. **Sesgo de selección:** la tercia se eligió en una segunda iteración, con lo aprendido de prueba y validación.
   Con el mismo pipeline, los 19 sobrevivientes tienen una mediana de Sharpe fuera de muestra de 0.21. GLD-GDX-B es
   el 1.º de 19, y la correlación entre el Sharpe de train y el de fuera de muestra a través de los grupos es −0.29.
   El **Sharpe deflactado** (N = 19) es ≈ 0.46.
3. **Inestabilidad:** el Johansen móvil rechaza poco (14 % de las ventanas de train), y en la prueba anidada
   (train partido 60/20/20) esta familia de grupos da Sharpe negativo en 2017–2020.
4. **Sensibilidad:** con tolerancias de los filtros de 10 % o 40 % en lugar de 20 %, el Sharpe fuera de muestra
   baja a 0.17–0.69 contra 0.87. Los hiperparámetros de la optimización, en cambio, son robustos.

**Conclusión.** La relación GLD-GDX-B es **estructural en su origen pero inestable en sus pesos**: existe un vector
que corrige, con fundamento económico, cuyo nivel y pesos derivan con los años. La estrategia funciona porque el
filtro 1 sigue esa deriva. Que este grupo en particular sea el mejor y que el Sharpe fuera de muestra sea ≈ 0.9 no
es estadísticamente concluyente después de corregir por la búsqueda. En operación real se usaría con la regla de
monitoreo y apagado del post-mortem (`project_management/postmortem.md`).

## 10. Supuestos y limitaciones

- **Supuestos de mercado:**
    - Se opera al precio de cierre de t + 1 sin slippage ni impacto.
    - Comisión de 0.125 % por pata y préstamo de 0.25 % anual sobre el nocional corto, siempre disponible.
    - El efectivo no rinde intereses (r_f = 0).
- **Datos:**
    - Precios ajustados de Yahoo.
    - Sesgo de supervivencia: solo se excluyen empresas adquiridas.
    - Universos elegidos por el equipo.
- **Modelo:**
    - Johansen supone una sola relación lineal en log-precios con constante.
    - Los filtros suponen ruido gaussiano.
    - Q, R, φ y θ están congelados desde train; no hay recalibración, porque la recalibración probada no mejoró
      fuera de muestra de forma consistente.
    - Fuera de muestra la varianza de las innovaciones del filtro 2 baja a 0.51 / 0.58: el filtro sobreestima el ruido
      y es conservador.
- **Estadística:**
    - Hay pocas operaciones (9 y 11 fuera de muestra), así que el Sharpe tiene mucho error.
    - Ljung–Box a 5–10 rezagos rechaza con cualquier modelo del filtro 2.
    - El grid tiene su óptimo en el borde.
- **Proceso:** dos iteraciones de selección. La segunda la autorizó el profesor y está documentada completa en
  `docs/decisiones.md`, incluidas las pruebas que no funcionaron (prueba anidada, hiperparámetros, recalibración y
  un solo sector).
- **Excluido del alcance:** Risk Parity entre grupos (sección 3.7), operación en vivo y datos intradía.
