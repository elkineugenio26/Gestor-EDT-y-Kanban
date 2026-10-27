"""Adaptador SQLite: único lugar que conoce SQL y el sistema de archivos.

- El esquema se crea de forma controlada (`CREATE TABLE IF NOT EXISTS` + `user_version`).
- `save_state` corre en UNA transacción: o se guarda todo o no se guarda nada.
- Cualquier `sqlite3.Error` se convierte en `Err(PersistenceError)`.
"""
from __future__ import annotations

import sqlite3
import threading

from app.core.errors import NotFound, PersistenceError
from app.core.result import Err, Ok, Result
from app.domain.models import (
    Member, Priority, Project, ProjectState, Status, Task, WorkPackage,
)

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    description TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS members (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    position INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS packages (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    parent_id TEXT REFERENCES packages(id) ON DELETE CASCADE,
    position INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    package_id TEXT NOT NULL REFERENCES packages(id) ON DELETE CASCADE,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    priority TEXT NOT NULL CHECK (priority IN ('Baja', 'Media', 'Alta')),
    status TEXT NOT NULL CHECK (status IN ('Pendiente', 'En progreso', 'En revisión', 'Terminada')),
    assignee_id TEXT REFERENCES members(id) ON DELETE SET NULL,
    position INTEGER NOT NULL
);
"""


class SqliteProjectRepository:
    def __init__(self, path: str = ":memory:"):
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None
        self._init_error: PersistenceError | None = None
        try:
            self._conn = sqlite3.connect(path, check_same_thread=False)
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._init_schema()
        except sqlite3.Error as exc:
            self._init_error = PersistenceError(f"no se pudo abrir la base de datos: {exc}")

    # ------------------------------------------------------------------ esquema
    def _init_schema(self) -> None:
        assert self._conn is not None
        with self._conn:
            self._conn.executescript(SCHEMA)
            self._conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()

    def _usable(self) -> Err | None:
        return Err(self._init_error) if self._init_error is not None else None

    # -------------------------------------------------------------------- lecturas
    def list_projects(self) -> Result:
        if (err := self._usable()) is not None:
            return err
        try:
            with self._lock:
                rows = self._conn.execute("SELECT id, name, description FROM projects ORDER BY rowid").fetchall()
            return Ok(tuple(Project(*row) for row in rows))
        except sqlite3.Error as exc:
            return Err(PersistenceError(str(exc)))

    def load_state(self, project_id: str) -> Result:
        if (err := self._usable()) is not None:
            return err
        try:
            with self._lock:
                c = self._conn
                row = c.execute("SELECT id, name, description FROM projects WHERE id = ?", (project_id,)).fetchone()
                if row is None:
                    return Err(NotFound("proyecto", project_id))
                members = c.execute(
                    "SELECT id, name FROM members WHERE project_id = ? ORDER BY position", (project_id,)).fetchall()
                packages = c.execute(
                    "SELECT id, name, parent_id FROM packages WHERE project_id = ? ORDER BY position",
                    (project_id,)).fetchall()
                tasks = c.execute(
                    "SELECT id, title, package_id, priority, status, assignee_id FROM tasks "
                    "WHERE project_id = ? ORDER BY position", (project_id,)).fetchall()
            return Ok(ProjectState(
                project=Project(*row),
                members=tuple(Member(*m) for m in members),
                packages=tuple(WorkPackage(*p) for p in packages),
                tasks=tuple(Task(i, t, pk, Priority(pr), Status(st), a) for i, t, pk, pr, st, a in tasks),
            ))
        except (sqlite3.Error, ValueError) as exc:  # ValueError: valor de enum corrupto
            return Err(PersistenceError(str(exc)))

    # ------------------------------------------------------------------ escritura
    def save_state(self, state: ProjectState) -> Result:
        if (err := self._usable()) is not None:
            return err
        pid = state.project.id
        try:
            with self._lock, self._conn:  # `with conn`: COMMIT si todo sale bien, ROLLBACK si hay error
                c = self._conn
                c.execute(
                    "INSERT INTO projects (id, name, description) VALUES (?, ?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET name = excluded.name, description = excluded.description",
                    (pid, state.project.name, state.project.description))
                # Se reemplaza el contenido del proyecto. Orden: hijos antes que padres.
                c.execute("DELETE FROM tasks WHERE project_id = ?", (pid,))
                c.execute("DELETE FROM packages WHERE project_id = ?", (pid,))
                c.execute("DELETE FROM members WHERE project_id = ?", (pid,))
                c.executemany(
                    "INSERT INTO members (id, project_id, name, position) VALUES (?, ?, ?, ?)",
                    [(m.id, pid, m.name, i) for i, m in enumerate(state.members)])
                # `parent_id` se inserta primero en NULL y luego se enlaza: evita depender del orden.
                c.executemany(
                    "INSERT INTO packages (id, project_id, name, parent_id, position) VALUES (?, ?, ?, NULL, ?)",
                    [(p.id, pid, p.name, i) for i, p in enumerate(state.packages)])
                c.executemany(
                    "UPDATE packages SET parent_id = ? WHERE id = ?",
                    [(p.parent_id, p.id) for p in state.packages if p.parent_id is not None])
                c.executemany(
                    "INSERT INTO tasks (id, project_id, package_id, title, priority, status, assignee_id, position) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [(t.id, pid, t.package_id, t.title, t.priority.value, t.status.value, t.assignee_id, i)
                     for i, t in enumerate(state.tasks)])
            return Ok(None)
        except sqlite3.Error as exc:
            return Err(PersistenceError(str(exc)))
