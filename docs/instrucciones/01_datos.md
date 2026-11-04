# 01 — Datos: ingesta, limpieza, validación y split

**Dueño:** Juan Manuel Espinosa (JME) · **Revisor:** Gonzalo Cano (GC) · **Notebook:** `notebooks/01_datos.ipynb` · **Carpeta:** `data/` · **Depende de:** — · **Alimenta a:** 02, 03, 06
**Leer antes:** `docs/notas_clase/02_pairs_trading_secuencial.md` (sección de datos, si la hay)

## Objetivo

Descargar 10–15 años de precios diarios del universo candidato, limpiarlos, validarlos y partirlos
cronológicamente 60/20/20 sin look-ahead.

## Parámetros de este módulo

`SPLIT = (0.60, 0.20, 0.20)`, `N_ASSETS = 4` en `data/split.py`. `MAX_FFILL = 3` en `data/clean.py`, `JUMP_THRESHOLD = 0.40` en `data/validate.py`. Recibe `START_DATE`, `END_DATE`, `DATA_SNAPSHOT` desde `main.py`. Si cambian, actualizar la tabla de parámetros de `CLAUDE.md`.

## Contrato

- **Lee:** `START_DATE`, `END_DATE` (argumentos desde `main.py`), lista de tickers del universo (de `cointegration/universe.py`).
- **Escribe:** `data/snapshot/prices_raw.parquet` (snapshot versionado), `artifacts/split_dates.json`, `artifacts/validation_report.json`, `artifacts/prices.parquet` (solo los 4 activos finales, columna `split`; se escribe cuando 02 elija el grupo).
- **Expone:** `load_prices(tickers) -> DataFrame`, `split_data(df) -> (train, test, validation)`, `split_dates() -> dict`.

## Loop de trabajo

```
REPETIR hasta cumplir el criterio de terminado:
  1. Toma el primer ítem sin [x] del checklist.
  2. Impleméntalo en data/ con docstring.
  3. Verifica: corre la función, inspecciona shape, fechas, NaN; agrega/ajusta una prueba si aplica.
  4. Marca [x], anota decisiones en docs/decisiones.md, commit.
```

## Checklist

- [ ] Descarga con `yfinance` usando precios **ajustados** (splits y dividendos), con snapshot local versionado en `data/snapshot/`.
- [ ] Ventana de 10–15 años; fechas fijas en `main.py` (no "hoy") para reproducibilidad.
- [ ] Alinear calendarios entre activos (intersección de fechas hábiles).
- [ ] Manejo de faltantes documentado (forward-fill limitado o eliminar fechas) — nunca back-fill.
- [ ] Validación: sin NaN, precios > 0, sin duplicados, índice ordenado, detección de saltos anómalos.
- [ ] Reporte de validación (filas, rango de fechas, faltantes tratados) impreso por `main.py`.
- [ ] Split cronológico 60/20/20 → entrenamiento / prueba / validación; fechas de corte guardadas.
- [ ] La partición se define **antes** de cualquier estimación y todas las partes la importan de aquí.
- [ ] `artifacts/prices.parquet` con columna `split`.
- [ ] Figura 1: series de precios individuales de los activos del grupo (normalizadas a 100 opcional).

## Criterio de terminado

`python -c "from data import ...; ..."` devuelve las tres particiones sin NaN, las fechas de corte están en
`data/split.py`/artefacto y la figura 1 existe en `docs/figuras/`.

## Trampas

- Usar precios no ajustados → splits parecen rupturas de cointegración.
- Rellenar hacia atrás (bfill) = look-ahead.
- Tickers que cambian de nombre o se deslistan dentro de la ventana (sesgo de supervivencia: mencionarlo en limitaciones).

## Preguntas probables

- ¿Por qué precios ajustados? ¿Cómo trataron días faltantes? ¿Qué sesgo de supervivencia tiene su universo?
