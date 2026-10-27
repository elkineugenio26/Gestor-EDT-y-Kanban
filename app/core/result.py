"""Resultados explícitos: `Ok` / `Err`.

Los errores esperados (validación, transición inválida, "no existe") viajan como
valores, no como excepciones. Se consumen con `match/case` o con `and_then`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T


@dataclass(frozen=True)
class Err(Generic[E]):
    error: E


Result = Ok[T] | Err[E]


def map_ok(result: "Result", f: Callable) -> "Result":
    """Aplica `f` al valor si es Ok; deja pasar el Err intacto."""
    match result:
        case Ok(value):
            return Ok(f(value))
        case Err():
            return result


def and_then(result: "Result", f: Callable[[T], "Result"]) -> "Result":
    """Encadena pasos que pueden fallar (en el primer Err se corta)."""
    match result:
        case Ok(value):
            return f(value)
        case Err():
            return result
