# Gestor de proyectos con EDT y Kanban

Aplicación web local para planificar un proyecto con una **Estructura de Desglose del Trabajo (EDT/WBS)**,
asignar responsables y seguir el avance en un tablero **Kanban**.

- La **EDT** responde *¿qué trabajo hay que realizar?* (paquetes y tareas).
- **Kanban** responde *¿en qué estado está ese trabajo?* (Pendiente → En progreso → En revisión → Terminada).

Stack: Python 3.10+ (probado en 3.13; se usa `match/case`) · ReactPy (interfaz) · FastAPI (solo sirve la app, **sin API REST propia**) · SQLite · pytest.

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> `fastapi` está fijado a `0.115.14` a propósito: ReactPy 1.1 usa `Starlette.add_websocket_route`,
> que las versiones más recientes de FastAPI/Starlette eliminaron.

## Ejecución

```bash
uvicorn app.main:app --reload
```

Abrir <http://127.0.0.1:8000>. Los datos se guardan en `data/gestor.db` (se crea solo).
Para usar otra base: `GESTOR_DB=/ruta/otra.db uvicorn app.main:app`.

## Pruebas

```bash
python -m pytest
```

- `tests/unit/`: núcleo puro (sin ReactPy, sin FastAPI, sin archivos) + prueba de arquitectura.
- `tests/integration/`: adaptador SQLite (en memoria o archivo temporal, nunca datos reales)
  y un recorrido de la interfaz ReactPy sin navegador.

## Estructura

```text
app/
  domain/models.py        Tipos inmutables: Project, Member, WorkPackage, Task, ProjectState, Status, Priority
  core/                   NÚCLEO FUNCIONAL (puro: sin I/O)
    result.py             Ok / Err
    errors.py             Errores como datos + describe() para mensajes
    validation.py         Validadores componibles
    kanban.py             Tabla de transiciones y change_status
    wbs.py                Crear proyecto / EDT / tareas (ProjectState -> Result[ProjectState])
    queries.py            Búsquedas, filtros, orden, tablero, conteos
    commands.py           Comandos + apply() con match/case
  ports/repository.py    Contrato mínimo de persistencia (Protocol)
  adapters/sqlite_repository.py   SQLite: esquema, transacciones, errores
  shell/                  SHELL IMPERATIVA
    service.py            cargar → core puro → guardar
    decorators.py         @logged (registro + duración)
  ui/                     Componentes ReactPy (sin reglas de negocio)
  main.py                 Ensamble: SQLite + servicio + ReactPy sobre FastAPI
tests/
```

## Decisiones de arquitectura

**Functional Core / Imperative Shell.** Todo lo que decide algo (validar, mover una tarea, filtrar,
ordenar, contar) está en `app/core` y son funciones puras: misma entrada → misma salida, sin efectos.
La shell hace lo que depende del entorno: leer/escribir SQLite, generar ids (`uuid`), registrar logs
y dibujar la interfaz.

```text
Evento ReactPy → AppService.execute
                   1. repo.load_state(...)            (efecto: leer)
                   2. commands.apply(state, command)  (PURO: decide)
                   3. repo.save_state(new_state)      (efecto: escribir, transacción)
                 → la UI muestra el nuevo estado o el mensaje de error
```

- **Estado como valor.** El core recibe un `ProjectState` completo y devuelve uno nuevo. Si el core
  devuelve `Err`, la shell **no guarda nada**: no hay estados parciales.
- **Ids fuera del core.** Los ids viajan dentro de los comandos (los genera la shell), así `apply` es determinista.
- **Guardado atómico.** `save_state` reemplaza el proyecto en una sola transacción; si algo falla, hace rollback.
- **Un solo puerto.** `ProjectRepository` es un `Protocol` con 3 métodos; no hay jerarquías ni capas extra.
- **La arquitectura se verifica con una prueba** (`tests/unit/test_architecture.py`): el núcleo no puede importar
  ReactPy, FastAPI, SQLite, `os`, `uuid`, `time`, `logging`, ni la shell/UI.

### Reglas Kanban

```text
Pendiente  ⇄  En progreso  ⇄  En revisión  ⇄  Terminada
```

Sin saltar etapas (Pendiente → Terminada es inválido). Reabrir una tarea terminada la devuelve a *En revisión*.
Las reglas son una tabla inmutable (`ALLOWED_TRANSITIONS` en `app/core/kanban.py`); la UI solo ofrece los botones permitidos
(`next_statuses`), pero la regla se vuelve a comprobar en el core.

## Evidencia de los temas del curso

