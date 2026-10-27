"""Reglas Kanban: qué transiciones de estado están permitidas.

Las reglas son DATOS (una tabla), no `if` encadenados: describen el QUÉ.

    Pendiente ⇄ En progreso ⇄ En revisión ⇄ Terminada
    (no se puede saltar etapas: p. ej. Pendiente → Terminada es inválido)
"""
from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType

from app.core.errors import InvalidTransition
from app.core.result import Err, Ok, Result
from app.domain.models import Status, Task

# MappingProxyType + frozenset: la tabla misma es inmutable.
ALLOWED_TRANSITIONS = MappingProxyType({
    Status.PENDIENTE: frozenset({Status.EN_PROGRESO}),
    Status.EN_PROGRESO: frozenset({Status.PENDIENTE, Status.EN_REVISION}),
    Status.EN_REVISION: frozenset({Status.EN_PROGRESO, Status.TERMINADA}),
    Status.TERMINADA: frozenset({Status.EN_REVISION}),  # reabrir pasa por revisión
})


def can_transition(current: Status, requested: Status) -> bool:
    return requested in ALLOWED_TRANSITIONS[current]


def next_statuses(current: Status) -> tuple[Status, ...]:
    """Estados a los que se puede mover (en el orden del tablero). Sirve para la UI."""
    return tuple(s for s in Status if can_transition(current, s))


def change_status(task: Task, requested: Status) -> Result:
    """Devuelve una tarea NUEVA con el estado cambiado, o Err(InvalidTransition).

    Pura: no muta `task`. Si falla, el original queda intacto.
    """
    if not can_transition(task.status, requested):
        return Err(InvalidTransition(task.status, requested))
    return Ok(replace(task, status=requested))
