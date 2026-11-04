# Bitácora de decisiones de modelado

Registrar aquí toda decisión que no venga fijada por el enunciado o las notas de clase.
Sirve para el reporte y para responder "¿por qué hicieron X?" en la exposición.

| Fecha | Parte | Decisión | Alternativa descartada | Justificación | Autor |
|---|---|---|---|---|---|
| 2026-10-31 | Alcance | Se omite 3.7 Risk Parity (y figura 9 / prueba 4 Nivel B) | Implementarla | Indicación del profesor | Equipo |
| 2026-10-31 | Datos | Grupo de 4 activos | 2–8 activos | 2 · n integrantes (n = 2), regla del enunciado | Equipo |
| 2026-11-02 | VECM / KF2 | Los "residuales del VECM" (§3.6) son el **término de corrección de error** ECT_t = β̂_tᵀP_t − ĉ_t que produce el filtro 1 día a día; esa serie es la que normaliza el filtro 2 para obtener z_t. El VECM (en train) aporta α, la condición −2 < βᵀα < 0 y la vida media | Residual ε_t de la ecuación del VECM (ΔP_t − ajustado); ECT estático con β de Johansen como señal principal | Respuesta del profesor (WhatsApp, 2026-11-02): "El residual de la relación de equilibrio, es el término de corrección de error del VECM, que el Filtro 1 produce día a día. No es residual como tal en términos de diferencia, si no la corrección que se aplica" | Profesor / JME |
| 2026-11-02 | Análisis | Comparar el ECT **estático** (βᵀP_t − c con β de Johansen congelado en train) contra el **dinámico** del filtro 1: gráfica de ambos, ADF y vida media de cada uno y, si da tiempo, backtest de ambos | Reportar solo el dinámico | Sugerencia del profesor ("Puedes comparar la estática con la dinámica del Filtro 1"); suma al criterio C (comparar escenarios) | Profesor / JME |
| 2026-11-04 | KF1 | El ECT de t se calcula con los pesos **prior** β̂_{t\|t−1} (equivale a la innovación ỹ_t del filtro 1) | Pesos posterior β̂_{t\|t}: ya absorbieron P_t y encogen el ECT hacia cero por el factor R/S_t | Causalidad; misma lógica que el z prior que exige §3.4 | Equipo |
