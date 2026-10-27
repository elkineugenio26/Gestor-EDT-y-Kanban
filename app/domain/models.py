"""Tipos del dominio.

Todo es INMUTABLE (`frozen=True`, tuplas en vez de listas): una "modificación"
siempre produce un valor nuevo con `dataclasses.replace`. Aquí no hay I/O.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    PENDIENTE = "Pendiente"
    EN_PROGRESO = "En progreso"
    EN_REVISION = "En revisión"
    TERMINADA = "Terminada"


class Priority(str, Enum):
    BAJA = "Baja"
    MEDIA = "Media"
    ALTA = "Alta"


# Orden numérico para ordenar por prioridad (mayor = más urgente).
PRIORITY_RANK = {Priority.BAJA: 1, Priority.MEDIA: 2, Priority.ALTA: 3}


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    description: str = ""


@dataclass(frozen=True)
class Member:
    id: str
    name: str


@dataclass(frozen=True)
class WorkPackage:
    """Nodo de la EDT/WBS: un entregable o paquete de trabajo.

    `parent_id` permite anidar paquetes (None = nodo de primer nivel).
    """
    id: str
    name: str
    parent_id: str | None = None


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    package_id: str
    priority: Priority = Priority.MEDIA
    status: Status = Status.PENDIENTE
    assignee_id: str | None = None  # None = sin responsable (ausencia explícita)


@dataclass(frozen=True)
class ProjectState:
    """Snapshot completo de un proyecto: es lo que el core recibe y devuelve."""
    project: Project
    members: tuple[Member, ...] = ()
    packages: tuple[WorkPackage, ...] = ()
    tasks: tuple[Task, ...] = ()
