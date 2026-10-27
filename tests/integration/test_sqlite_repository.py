"""Pruebas del adaptador SQLite. Siempre en memoria o en un archivo temporal: nunca datos reales."""
import sqlite3

import pytest

from app.adapters.sqlite_repository import SqliteProjectRepository
from app.core import commands, wbs
from app.core.errors import NotFound, PersistenceError
from app.core.result import Err, Ok
from app.domain.models import Priority, Status
from app.shell.service import AppService
from tests.conftest import unwrap


@pytest.fixture
def repo():
    r = SqliteProjectRepository(":memory:")
    yield r
    r.close()


def test_guardar_y_recuperar_es_identico(repo, state):
    assert repo.save_state(state) == Ok(None)
    assert repo.load_state("p1") == Ok(state)  # mismo contenido y mismo orden


def test_proyecto_inexistente_es_notfound_no_excepcion(repo):
    assert repo.load_state("nope") == Err(NotFound("proyecto", "nope"))


def test_lista_de_proyectos(repo, state):
    assert repo.list_projects() == Ok(())
    repo.save_state(state)
    assert unwrap(repo.list_projects()) == (state.project,)


def test_guardar_dos_veces_reemplaza_sin_duplicar(repo, state):
    repo.save_state(state)
    moved = unwrap(wbs.move_task(state, "t1", Status.EN_PROGRESO))
    repo.save_state(moved)
    loaded = unwrap(repo.load_state("p1"))
    assert loaded == moved and len(loaded.tasks) == 3


def test_persiste_ausencia_de_responsable_y_jerarquia(repo, state):
    repo.save_state(state)
    loaded = unwrap(repo.load_state("p1"))
    assert next(t for t in loaded.tasks if t.id == "t3").assignee_id is None
    assert next(p for p in loaded.packages if p.id == "k2").parent_id == "k1"


def test_esquema_controlado_es_idempotente(tmp_path):
    path = str(tmp_path / "t.db")
    SqliteProjectRepository(path).close()
    SqliteProjectRepository(path).close()  # reabrir no falla ni duplica
    conn = sqlite3.connect(path)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
    conn.close()


def test_los_datos_sobreviven_al_reabrir_el_archivo(tmp_path, state):
    path = str(tmp_path / "t.db")
    first = SqliteProjectRepository(path)
    first.save_state(state)
    first.close()
    second = SqliteProjectRepository(path)
    assert second.load_state("p1") == Ok(state)
    second.close()


def test_rollback_si_falla_a_mitad_de_guardado(repo, state):
    """Un estado inconsistente (tarea en paquete inexistente) viola la FK al insertar tareas.
    Todo el guardado debe revertirse: queda la versión anterior intacta."""
    repo.save_state(state)
    broken = unwrap(wbs.add_task(state, "t9", "Nueva", "k1"))
    from dataclasses import replace
    bad_task = replace(broken.tasks[-1], package_id="no-existe")
    broken = replace(broken, tasks=broken.tasks[:-1] + (bad_task,), project=replace(broken.project, name="CAMBIADO"))
    result = repo.save_state(broken)
    assert isinstance(result, Err) and isinstance(result.error, PersistenceError)
    assert unwrap(repo.load_state("p1")) == state  # ni el nombre ni las tareas cambiaron


def test_base_inaccesible_devuelve_error_no_excepcion(tmp_path):
    repo = SqliteProjectRepository(str(tmp_path / "no" / "existe" / "x.db"))
    assert isinstance(repo.list_projects(), Err)
    assert isinstance(repo.save_state(unwrap(wbs.create_project("p", "X"))), Err)


# --------------------------------------------------- shell: servicio + repositorio real
def test_servicio_flujo_completo_y_transicion_invalida_no_guarda(repo):
    svc = AppService(repo)
    project = unwrap(svc.create_project("Demo")).project
    unwrap(svc.execute(project.id, commands.AddPackage("k1", "Entregable 1")))
    unwrap(svc.execute(project.id, commands.AddTask("t1", "Hacer algo", "k1", Priority.ALTA)))

    rejected = svc.execute(project.id, commands.MoveTask("t1", Status.TERMINADA))
    assert isinstance(rejected, Err)
    assert unwrap(svc.load(project.id)).tasks[0].status == Status.PENDIENTE  # sin cambios parciales

    unwrap(svc.execute(project.id, commands.MoveTask("t1", Status.EN_PROGRESO)))
    assert unwrap(svc.load(project.id)).tasks[0].status == Status.EN_PROGRESO


def test_servicio_valida_antes_de_guardar(repo):
    svc = AppService(repo)
    assert isinstance(svc.create_project("   "), Err)
    assert unwrap(svc.list_projects()) == ()  # no se guardó nada


def test_servicio_proyecto_inexistente(repo):
    assert svc_err(AppService(repo).execute("nope", commands.AddMember("m", "X"))) == NotFound("proyecto", "nope")


def svc_err(result):
    assert isinstance(result, Err)
    return result.error
