# 00 — Flujo de trabajo y división del proyecto

## Cómo usar estas guías

Cada archivo `NN_*.md` es una parte del proyecto y funciona como un **prompt con loop**: se le puede pasar a
Claude (o seguir a mano) tal cual. Todas tienen la misma forma:

1. **Encabezado** — dueño, carpeta, dependencias, notas de clase a leer antes.
2. **Contrato** — qué lee y qué escribe (archivos de `artifacts/`). No se rompe sin avisar.
3. **Loop de trabajo** — el ciclo implementar → verificar → marcar → commit.
4. **Checklist** — cada requisito del enunciado que toca esa parte. Nada se entrega sin `[x]`.
5. **Criterio de terminado** — cuándo se sale del loop.
6. **Trampas** y **preguntas probables de la exposición**.

Prompt sugerido para Claude:

> Lee `docs/instrucciones/CLAUDE.md`, `docs/instrucciones/NN_xxx.md` y las notas de clase que indica. Ejecuta el loop de trabajo
> hasta cumplir el criterio de terminado. Marca el checklist conforme avances y registra en
> `docs/decisiones.md` cualquier decisión no definida en clase. Explícame cada función al terminarla.

## Orden y dependencias

```
01 datos ──► 02 cointegración ──► 03 Kalman 1 ──► 04 Kalman 2 ──► 05 VECM/señales ──► 06 backtest ──► 07 métricas ──► 08 dashboard
                                        └──────────────── 09 formulación Powell (reporte) ───────────────┘
10 tests (crecen junto con cada parte) · 11 reporte y exposición · 12 project management (todo el proyecto)
```

Para trabajar en paralelo sin esperar al otro: se acuerda primero el **contrato de artefactos** (`docs/instrucciones/CLAUDE.md`)
y quien va adelante deja un artefacto "dummy" con el esquema correcto para que el otro pueda avanzar.

## División del trabajo (50/50)

Acordada el 2026-11-04. JME = Juan Manuel Espinosa, GC = Gonzalo Cano. La asignación se copia en los roles de `charter.md`.

| Parte | Dueño | Revisor (PR) | Notebook de demostración | Pruebas a su cargo |
|---|---|---|---|---|
| 01 Datos | JME | GC | `01_datos.ipynb` | — |
| 02 Cointegración y selección | GC | JME | `02_seleccion_grupo.ipynb` | — |
| 03 Kalman 1 — pesos | JME | GC | `03_filtro1_pesos.ipynb` | `test_normalization.py` |
| 04 Kalman 2 — señal | GC | JME | `04_filtro2_senal.ipynb` | `test_filter.py` |
| 05 VECM y señales | GC | JME | `05_vecm_senales.ipynb` | — |
| 06 Backtest | JME | GC | `06_backtest.ipynb` | `test_accounting.py` |
| 07 Métricas y figuras 1–8 | GC | JME | `07_metricas.ipynb` | `test_causality.py` |
| 08 Dashboard | JME: vista ejecutiva · GC: vista técnica | cruzado | — | — |
| 09 Formulación Powell (reporte) | JME: filtro 1 · GC: filtro 2 · ambos: sistema completo | cruzado | — | — |
| 10 Tests | cada quien las de su parte (columna de la derecha) | cruzado | — | — |
| 11 Reporte y exposición | ambos, mitad y mitad | — | — | — |
| 12 Project management | JME: charter y sprints 01–02 · ambos: cierre de sprint y post-mortem | — | — | — |

**Universos candidatos (paso 1 de la selección):** cada integrante aporta uno con su justificación económica
(`cointegration/universe.py`): JME petroleras de EE. UU. y Europa; GC mineras de oro más el metal. El código del
embudo es uno solo (parte 02) y corre sobre ambos universos; el grupo final de 4 sale de uno de ellos.

**Notebooks (`notebooks/`):** uno por parte, para mostrar avance al profesor y estudiar para la exposición.
Solo importan funciones de los módulos y muestran resultados; **no contienen lógica propia** (si una celda
calcula algo que `main.py` necesita, esa lógica va al módulo).

## Reglas de Git

- Ramas `feat/gc-<tema>` (Gonzalo) y `feat/jme-<tema>` (Juan Manuel). `main` siempre corre.
- PR obligatorio revisado por el otro integrante. El revisor debe poder explicar el código que aprueba.
- Commits pequeños, en español, con prefijo: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`.
- Revisar balance cada semana: `git shortlog -sn --no-merges`.
- Cada quien commitea con su propia cuenta (`git config user.name` / `user.email` correctos).