| Contenido | Archivo → función / tipo | Qué se aplica y por qué |
|---|---|---|
| Del cómo al qué | `core/kanban.py` → `ALLOWED_TRANSITIONS`; `core/queries.py` → `board`, `build_predicate`, `pending_by_member` | Las transiciones son una **tabla de datos**, no `if` anidados. El tablero y los conteos se expresan como transformaciones (`{status: filter(...) for status in Status}`, `Counter(...)`). |
| Pattern matching estructural | `core/commands.py` → `apply`; `core/errors.py` → `describe`; `core/result.py` → `map_ok`, `and_then`; `shell/service.py` → `execute`; `ui/app.py` | `match/case` sobre dataclasses (comandos, errores, `Ok`/`Err`): cada variante se trata de forma explícita. |
| Funciones de orden superior | `core/queries.py` → `filter_tasks`, `sort_tasks`, `all_of`; `core/validation.py` → `all_validators`; `core/wbs.py` → `update_task` | Reciben funciones (predicado, clave, validador, transformación) y deciden el *cómo* a partir de ellas. `update_task` reutiliza «buscar + transformar + reconstruir» para mover, asignar y cambiar prioridad. |
| Lambdas y HOF | `core/queries.py` → `by_title_key`, `by_status`; `core/wbs.py` → lambdas pasadas a `and_then`; `ui/app.py` | Lambdas para criterios de una expresión. En cambio `priority_then_title` es una **función con nombre**: tiene lógica de dos niveles, se reutiliza (`board`) y se prueba por separado. |
| Closures | `core/queries.py` → `by_status`, `by_priority`, `by_assignee`; `core/validation.py` → `non_empty`, `max_length`; `shell/decorators.py` → `logged` | Cada closure captura un criterio **inmutable** (un Enum, un `str`, un `int`). No hay estado mutable escondido. `test_closure_captura_su_criterio` lo comprueba. |
| Inmutabilidad | `domain/models.py` (todas `frozen=True`, tuplas); `core/wbs.py` (`dataclasses.replace`) | Una «modificación» crea un valor nuevo. `test_el_estado_original_no_se_modifica` y `test_los_datos_del_dominio_son_inmutables` lo verifican. |
| Pureza y efectos secundarios | Puras: todo `app/core/` y `app/domain/`. Efectos: `adapters/sqlite_repository.py` (disco), `shell/service.py` (`new_id`, orquestación), `shell/decorators.py` (logging, reloj), `ui/` (pantalla) | Ver la tabla de abajo. `tests/unit/test_architecture.py` impide que el core importe infraestructura. |
| Ausencia de valor | `core/queries.py` → `find_by_id` (devuelve `None`), `require` (→ `Err(NotFound)`); `domain/models.py` → `Task.assignee_id: str \| None` | «No existe» (`None`/`NotFound`) se distingue de «existe y está vacío» (`()` en tablero, `0` pendientes). «Sin responsable» es un valor explícito (`UNASSIGNED`). |
| Manejo funcional de errores | `core/result.py` (`Ok`/`Err`); `core/errors.py` (`ValidationError`, `InvalidTransition`, `NotFound`, `Duplicate`, `PersistenceError`) | Los errores esperados son **valores**, no excepciones. Solo los fallos de infraestructura (`sqlite3.Error`, o un valor corrupto leído de la base) se capturan en la frontera del adaptador y se convierten en `Err(PersistenceError)`. |
| Decoradores | `shell/decorators.py` → `logged`; usado en `shell/service.py` (`create_project`, `execute`) | Preocupación transversal (registro + duración). Usa `functools.wraps`, **no cambia el resultado** y no contiene reglas del dominio. Probado en `test_validation_decorators.py`. |

### Qué es puro y qué no

| Función / módulo | ¿Puro? | Justificación |
|---|---|---|
| `kanban.change_status`, `wbs.*`, `commands.apply` | Sí | Reciben datos y devuelven un valor nuevo o `Err`; no tocan el original. |
| `queries.*` (filtros, orden, tablero, conteos, `wbs_outline`) | Sí | Solo transforman tuplas. |
| `errors.describe` | Sí | Solo produce texto. |
| `shell.service.new_id` | No | Aleatoriedad (`uuid`). Por eso no está en el core. |
| `SqliteProjectRepository.*` | No | Lee/escribe disco; puede fallar. |
| `shell.decorators.logged` | No | Lee el reloj y escribe logs. |
| Componentes en `ui/` | No | Estado visual y eventos del navegador. Las decisiones las toma el core. |

## Alcance

Cubre las 9 funciones mínimas del enunciado: crear/consultar proyecto, integrantes, EDT jerárquica (paquetes anidados) y tareas,
responsable/prioridad/estado, tablero, transiciones válidas, filtros (estado, responsable, prioridad), SQLite, y mensajes para
datos inválidos, búsquedas vacías y errores de persistencia.
Fuera de alcance (según el enunciado): API REST, autenticación, tiempo real, integraciones externas y evaluación lazy.

## Limitaciones conocidas

- No hay edición ni borrado de paquetes, integrantes o tareas (solo alta, asignación, prioridad y cambio de estado).
- `save_state` reescribe el proyecto completo en cada operación: simple y atómico, adecuado para un uso local; no escalaría a muchos usuarios.
- ReactPy 1.1 exige una versión antigua de FastAPI (ver Instalación).
