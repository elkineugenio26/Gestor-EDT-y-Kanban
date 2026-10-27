"""Shell imperativa: coordina repositorio + núcleo puro.

Patrón en cada operación:  cargar (efecto) → función pura del core → guardar (efecto).
Si el core devuelve Err, NO se guarda nada: el estado persistido no cambia.
"""
from __future__ import annotations

import uuid

from app.core import commands, wbs
from app.core.result import Err, Ok, Result
from app.ports.repository import ProjectRepository
from app.shell.decorators import logged


def new_id() -> str:
    """Generar ids es un efecto (aleatoriedad): por eso vive en la shell, no en el core."""
    return uuid.uuid4().hex[:8]


class AppService:
    def __init__(self, repo: ProjectRepository):
        self._repo = repo

    def list_projects(self) -> Result:
        return self._repo.list_projects()

    def load(self, project_id: str) -> Result:
        return self._repo.load_state(project_id)

    @logged("crear proyecto")
    def create_project(self, name: str, description: str = "") -> Result:
        match wbs.create_project(new_id(), name, description):  # core puro (valida)
            case Err() as err:
                return err
            case Ok(state):
                match self._repo.save_state(state):  # efecto
                    case Err() as err:
                        return err
                    case Ok():
                        return Ok(state)

    @logged("ejecutar comando")
    def execute(self, project_id: str, command: commands.Command) -> Result:
        match self._repo.load_state(project_id):  # efecto: leer
            case Err() as err:
                return err
            case Ok(state):
                match commands.apply(state, command):  # core puro: decide
                    case Err() as err:
                        return err  # nada se guarda
                    case Ok(new_state):
                        match self._repo.save_state(new_state):  # efecto: escribir
                            case Err() as err:
                                return err
                            case Ok():
                                return Ok(new_state)
