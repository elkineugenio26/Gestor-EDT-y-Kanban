"""Transformaciones puras del proyecto, la EDT y las tareas.

Cada función recibe un `ProjectState` y devuelve `Ok(nuevo_estado)` o `Err(error)`.
Jamás modifica el estado recibido.
"""
from __future__ import annotations

from dataclasses import replace

from app.core import queries
from app.core.errors import Duplicate, NotFound
from app.core.kanban import change_status
from app.core.result import Err, Ok, Result, and_then
from app.core.validation import validate_name
from app.domain.models import Member, Priority, Project, ProjectState, Status, Task, WorkPackage


def create_project(project_id: str, name: str, description: str = "") -> Result:
    match validate_name("nombre del proyecto", 80)(name):
        case Err() as err:
            return err
        case Ok(clean_name):
            return Ok(ProjectState(Project(project_id, clean_name, description.strip())))


def add_member(state: ProjectState, member_id: str, name: str) -> Result:
    if queries.find_member(state, member_id) is not None:
        return Err(Duplicate("integrante", member_id))
    return and_then(
        validate_name("nombre del integrante", 60)(name),
        lambda clean: Ok(replace(state, members=state.members + (Member(member_id, clean),))),
    )


def add_package(state: ProjectState, package_id: str, name: str, parent_id: str | None = None) -> Result:
    if queries.find_package(state, package_id) is not None:
        return Err(Duplicate("paquete", package_id))
    if parent_id is not None:
        match queries.require("paquete padre", parent_id, state.packages):
            case Err() as err:
                return err
    return and_then(
        validate_name("nombre del paquete", 80)(name),
        lambda clean: Ok(replace(state, packages=state.packages + (WorkPackage(package_id, clean, parent_id),))),
    )


def add_task(
    state: ProjectState,
    task_id: str,
    title: str,
    package_id: str,
    priority: Priority = Priority.MEDIA,
    assignee_id: str | None = None,
) -> Result:
    """Crea una tarea validando título, paquete y responsable (si se indica)."""
    if queries.find_task(state, task_id) is not None:
        return Err(Duplicate("tarea", task_id))
    if queries.find_package(state, package_id) is None:
        return Err(NotFound("paquete", package_id))
    if assignee_id is not None and queries.find_member(state, assignee_id) is None:
        return Err(NotFound("integrante", assignee_id))
    return and_then(
        validate_name("título de la tarea", 120)(title),
        lambda clean: Ok(replace(state, tasks=state.tasks + (
            Task(task_id, clean, package_id, priority, Status.PENDIENTE, assignee_id),
        ))),
    )


def _replace_task(state: ProjectState, updated: Task) -> ProjectState:
    return replace(state, tasks=tuple(updated if t.id == updated.id else t for t in state.tasks))


def update_task(state: ProjectState, task_id: str, transform) -> Result:
    """HOF: aplica `transform: Task -> Result[Task]` a UNA tarea y reconstruye el estado.

    Si la tarea no existe o `transform` falla, devuelve Err y el estado original no cambia.
    """
    return and_then(
        queries.require("tarea", task_id, state.tasks),
        lambda task: and_then(transform(task), lambda updated: Ok(_replace_task(state, updated))),
    )


def move_task(state: ProjectState, task_id: str, requested: Status) -> Result:
    return update_task(state, task_id, lambda task: change_status(task, requested))


def assign_task(state: ProjectState, task_id: str, assignee_id: str | None) -> Result:
    """`assignee_id=None` quita el responsable."""
    if assignee_id is not None and queries.find_member(state, assignee_id) is None:
        return Err(NotFound("integrante", assignee_id))
    return update_task(state, task_id, lambda task: Ok(replace(task, assignee_id=assignee_id)))


def set_priority(state: ProjectState, task_id: str, priority: Priority) -> Result:
    return update_task(state, task_id, lambda task: Ok(replace(task, priority=priority)))
