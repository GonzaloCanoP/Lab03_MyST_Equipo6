# 10 — Pruebas obligatorias (pytest)

**Dueño:** cada prueba la escribe quien implementa la parte que prueba · **Carpeta:** `tests/`

## Loop de trabajo

```
REPETIR hasta que pytest pase en verde con las 4 pruebas:
  1. Escribe la prueba ANTES o junto con la parte que prueba.
  2. Córrela: pytest -v tests/test_xxx.py
  3. Si falla, arregla el código (no la prueba), salvo que la prueba esté mal planteada.
  4. Commit.
```

## Checklist

- [ ] `test_causality.py` — z_t no cambia al recalcular el pipeline completo con datos hasta t, para ≥ 3 valores de t.
- [x] `test_normalization.py` — β̂ mantiene escala y signo estables entre reestimaciones consecutivas (Johansen en ventanas consecutivas, invariancia a la escala del eigenvector, filtro 1 con ancla fija y sin cambios de signo, datos del proyecto).
- [ ] `test_accounting.py` — equity = cash + Σ patas; costo total = nº operaciones por pata × comisión + devengo de préstamo en cortos.
- [ ] `test_filter.py` — innovaciones normalizadas con varianza ≈ 1 (tolerancia declarada) y autocorrelación no significativa.
- [ ] ~~Nivel B: contribuciones al riesgo iguales~~ (fuera de alcance, sin Risk Parity).
- [ ] Pruebas rápidas (< 1 min en total): usar subconjuntos o fixtures pequeños.
- [ ] `pytest` corre desde la raíz sin configuración extra.
