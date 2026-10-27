"""Consultas puras sobre el estado: búsqueda, filtros, orden, tablero.

Aquí se concentran funciones de orden superior, closures y lambdas.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Callable, Iterable

from app.core.errors import NotFound
from app.core.result import Err, Ok, Result
from app.domain.models import (
    PRIORITY_RANK, Member, Priority, ProjectState, Status, Task, WorkPackage,
)

Predicate = Callable[[Task], bool]

UNASSIGNED = "__sin_responsable__"  # valor especial de filtro: tareas sin responsable


# ---------------------------------------------------------------- Ausencia de valor
def find_by_id(items: Iterable, item_id: str):
    """Devuelve el elemento o `None` si NO existe (ausencia explícita)."""
    return next((item for item in items if item.id == item_id), None)


def require(entity: str, item_id: str, items: Iterable) -> Result:
    """Convierte la ausencia (None) en un Err(NotFound) con significado."""
    found = find_by_id(items, item_id)
    if found is None:
        return Err(NotFound(entity, item_id))
    return Ok(found)


def find_task(state: ProjectState, task_id: str) -> Task | None:
    return find_by_id(state.tasks, task_id)


def find_member(state: ProjectState, member_id: str) -> Member | None:
    return find_by_id(state.members, member_id)


def find_package(state: ProjectState, package_id: str) -> WorkPackage | None:
    return find_by_id(state.packages, package_id)


# ---------------------------------------------------------- Closures: fábricas de filtros
def by_status(status: Status) -> Predicate:
    """CLOSURE: captura `status`. El estado capturado es inmutable (un Enum)."""
    return lambda task: task.status == status


def by_priority(priority: Priority) -> Predicate:
    return lambda task: task.priority == priority


def by_assignee(assignee_id: str) -> Predicate:
    """CLOSURE: captura el responsable. `UNASSIGNED` filtra las tareas sin responsable."""
    if assignee_id == UNASSIGNED:
        return lambda task: task.assignee_id is None
    return lambda task: task.assignee_id == assignee_id


def all_of(*predicates: Predicate) -> Predicate:
    """HOF: combina predicados con AND. Sin predicados, acepta todo."""
    return lambda task: all(p(task) for p in predicates)


def filter_tasks(tasks: Iterable[Task], predicate: Predicate) -> tuple[Task, ...]:
    """HOF: el 'cómo' filtrar lo decide el predicado que se recibe."""
    return tuple(filter(predicate, tasks))


@dataclass(frozen=True)
class TaskFilter:
    """Filtros elegidos por la UI. `None` = ese criterio no se aplica."""
    status: Status | None = None
    assignee_id: str | None = None
    priority: Priority | None = None


def build_predicate(f: TaskFilter) -> Predicate:
    """Declarativo: arma el predicado solo con los criterios activos."""
    active = [
        by_status(f.status) if f.status is not None else None,
        by_assignee(f.assignee_id) if f.assignee_id is not None else None,
        by_priority(f.priority) if f.priority is not None else None,
    ]
    return all_of(*(p for p in active if p is not None))


# ------------------------------------------------------------------------ Orden
def sort_tasks(tasks: Iterable[Task], key: Callable[[Task], object], reverse: bool = False) -> tuple[Task, ...]:
    return tuple(sorted(tasks, key=key, reverse=reverse))


# Lambdas pequeñas: criterios de una sola expresión, usados en un solo lugar.
by_title_key = lambda t: t.title.lower()


def priority_then_title(task: Task) -> tuple[int, str]:
    """Función CON NOMBRE: se reutiliza, se prueba y merece documentación.
    Más prioritaria primero (rank negativo), desempate alfabético."""
    return (-PRIORITY_RANK[task.priority], task.title.lower())


# ----------------------------------------------------------------------- Tablero
def board(tasks: Iterable[Task]) -> dict[Status, tuple[Task, ...]]:
    """Agrupa tareas por columna. Siempre incluye las 4 columnas (aunque vacías)."""
    tasks = tuple(tasks)
    return {
        status: sort_tasks(filter_tasks(tasks, by_status(status)), priority_then_title)
        for status in Status
    }


def pending_by_member(state: ProjectState) -> dict[str, int]:
    """Tareas no terminadas por integrante (clave UNASSIGNED = sin responsable)."""
    open_tasks = filter_tasks(state.tasks, lambda t: t.status != Status.TERMINADA)
    counts = Counter(t.assignee_id if t.assignee_id is not None else UNASSIGNED for t in open_tasks)
    # Incluye integrantes con 0 pendientes: "no tiene tareas" es un dato válido.
    return {**{m.id: 0 for m in state.members}, **counts}


def count_by_status(tasks: Iterable[Task]) -> dict[Status, int]:
    """Cantidad de tareas por estado (las 4 claves siempre presentes, aunque valgan 0)."""
    counts = Counter(t.status for t in tasks)
    return {status: counts.get(status, 0) for status in Status}


def progress_percent(tasks: Iterable[Task]) -> int:
    """% de tareas terminadas (0 si no hay tareas)."""
    tasks = tuple(tasks)
    if not tasks:
        return 0
    done = len(filter_tasks(tasks, by_status(Status.TERMINADA)))
    return round(100 * done / len(tasks))


# -------------------------------------------------------------------------- EDT
def wbs_outline(packages: Iterable[WorkPackage]) -> tuple[tuple[WorkPackage, int], ...]:
    """Aplana el árbol de la EDT en orden jerárquico: ((paquete, profundidad), ...)."""
    packages = tuple(packages)

    def children_of(parent_id: str | None) -> tuple[WorkPackage, ...]:
        return tuple(p for p in packages if p.parent_id == parent_id)

    def walk(parent_id: str | None, depth: int) -> tuple[tuple[WorkPackage, int], ...]:
        return tuple(
            entry
            for pkg in children_of(parent_id)
            for entry in ((pkg, depth),) + walk(pkg.id, depth + 1)
        )

    return walk(None, 0)