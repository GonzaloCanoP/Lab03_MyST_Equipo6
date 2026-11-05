# Lab03_MyST_Equipo6 — Arbitraje Estadístico con Cointegración y Filtros de Kalman

Microestructuras y Sistemas de Trading · ITESO

## Integrantes

- Gonzalo Cano
- Juan Manuel Espinosa

## Nivel de alcance

Lab03 completo **sin la sección 3.7 Risk Parity** (indicación del profesor). Un solo grupo cointegrado: la tercia
**GLD-GDX-B** (oro, ETF de mineras y Barrick), elegida en la segunda iteración de la selección (ver `docs/decisiones.md`).

## Descripción

_TODO: 1 párrafo — universo, grupo seleccionado, Johansen → filtro de Kalman 1 (pesos) → filtro de Kalman 2
(z-score) → VECM → backtest con costos. Resultados clave en validación._

## Instalación

Requiere **Python 3.12**.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Notebooks de demostración

Un notebook por parte en `notebooks/` (solo importan funciones de los módulos; el pipeline evaluado es `main.py`):

```bash
jupyter notebook notebooks/
```

## Reproducción

```bash
python main.py
```

**Semilla aleatoria:** `SEED = 42`, fijada en `main.py` y aplicada con `np.random.seed(SEED)` al inicio del
pipeline; toda función con aleatoriedad la recibe como argumento, por lo que cada corrida produce los mismos resultados.

## Pruebas

```bash
pytest
```

## Dashboard — guía de uso

```bash
streamlit run dashboard/app.py
```

_TODO: guía de una página (vista ejecutiva vs vista técnica, filtros, cómo leer cada gráfica)._

## Uso de asistencia de IA

_TODO: qué partes del proyecto usaron asistencia de IA y cómo se verificó._
