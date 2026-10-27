import dataclasses

import pytest

from app.core import commands, wbs
from app.core.errors import Duplicate, InvalidTransition, NotFound, ValidationError, describe
from app.core.result import Err, Ok
from app.domain.models import Priority, Status
from tests.conftest import unwrap


# ------------------------------------------------------------------ proyecto
def test_crear_proyecto_normaliza_el_nombre():
    assert unwrap(wbs.create_project("p", "  Mi proyecto  ")).project.name == "Mi proyecto"


@pytest.mark.parametrize("name", ["", "   ", "x" * 81])
def test_crear_proyecto_rechaza_nombres_invalidos(name):
    assert isinstance(wbs.create_project("p", name), Err)


def test_limite_exacto_de_longitud_es_valido():
    assert isinstance(wbs.create_project("p", "x" * 80), Ok)


# ------------------------------------------------------------ EDT y tareas
def test_agregar_paquete_con_padre_inexistente(state):
    assert wbs.add_package(state, "k9", "Huérfano", parent_id="nope") == Err(NotFound("paquete padre", "nope"))


def test_agregar_tarea_a_paquete_inexistente(state):
    assert wbs.add_task(state, "t9", "X", "nope") == Err(NotFound("paquete", "nope"))


def test_agregar_tarea_con_responsable_inexistente(state):
    assert wbs.add_task(state, "t9", "X", "k1", assignee_id="nope") == Err(NotFound("integrante", "nope"))


def test_titulo_vacio_es_error_de_validacion(state):
    match wbs.add_task(state, "t9", "   ", "k1"):
        case Err(ValidationError(field, _)):
            assert "título" in field
        case other:
            pytest.fail(str(other))


def test_ids_duplicados(state):
    assert wbs.add_member(state, "m1", "Otro") == Err(Duplicate("integrante", "m1"))
    assert wbs.add_task(state, "t1", "Otra", "k1") == Err(Duplicate("tarea", "t1"))


def test_las_tareas_nuevas_nacen_pendientes(state):
    new = unwrap(wbs.add_task(state, "t9", "Nueva", "k1"))
    assert next(t for t in new.tasks if t.id == "t9").status == Status.PENDIENTE


# -------------------------------------------------------------- inmutabilidad
def test_el_estado_original_no_se_modifica(state):
    before = state
    unwrap(wbs.add_task(state, "t9", "Nueva", "k1"))
    unwrap(wbs.move_task(state, "t1", Status.EN_PROGRESO))
    assert state == before and len(state.tasks) == 3


def test_los_datos_del_dominio_son_inmutables(state):
    with pytest.raises(dataclasses.FrozenInstanceError):
        state.tasks[0].title = "cambiado"  # type: ignore[misc]


# ------------------------------------------------------------ cambios de tarea
def test_mover_tarea_y_rechazo_sin_cambios(state):
    moved = unwrap(wbs.move_task(state, "t1", Status.EN_PROGRESO))
    assert next(t for t in moved.tasks if t.id == "t1").status == Status.EN_PROGRESO
    assert wbs.move_task(state, "t1", Status.TERMINADA) == Err(InvalidTransition(Status.PENDIENTE, Status.TERMINADA))


def test_mover_tarea_inexistente(state):
    assert wbs.move_task(state, "zzz", Status.EN_PROGRESO) == Err(NotFound("tarea", "zzz"))


def test_asignar_y_desasignar(state):
    assigned = unwrap(wbs.assign_task(state, "t3", "m2"))
    assert next(t for t in assigned.tasks if t.id == "t3").assignee_id == "m2"
    cleared = unwrap(wbs.assign_task(assigned, "t3", None))
    assert next(t for t in cleared.tasks if t.id == "t3").assignee_id is None


def test_asignar_a_integrante_inexistente(state):
    assert wbs.assign_task(state, "t3", "nope") == Err(NotFound("integrante", "nope"))


def test_cambiar_prioridad(state):
    new = unwrap(wbs.set_priority(state, "t2", Priority.ALTA))
    assert next(t for t in new.tasks if t.id == "t2").priority == Priority.ALTA


# ------------------------------------------------------------------- comandos
def test_apply_despacha_cada_comando(state):
    s = unwrap(commands.apply(state, commands.AddMember("m3", "Eva")))
    s = unwrap(commands.apply(s, commands.AddPackage("k3", "Pruebas")))
    s = unwrap(commands.apply(s, commands.AddTask("t4", "Plan de pruebas", "k3", Priority.ALTA, "m3")))
    s = unwrap(commands.apply(s, commands.MoveTask("t4", Status.EN_PROGRESO)))
    s = unwrap(commands.apply(s, commands.AssignTask("t4", None)))
    s = unwrap(commands.apply(s, commands.SetPriority("t4", Priority.BAJA)))
    t4 = next(t for t in s.tasks if t.id == "t4")
    assert (t4.status, t4.assignee_id, t4.priority) == (Status.EN_PROGRESO, None, Priority.BAJA)


def test_apply_es_determinista(state):
    cmd = commands.MoveTask("t1", Status.EN_PROGRESO)
    assert commands.apply(state, cmd) == commands.apply(state, cmd)


def test_describe_produce_mensajes_legibles():
    assert "En progreso" in describe(InvalidTransition(Status.PENDIENTE, Status.EN_PROGRESO))
    assert "tarea" in describe(NotFound("tarea", "x"))
    assert describe(NotFound("paquete", "")) == "Debes elegir un paquete."
