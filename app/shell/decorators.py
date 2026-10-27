"""Decorador de una preocupación TRANSVERSAL: registrar y medir una operación.

No contiene reglas del dominio ni cambia el resultado de la función decorada:
solo observa (nombre, duración, éxito/fracaso) y devuelve el valor tal cual.
"""
from __future__ import annotations

import functools
import logging
import time
from typing import Callable

from app.core.result import Err, Ok

logger = logging.getLogger("gestor")


def logged(operation: str) -> Callable:
    """Fábrica de decorador (closure sobre `operation`).

    Uso:
        @logged("mover tarea")
        def mover(...): ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)  # conserva __name__ y __doc__ de la función original
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            match result:
                case Ok():
                    logger.info("%s: ok (%.1f ms)", operation, elapsed_ms)
                case Err(error):
                    logger.warning("%s: error %s (%.1f ms)", operation, error, elapsed_ms)
                case _:
                    logger.info("%s: terminó (%.1f ms)", operation, elapsed_ms)
            return result
        return wrapper
    return decorator
