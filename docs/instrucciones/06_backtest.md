# 06 — Backtest multi-pata con costos y walk-forward

**Dueño:** Juan Manuel Espinosa (JME) · **Revisor:** Gonzalo Cano (GC) · **Notebook:** `notebooks/06_backtest.ipynb` · **Carpeta:** `backtest/` · **Depende de:** 05 · **Alimenta a:** 07, 08
**Leer antes:** `docs/notas_clase/02_pairs_trading_secuencial.md`

## Objetivo

Simular la estrategia día a día con contabilidad exacta por pata, comisiones, costo de préstamo en cortos y
evaluación walk-forward en train / test / validación.

## Parámetros de este módulo

`COMMISSION = 0.00125`, `BORROW_RATE_ANNUAL = 0.0025`, `TRADING_DAYS = 252` en `backtest/costs.py`. Si cambian, actualizar la tabla de parámetros de `CLAUDE.md`.

## Contrato

- **Lee:** precios, `signals.parquet`, `params.json`.
- **Escribe:** `equity_curve.parquet`, `trades.csv`, `rebalance_comparison.csv`.
- **Expone:** `run_backtest(prices, signals, params) -> BacktestResult`.

## Loop de trabajo

```
REPETIR hasta cumplir el criterio de terminado:
  1. Toma el primer ítem sin [x].
  2. Implementa.
  3. Verifica con un caso de juguete calculado a mano (2 días, 2 patas) y con la prueba de contabilidad.
  4. Marca [x], commit.
```

## Checklist

- [ ] Estado del portafolio por día: efectivo, acciones por activo, valor por pata, equity.
- [ ] Identidad contable: equity = cash + Σ valor de patas (largo positivo, corto negativo) en **cada** día.
- [ ] Comisión 0.125 % por operación, por pata, a la entrada **y** a la salida (y en cada rebalanceo).
- [ ] Préstamo 0.25 % anual sobre nocional corto, devengo **diario** (`/252` o `/360`: declararlo).
- [ ] 80 % del capital **disponible** (definir: equity actual vs capital inicial).
- [ ] Rebalanceo diario por β̂_t con costo registrado vs política de banda de no-rebalanceo → `rebalance_comparison.csv`.
- [ ] Stop por |z| y salida por holding máximo; motivo de salida en la bitácora.
- [ ] Walk-forward: train → test → validación con parámetros congelados; curva de capital continua con columna `split`.
- [ ] Bitácora de operaciones: fecha entrada/salida, dirección, días, P&L bruto, comisiones, préstamo, P&L neto, motivo.
- [ ] Atribución de costos: P&L bruto = neto + comisiones + préstamo.
- [ ] Figura 7: curvas de capital train / test / validación. Figura 2: spread con señales marcadas.

## Criterio de terminado

Prueba de contabilidad multi-pata pasa; costos totales = nº operaciones por pata × comisión + devengo de
préstamo; artefactos completos.

## Trampas

- Ejecutar al precio del mismo día en que se generó la señal con datos de cierre (look-ahead sutil).
- Cobrar comisión una sola vez por "operación de spread" en lugar de por pata.
- Olvidar el costo de rebalancear.

## Preguntas probables

- ¿Cuánto costó el rebalanceo diario vs la banda? ¿Cómo pierde dinero esta estrategia?
