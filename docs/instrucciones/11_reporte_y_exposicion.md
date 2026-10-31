# 11 — Reporte ejecutivo (docs/reporte.pdf) y exposición

**Dueño:** ambos · **Depende de:** todo

## Loop de trabajo

```
REPETIR hasta cumplir el criterio de terminado:
  1. Toma la primera sección sin [x].
  2. Redáctala con cifras propias (de artifacts/metrics.json, tablas, figuras).
  3. Verifica: cada afirmación tiene un número o figura que la respalde.
  4. Marca [x].
```

## Checklist — Reporte

- [ ] Universo y justificación económica; argumento contra pruebas múltiples.
- [ ] Tabla de selección (todos los grupos, etapa de descarte, total evaluado).
- [ ] Johansen: traza, max-eigen, rango, comparación de vectores, ADF y vida media.
- [ ] Formulación Powell: filtro 1, filtro 2, sistema completo (ver 09).
- [ ] Q, R, inicialización, burn-in, normalización y signo.
- [ ] VECM: α y su interpretación.
- [ ] Umbrales y procedimiento de búsqueda.
- [ ] Resultados por split, costos, rebalanceo diario vs banda.
- [ ] Figuras 1–8 con título, ejes y leyenda.
- [ ] ¿Relación estructural o artefacto? Respuesta argumentada con cifras.
- [ ] Supuestos y limitaciones explícitos.
- [ ] PDF en `docs/reporte.pdf` **antes** de la exposición (−5 si no).

## Checklist — Exposición (10 min + 5 de preguntas)

- [ ] Guion con reparto de tiempo 50/50.
- [ ] Diapositivas limpias, una idea por gráfica, sin capturas de código ni texto saturado.
- [ ] Sin leer notas ni diapositivas.
- [ ] Ensayo cronometrado (≤ 10 min) al menos 2 veces.
- [ ] Cada integrante puede explicar **todo** el código: sesión de preguntas cruzadas usando las secciones
      "Preguntas probables" de cada guía.
- [ ] Saber ubicar en el código: z prior, normalización, cálculo de costos, split.
