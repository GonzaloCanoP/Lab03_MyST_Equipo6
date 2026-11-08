# 99 — Checklist final de entrega (contra la rúbrica)

Revisión desde clon limpio hecha el 2026-11-07 (JME): `main.py`, `pytest`, dashboard y los 7 notebooks sin errores.

Correr este loop el día anterior a la entrega, **antes** de las 23:59, desde un clon limpio del repo.

```
REPETIR hasta que todo esté en [x]:
  1. git clone <repo> /tmp/check && cd /tmp/check
  2. python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
  3. python main.py && pytest && streamlit run dashboard/app.py
  4. Revisar la lista; arreglar lo que falle en el repo real; commit; volver a 1.
```

## A. Estructura y reproducibilidad (10)

- [x] Repo público `Lab03_MyST_Equipo6` (se clonó sin credenciales).
- [x] Carpetas obligatorias: data, cointegration, kalman, strategy, backtest, performance, dashboard/app.py, project_management, artifacts, tests, docs/reporte.pdf.
- [x] `python main.py` corre sin errores desde un clon limpio (−10 si no): 1 min 23 s, sin descargas, artefactos y figuras idénticos byte a byte.
- [x] `requirements.txt` con versiones fijadas (instala en un entorno nuevo de Python 3.12).
- [x] Semilla fijada y documentada (`SEED = 42`, README).
- [ ] README: integrantes, nivel de alcance, descripción, instalación, comando exacto, guía del dashboard, uso de IA. **Falta la parte de GC en "Uso de asistencia de IA"**; lo demás está.
- [x] Ambos integrantes con commits propios y balanceados; historial descriptivo (`git shortlog -sn --no-merges`: JME 34, GC 30).

## B. Lógica del modelo (10)

- [x] Johansen, KF1, KF2, VECM, señales, sizing implementados según la formulación (`docs/powell.md` con el nombre de la función junto a cada elemento).
- [x] Supuestos declarados explícitamente (reporte, sección 10).

## C. Resultados y análisis (10)

- [x] Figuras 1–8 presentes y correctas (`docs/figuras/`, regeneradas por `main.py`).
- [x] Análisis con cifras propias; comparación de escenarios (splits, rebalanceo vs banda, sensibilidad de umbrales).
- [x] Limitaciones declaradas (reporte, secciones 9 y 10).

## D. Código, pruebas, documentación (10)

- [x] 4 pruebas pasan con `pytest` (61 en total en el clon limpio, 52 s).
- [x] Docstrings en funciones principales; sin código muerto ni duplicado (revisión automática: todas las funciones públicas con docstring y ninguna definida sin usar; la duplicación se revisó en las revisiones cruzadas).
- [ ] Uso de IA declarado (falta la parte de GC en el README).

## Penalizaciones a evitar

- [ ] Último commit antes de las 23:59 del día previo.
- [x] `docs/reporte.pdf` y dashboard en el repo antes de la exposición.
