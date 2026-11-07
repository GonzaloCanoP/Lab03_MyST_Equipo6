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

Requiere los artefactos de `artifacts/` (ya versionados; si faltan, el dashboard lo indica y basta con correr
`python main.py`). El dashboard **no recalcula nada**: solo lee esos archivos.

**Navegación (estilo terminal financiera).**
- **Barra de comando** arriba: grupo (GLD-GDX-B) y fecha de los datos.
- **Partición** (`TODO`, `TRAIN`, `TEST`, `VALID`) y **rango de fechas**: aplican a todas las gráficas. El fondo
  sombreado marca la partición: azul = entrenamiento, ámbar = prueba, verde = validación.
- **Teclas de función** `F1 EJECUTIVA` y `F2 TÉCNICA` cambian de vista.
- Todas las gráficas son interactivas (Plotly): arrastrar para hacer zoom, doble clic para regresar, pasar el cursor
  para ver valores; en la leyenda, un clic oculta una serie.

**F1 — Vista ejecutiva (JME).** Qué tan bien le fue a la estrategia y cuánto costó. La cinta de arriba es la tarjeta
de la partición elegida (`TODO` = las tres encadenadas): rendimiento, CAGR, Sharpe, Sortino, Calmar, MDD, win rate,
profit factor y operaciones, leídos de `metrics.json`.

| Panel | Qué muestra | Cómo leerlo |
|---|---|---|
| 1) Curva de capital y drawdown | capital por partición (cada una arranca con $1,000,000, como la figura 7) o encadenado; abajo, la caída bajo el máximo previo | `ENCADENADA` es la curva del total de `metrics.json`; los tramos planos son días sin posición |
| 2) Métricas por partición | tabla de `metrics.json` para train, prueba, validación y total; la partición elegida va resaltada | métricas de la partición completa, no del ajuste fino de fechas |
| 3) Atribución de costos | cascada P&L bruto → comisiones → préstamo → P&L neto en el rango elegido | la nota da los costos como % del bruto |
| 4) Rendimiento por año | rendimiento neto compuesto de cada año calendario | el signo va en la etiqueta; el primer y el último año son parciales |
| 5) Bitácora de operaciones | operaciones que entran en el rango, filtrables por dirección, resultado y motivo de salida | rend. = P&L neto / capital antes de entrar; abajo, número de operaciones, % ganadoras, mejor y peor |
| 6) Distribución por operación | histograma de rendimientos por operación con la normal de misma media y desviación | sesgo, curtosis y Jarque–Bera en la nota; con todo el periodo coinciden con la figura 8 |

**F2 — Vista técnica (GC).** Cómo se construye la señal. La cinta de arriba resume el estado al final del rango:
z, posición (▲ largo / ▼ corto / ■ plano), β̂ actuales, θ y métricas totales.

| Panel | Qué muestra | Cómo leerlo |
|---|---|---|
| 1) Spread y señales | ECT dinámico (filtro 1), μ prior (filtro 2), entradas ▲▼ y salidas por motivo | las entradas ocurren lejos de μ; las salidas por reversión (●) cerca de μ; ✕ = stop, ■ = holding |
| 2) z-score y umbrales | z prior con las bandas de entrada, salida y stop congeladas desde train | fuera de la banda amarilla se entra; en la línea punteada se sale |
| 3) β̂_t por activo | pesos del filtro 1 (GDX = +1) contra el β̃ de Johansen (punteado) | una deriva lenta es la que absorbe el filtro; un salto indicaría ruptura |
| 4) Eigenvector de Johansen móvil | β̃ por ventana de 504 días y la razón traza / crítico | arriba de 1 la ventana rechaza r = 0; los saltos de β̃ aparecen cuando no hay cointegración |
| 5) Ganancia de Kalman | K_t del filtro 1 (c y pesos) y del filtro 2 (μ y x) | ganancias pequeñas = el filtro confía en su estado y se mueve despacio |
| 6) Varianza posterior | diagonal de P_t\|t de ambos filtros (escala log) | crece si el filtro se vuelve más incierto |
| 7) Sharpe móvil 252 días | Sharpe neto de un año contra el de cada partición completa | un año con un stop basta para volverlo negativo; en el primer año de prueba y de validación la ventana todavía incluye días de la partición anterior |

## Uso de asistencia de IA

_TODO: qué partes del proyecto usaron asistencia de IA y cómo se verificó._
