"""Comandos: la UI describe QUÉ quiere hacer; `apply` decide cómo (pattern matching).

Los ids vienen DENTRO del comando (los genera la shell): así `apply` sigue siendo
pura y determinista, sin llamar a uuid ni al reloj.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core import wbs
from app.core.result import Result
from app.domain.models import Priority, ProjectState, Status


@dataclass(frozen=True)
class AddMember:
    member_id: str
    name: str


@dataclass(frozen=True)
class AddPackage:
    package_id: str
    name: str
    parent_id: str | None = None


@dataclass(frozen=True)
class AddTask:
    task_id: str
    title: str
    package_id: str
    priority: Priority = Priority.MEDIA
    assignee_id: str | None = None


@dataclass(frozen=True)
class MoveTask:
    task_id: str
    status: Status


@dataclass(frozen=True)
class AssignTask:
    task_id: str
    assignee_id: str | None


@dataclass(frozen=True)
class SetPriority:
    task_id: str
    priority: Priority


Command = AddMember | AddPackage | AddTask | MoveTask | AssignTask | SetPriority


def apply(state: ProjectState, command: Command) -> Result:
    """Despacha un comando al caso de uso correspondiente. Pura."""
    match command:
        case AddMember(member_id, name):
            return wbs.add_member(state, member_id, name)
        case AddPackage(package_id, name, parent_id):
            return wbs.add_package(state, package_id, name, parent_id)
        case AddTask(task_id, title, package_id, priority, assignee_id):
            return wbs.add_task(state, task_id, title, package_id, priority, assignee_id)
        case MoveTask(task_id, status):
            return wbs.move_task(state, task_id, status)
        case AssignTask(task_id, assignee_id):
            return wbs.assign_task(state, task_id, assignee_id)
        case SetPriority(task_id, priority):
            return wbs.set_priority(state, task_id, priority)
