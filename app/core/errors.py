"""Errores esperados del dominio, como datos (no excepciones)."""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import Status


@dataclass(frozen=True)
class ValidationError:
    field: str
    message: str


@dataclass(frozen=True)
class InvalidTransition:
    current: Status
    requested: Status


@dataclass(frozen=True)
class NotFound:
    entity: str  # "proyecto", "integrante", "paquete", "tarea"
    id: str


@dataclass(frozen=True)
class Duplicate:
    entity: str
    id: str


@dataclass(frozen=True)
class PersistenceError:
    """Lo produce el adaptador SQLite (la shell); vive aquí para tener un solo tipo de error."""
    detail: str


DomainError = ValidationError | InvalidTransition | NotFound | Duplicate | PersistenceError


def describe(error: DomainError) -> str:
    """Traduce un error a un mensaje comprensible. Pura: solo produce texto."""
    match error:
        case ValidationError(field, message):
            return f"Dato inválido en «{field}»: {message}"
        case InvalidTransition(current, requested):
            return f"No se puede pasar de «{current.value}» a «{requested.value}»."
        case NotFound(entity, ""):  # id vacío: la persona no eligió nada
            return f"Debes elegir un {entity}."
        case NotFound(entity, id):
            return f"No se encontró {entity} con id «{id}»."
        case Duplicate(entity, id):
            return f"Ya existe {entity} con id «{id}»."
        case PersistenceError(detail):
            return f"Problema al guardar o leer los datos: {detail}"
