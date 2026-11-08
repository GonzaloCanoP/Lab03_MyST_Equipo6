# Post-mortem — Lab03 Equipo 6

> 1–2 páginas. Se evalúa honestidad y profundidad, no que todo saliera bien.
> Redactado el 2026-11-07 por JME para revisión de GC.

## Hitos cumplidos a tiempo y retrasados (y por qué)

| Hito (charter) | Objetivo | Real | Comentario |
|---|---|---|---|
| Plan, división del trabajo y universos | 11-04 | 11-04 | — |
| Pipeline de datos (split congelado, snapshot) | 11-04 | 11-04 | — |
| Cointegración (grupo elegido) | 11-05 | 11-04 | adelantado; **rehecho el 11-05** en la iteración 2 |
| Filtro 1 validado | 11-05 | 11-04 | adelantado |
| Filtro 2 + VECM + señales | 11-06 | 11-04 | adelantado |
| Backtest de punta a punta | 11-06 | 11-04 | adelantado |
| Métricas, figuras 1–8, pruebas en verde | 11-07 | 11-07 | a tiempo (61 pruebas) |
| Dashboard | 11-07 | 11-07 | a tiempo |
| Reporte PDF y revisión desde clon limpio | 11-08 | 11-07 | adelantado; el clon limpio reproduce todo byte a byte |

El pipeline completo corrió el 11-04, dos días antes de lo previsto, porque se trabajó en paralelo contra un
contrato de artefactos fijo (`CLAUDE.md`): cada parte sabía qué columnas recibía y entregaba. Ese adelanto fue lo que
permitió absorber la iteración 2 sin mover la entrega.

## Cuellos de botella técnicos

1. **La cointegración del primer grupo no se sostuvo.** GLD-GDX-AEM-FNV pasó todas las etapas en train, pero en
   validación su spread estático estuvo en promedio a ≈ 10 desviaciones de train (máximo ≈ 15) y el Sharpe neto bajó
   a 0.33 / 0.39. Se hicieron cuatro análisis fuera del pipeline antes de cambiar nada (prueba anidada, hiperparámetros,
   recalibración periódica y un solo sector) y la conclusión fue que el problema era la estabilidad del vector, no
   el ajuste. Costó un día (11-05) rehacer selección, notebooks, guías y Powell con la tercia GLD-GDX-B.
2. **El filtro 2 de clase no servía tal cual.** El nivel local o persigue al ECT (z sin señal) o deja innovaciones
   autocorrelacionadas; se pasó a un estado aumentado (media lenta + AR(1)), que hubo que justificar y revalidar.
3. **Q del filtro 1 no se puede calibrar por máxima verosimilitud** sin que el ECT revierta por construcción; se
   usó separación de escalas. Calibrar Q y R fue más trabajo que programar el filtro.
4. **Costos.** Con rebalanceo diario las comisiones se llevan ≈ 24 % del P&L bruto en train; eso obligó a comparar
   contra bandas de no-rebalanceo y a no mezclar esa elección con prueba y validación.

## Cuellos de botella organizacionales

- **Dependencia en serie entre partes** (02 → 03 → 04 → 05 → 06). Se mitigó con el contrato de artefactos y
  artefactos de ejemplo, pero la iteración 2 obligó a tocar notebooks y guías del otro integrante; se hizo con su
  autorización y quedó registrado.
- **Revisiones cruzadas.** Cada parte la revisó el otro integrante antes de seguir (registradas en
  `docs/decisiones.md`); detectaron detalles reales (det_order, regla con stop plano, estilo del dashboard).
- **Balance de commits.** Al 2026-11-07: 34 (JME) y 30 (GC) commits de trabajo, más 3 merges de PR de GC.

## Qué haríamos distinto en producción real

1. **Fijar desde el inicio una regla de selección que use solo train** (por ejemplo, exigir estabilidad en una
   prueba anidada) y no cambiarla después de ver prueba y validación. La iteración 2 fue válida y autorizada, pero
   su resultado lleva un sesgo de selección: GLD-GDX-B fue el mejor de 19 sobrevivientes fuera de muestra (mediana
   0.21) y su Sharpe deflactado (N = 19) es ≈ 0.46.
2. **Contar todas las alternativas probadas** (280 grupos, 10 configuraciones de hiperparámetros) para deflactar el
   Sharpe en el reporte desde el diseño.
3. **Monitoreo y regla de apagado** antes de operar (ver abajo), con un periodo de papel antes de usar capital.
4. **Costos realistas:** slippage e impacto además de la comisión, y la banda de no-rebalanceo dentro del grid desde
   el principio.

### Regla de monitoreo y apagado (qué hacer cuando la relación se rompe)

| Nivel | Disparo (umbrales de train) | Acción |
|---|---|---|
| 1. Alerta | media de 63 días del ECT estático fuera de ±2.2 desviaciones de train (percentil 99 de train) | revisar; el filtro 1 sigue absorbiendo la deriva |
| 2. Pausa | \|z\| > z_stop más de 11 días seguidos (racha máxima de train) o dos stops en seis meses | no abrir operaciones nuevas; dejar cerrar las abiertas |
| 3. Apagado | drawdown peor que 1.5 × MDD de train (−9.8 %), o el embudo con ventana creciente sin vector con vida media en [5, 60] días tres meses seguidos | cerrar todo; repetir la selección solo con datos anteriores a esa fecha |

Aplicada a la historia, con GLD-GDX-B la alerta se habría encendido en prueba y validación (la media de 63 días llegó a
2.65 y 2.73 desviaciones; el ECT estático promedió −1.6 desviaciones en 2022–2023 y −2.2 en 2024), pero ni la pausa
ni el apagado: fuera de muestra nunca hubo un día con |z| > 2.5 y el MDD fue −4.5 % / −3.7 %. Con GLD-GDX-AEM-FNV la
pausa se habría activado en validación (77 días seguidos con |z| > 2). El Johansen móvil de 2 años no sirve como
disparo: con la tercia rechaza r = 0 solo en 14 % de las ventanas de train. Los umbrales son una propuesta y no
se optimizaron ni se probaron dentro del backtest.

## Riesgos del registro: ¿se materializaron?

| # | Riesgo | ¿Se materializó? | Qué pasó |
|---|---|---|---|
| 1 | Pérdida de cointegración fuera de muestra | **Sí** | iteración 1 rota en validación; la tercia se debilita (ADF del ECT estático p = 0.27 en prueba) sin romperse; mitigado con el filtro 1, stop y holding |
| 2 | Divergencia del filtro | No | pesos estables; en prueba / validación la varianza de innovaciones del filtro 2 baja a 0.51 / 0.58 (filtro conservador) |
| 3 | Datos o caída de yfinance | No | snapshot versionado; nunca se volvió a descargar |
| 4 | Sesgo de pruebas múltiples | **Sí, en parte** | 280 grupos y 2 iteraciones; reportado con conteos, falsos positivos esperados y Sharpe deflactado |
| 5 | Look-ahead | No | z y ECT prior, ejecución en t + 1, fechas congeladas; prueba de causalidad en verde |
| 6 | Ticker reasignado | **Sí** | `GOLD` ya no es Barrick; se usó `B` |
| 7 | Cointegración de un solo episodio | **Sí** | las petroleras dependían de 2020; no pasaron la correlación |
| 8 | Tiempo insuficiente | No | el adelanto del 11-04 absorbió la iteración 2 |
| 9 | Commits desbalanceados | No | 34 / 30 commits de trabajo |
