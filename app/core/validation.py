"""Validadores pequeños y componibles (funciones de orden superior)."""
from __future__ import annotations

from typing import Callable

from app.core.errors import ValidationError
from app.core.result import Err, Ok, Result

# Un validador recibe un valor y devuelve Ok(valor_normalizado) o Err(ValidationError)
Validator = Callable[[str], "Result"]


def non_empty(field: str) -> Validator:
    """CLOSURE: captura `field` para construir el mensaje de error."""
    def check(value: str) -> Result:
        clean = (value or "").strip()
        return Ok(clean) if clean else Err(ValidationError(field, "no puede estar vacío"))
    return check


def max_length(field: str, limit: int) -> Validator:
    """CLOSURE: captura `field` y `limit`."""
    def check(value: str) -> Result:
        return Ok(value) if len(value) <= limit else Err(
            ValidationError(field, f"no puede superar {limit} caracteres")
        )
    return check


def all_validators(*validators: Validator) -> Validator:
    """HOF: compone validadores; devuelve el primer error o el valor normalizado."""
    def check(value: str) -> Result:
        current = value
        for validator in validators:
            match validator(current):
                case Ok(v):
                    current = v
                case Err() as err:
                    return err
        return Ok(current)
    return check


def validate_name(field: str, limit: int = 80) -> Validator:
    return all_validators(non_empty(field), max_length(field, limit))
