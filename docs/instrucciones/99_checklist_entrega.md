# 99 — Checklist final de entrega (contra la rúbrica)

Correr este loop el día anterior a la entrega, **antes** de las 23:59, desde un clon limpio del repo.

```
REPETIR hasta que todo esté en [x]:
  1. git clone <repo> /tmp/check && cd /tmp/check
  2. python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
  3. python main.py && pytest && streamlit run dashboard/app.py
  4. Revisar la lista; arreglar lo que falle en el repo real; commit; volver a 1.
```

## A. Estructura y reproducibilidad (10)

- [ ] Repo público `Lab03_MyST_Equipo6`.
- [ ] Carpetas obligatorias: data, cointegration, kalman, strategy, backtest, performance, dashboard/app.py, project_management, artifacts, tests, docs/reporte.pdf.
- [ ] `python main.py` corre sin errores desde un clon limpio (−10 si no).
- [ ] `requirements.txt` con versiones fijadas.
- [ ] Semilla fijada y documentada.
- [ ] README: integrantes, nivel de alcance, descripción, instalación, comando exacto, guía del dashboard, uso de IA.
- [ ] Ambos integrantes con commits propios y balanceados; historial descriptivo.

## B. Lógica del modelo (10)

- [ ] Johansen, KF1, KF2, VECM, señales, sizing implementados según la formulación.
- [ ] Supuestos declarados explícitamente.

## C. Resultados y análisis (10)

- [ ] Figuras 1–8 presentes y correctas.
- [ ] Análisis con cifras propias; comparación de escenarios (splits, rebalanceo vs banda, sensibilidad de umbrales).
- [ ] Limitaciones declaradas.

## D. Código, pruebas, documentación (10)

- [ ] 4 pruebas pasan con `pytest`.
- [ ] Docstrings en funciones principales; sin código muerto ni duplicado.
- [ ] Uso de IA declarado.

## Penalizaciones a evitar

- [ ] Último commit antes de las 23:59 del día previo.
- [ ] `docs/reporte.pdf` y dashboard en el repo antes de la exposición.
