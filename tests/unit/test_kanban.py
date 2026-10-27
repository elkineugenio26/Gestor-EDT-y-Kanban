import pytest

from app.core import kanban
from app.core.errors import InvalidTransition
from app.core.result import Err, Ok
from app.domain.models import Status, Task


def make_task(status=Status.PENDIENTE):
    return Task("t", "Tarea", "k", status=status)


@pytest.mark.parametrize("current,requested", [
    (Status.PENDIENTE, Status.EN_PROGRESO),
    (Status.EN_PROGRESO, Status.EN_REVISION),
    (Status.EN_PROGRESO, Status.PENDIENTE),
    (Status.EN_REVISION, Status.TERMINADA),
    (Status.EN_REVISION, Status.EN_PROGRESO),
    (Status.TERMINADA, Status.EN_REVISION),
])
def test_transiciones_validas(current, requested):
    match kanban.change_status(make_task(current), requested):
        case Ok(task):
            assert task.status == requested
        case other:
            pytest.fail(f"se esperaba Ok, llegó {other}")


@pytest.mark.parametrize("current,requested", [
    (Status.PENDIENTE, Status.TERMINADA),       # salto de etapas
    (Status.PENDIENTE, Status.EN_REVISION),
    (Status.TERMINADA, Status.PENDIENTE),
    (Status.EN_PROGRESO, Status.TERMINADA),
    (Status.PENDIENTE, Status.PENDIENTE),       # límite: mismo estado
])
def test_transiciones_invalidas(current, requested):
    assert kanban.change_status(make_task(current), requested) == Err(InvalidTransition(current, requested))


def test_no_muta_la_tarea_original():
    original = make_task()
    kanban.change_status(original, Status.EN_PROGRESO)
    assert original.status == Status.PENDIENTE


def test_next_statuses_guia_a_la_ui():
    assert kanban.next_statuses(Status.EN_PROGRESO) == (Status.PENDIENTE, Status.EN_REVISION)
    assert kanban.next_statuses(Status.PENDIENTE) == (Status.EN_PROGRESO,)


def test_toda_columna_tiene_transiciones_definidas():
    assert set(kanban.ALLOWED_TRANSITIONS) == set(Status)
