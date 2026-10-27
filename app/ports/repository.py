"""Contrato mínimo para persistir proyectos.

Es un `Protocol` (tipado estructural): el núcleo y la shell dependen de ESTA forma,
no de SQLite. Un solo contrato, sin jerarquías de clases.

Todos los métodos devuelven `Ok`/`Err` (con `PersistenceError` o `NotFound`):
los problemas de disco son esperables y no deben escapar como excepciones.
"""
from __future__ import annotations

from typing import Protocol

from app.core.result import Result
from app.domain.models import ProjectState


class ProjectRepository(Protocol):
    def list_projects(self) -> Result:
        """Ok(tuple[Project, ...])"""

    def load_state(self, project_id: str) -> Result:
        """Ok(ProjectState) | Err(NotFound) | Err(PersistenceError)"""

    def save_state(self, state: ProjectState) -> Result:
        """Guarda el proyecto completo de forma atómica. Ok(None) | Err(PersistenceError)"""
