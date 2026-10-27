# Guía de entrega (equipo de 3)

Este documento ayuda a organizar el trabajo, el PDF y el video. No es parte del código.

## 1. Reparto sugerido de responsabilidades

El código ya está escrito, pero **cada integrante debe poder explicar y defender su parte**. Lean, ejecuten,
modifiquen y rompan su parte a propósito para entenderla.

| Integrante | Responsabilidad | Archivos | Temas que explica |
|---|---|---|---|
| **A: Núcleo de dominio** | Modelo, reglas Kanban, EDT y comandos | `domain/models.py`, `core/result.py`, `core/errors.py`, `core/kanban.py`, `core/wbs.py`, `core/commands.py`, `tests/unit/test_kanban.py`, `test_wbs_commands.py` | Inmutabilidad, manejo funcional de errores, pattern matching, del cómo al qué (tabla de transiciones) |
| **B: Persistencia y shell** | Puerto, SQLite, servicio, decorador | `ports/`, `adapters/sqlite_repository.py`, `shell/service.py`, `shell/decorators.py`, `tests/integration/test_sqlite_repository.py`, `test_validation_decorators.py` (parte del decorador) | Pureza/efectos, decoradores, transacciones atómicas, `load → apply → save` |
| **C: Consultas, validación e interfaz** | Filtros, orden, tablero, validadores, UI | `core/queries.py`, `core/validation.py`, `ui/`, `main.py`, `tests/unit/test_queries.py`, `tests/integration/test_ui_flow.py`, `test_architecture.py` | HOF, lambdas vs funciones con nombre, closures, ausencia de valor, ReactPy sobre FastAPI |

README, PDF y video: se reparten entre los tres (cada quien escribe las filas de la tabla de evidencias de su parte).

## 2. Cómo dejar un historial de contribuciones verdadero

El enunciado pide que el historial permita identificar el aporte de cada integrante. Lo que cuenta es trabajo
**real y propio** en el repositorio, no la cantidad de commits.

1. Una persona crea el repositorio remoto y agrega a las otras dos como colaboradoras.
2. Cada integrante trabaja en **su propia rama** (`feat/nucleo`, `feat/persistencia`, `feat/ui`) y abre un **Pull Request**
   que otro integrante revisa (las revisiones también son evidencia de contribución).
3. Cada quien hace commits con **su propio usuario de git** (`git config user.name` / `user.email`).
4. Antes de entregar, cada integrante debe haber hecho cambios sustantivos en su parte: por ejemplo, agregar un
   estado nuevo al Kanban (A), una restricción o un índice en SQLite (B), un filtro nuevo (C). Eso además los prepara para la defensa.
5. No reescriban el historial ni hagan commits a nombre de otra persona.

Ideas de ampliación que sirven como aporte propio y demuestran comprensión:
- A: editar el nombre de una tarea (`wbs.rename_task` + comando + pruebas).
- B: borrar una tarea con `ON DELETE` y probar el rollback.
- C: ordenar el tablero por otro criterio con otra función de clave; filtro por paquete (otro closure).

## 3. Contenido sugerido del PDF

1. **Portada**: título, integrantes, materia, fecha y **enlaces clicables** al repositorio y al video.
2. **Problema y objetivo**: por qué EDT y Kanban son distintos y complementarios.
3. **Solución**: capturas del recorrido (crear proyecto → EDT → tareas → mover en Kanban → filtros → error de transición).
4. **Arquitectura**: diagrama núcleo / shell / adaptador y el flujo `load → apply → save`.
5. **Flujo EDT/Kanban**: ejemplo con un proyecto real y la tabla de transiciones.
6. **Decisiones funcionales**: la tabla de evidencias del README (resumida) y qué es puro y qué no.
7. **Pruebas**: salida de `python -m pytest` (71 pruebas) y qué cubre cada carpeta.
8. **Contribuciones**: por integrante, responsabilidad y dónde se ve (ramas, PRs, commits, archivos).
9. **Uso de IA**: en qué se usó como apoyo y cómo verificaron y entendieron el código.

Verifiquen que los enlaces del PDF **se pueden pulsar** y abren el repositorio y el video.

## 4. Guion del video (≈ 8–10 min, los tres hablan)

| Tiempo | Quién | Contenido |
|---|---|---|
| 0:00 | Todos | Presentación y qué hace la app |
| 0:30 | C | Demo: crear proyecto, integrantes, EDT con subpaquetes, tareas con responsable y prioridad |
| 2:30 | C | Demo: filtros y estados vacíos; mensaje por dato inválido |
| 3:30 | A | Demo: mover tareas por el Kanban; mostrar que no se puede saltar etapas. Mostrar `ALLOWED_TRANSITIONS` y `change_status`; explicar `Ok`/`Err`, inmutabilidad y `match/case` en `commands.apply` |
| 5:30 | C | Mostrar `queries.py`: closures (`by_assignee`), HOF (`filter_tasks`, `all_of`), lambda vs `priority_then_title` |
| 6:30 | B | Mostrar `service.execute` (cargar → puro → guardar), el adaptador SQLite, la transacción y el decorador `@logged` |
| 8:00 | B | Correr `pytest`; mostrar `test_architecture.py` y la prueba de rollback |
| 9:00 | Todos | Cierre: qué es puro, qué es efecto y qué aprendieron |

## 5. Lista final

- [ ] Todos hicieron commits/PRs propios y pueden explicarlos.
- [ ] `pip install -r requirements.txt` y `uvicorn app.main:app` funcionan en una máquina limpia.
- [ ] `python -m pytest` pasa.
- [ ] Reemplazaron los marcadores «[Agregar aquí el enlace…]» del enunciado por los enlaces reales.
- [ ] El PDF tiene enlaces clicables al repositorio y al video.
- [ ] Los tres aparecen hablando en el video.
