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

_Por definir en la siguiente sesión._ Llenar la tabla y copiar la asignación al `charter.md`.

| Parte | Dueño | Revisor (PR) |
|---|---|---|
| 01 Datos | | |
| 02 Cointegración y selección | | |
| 03 Kalman 1 — pesos | | |
| 04 Kalman 2 — señal | | |
| 05 VECM y señales | | |
| 06 Backtest | | |
| 07 Métricas | | |
| 08 Dashboard | | |
| 09 Formulación Powell (reporte) | | |
| 10 Tests | | |
| 11 Reporte y exposición | | |
| 12 Project management | | |

## Reglas de Git

- Ramas `feat/gc-<tema>` (Gonzalo) y `feat/jme-<tema>` (Juan Manuel). `main` siempre corre.
- PR obligatorio revisado por el otro integrante. El revisor debe poder explicar el código que aprueba.
- Commits pequeños, en español, con prefijo: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`.
- Revisar balance cada semana: `git shortlog -sn --no-merges`.
- Cada quien commitea con su propia cuenta (`git config user.name` / `user.email` correctos).
