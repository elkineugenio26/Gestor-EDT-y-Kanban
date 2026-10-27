"""Ensamble e inicio: aquí se conectan SQLite, el servicio y ReactPy sobre FastAPI.

FastAPI solo sirve la aplicación ReactPy: NO hay endpoints REST propios.

Ejecutar:  uvicorn app.main:app --reload
Base de datos: ./data/gestor.db (cambiar con la variable GESTOR_DB)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from reactpy.backend.fastapi import configure

from app.adapters.sqlite_repository import SqliteProjectRepository
from app.shell.service import AppService
from app.ui.app import make_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


def create_app(db_path: str | None = None) -> FastAPI:
    path = db_path or os.environ.get("GESTOR_DB", "data/gestor.db")
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    service = AppService(SqliteProjectRepository(path))
    api = FastAPI(title="Gestor EDT + Kanban")
    configure(api, make_app(service))
    return api


app = create_app()
