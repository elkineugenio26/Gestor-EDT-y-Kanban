import pytest

from app.core import queries
from app.core.errors import NotFound
from app.core.queries import TaskFilter, UNASSIGNED
from app.core.result import Err, Ok
from app.domain.models import Priority, Status, Task
from tests.conftest import unwrap
from app.core import wbs


def ids(tasks):
    return [t.id for t in tasks]


# --------------------------------------------------------------- ausencia de valor
def test_find_devuelve_none_cuando_no_existe(state):
    assert queries.find_task(state, "zzz") is None
    assert queries.find_member(state, "zzz") is None
    assert queries.find_package(state, "zzz") is None


def test_require_convierte_none_en_notfound(state):
    assert queries.require("tarea", "zzz", state.tasks) == Err(NotFound("tarea", "zzz"))
    assert isinstance(queries.require("tarea", "t1", state.tasks), Ok)


def test_proyecto_sin_tareas_es_valido_y_distinto_de_no_existe():
    empty = unwrap(wbs.create_project("p", "Vacío"))
    assert queries.board(empty.tasks)[Status.PENDIENTE] == ()  # vacío ≠ inexistente


# ---------------------------------------------------------------------- filtros
def test_filtrar_por_estado_responsable_y_prioridad(state):
    state = unwrap(wbs.move_task(state, "t1", Status.EN_PROGRESO))
    f = lambda **kw: ids(queries.filter_tasks(state.tasks, queries.build_predicate(TaskFilter(**kw))))
    assert f(status=Status.EN_PROGRESO) == ["t1"]
    assert f(assignee_id="m2") == ["t2"]
    assert f(priority=Priority.MEDIA) == ["t3"]
    assert f(assignee_id=UNASSIGNED) == ["t3"]


def test_sin_filtros_devuelve_todo_y_combinados_usan_and(state):
    assert len(queries.filter_tasks(state.tasks, queries.build_predicate(TaskFilter()))) == 3
    combined = queries.build_predicate(TaskFilter(assignee_id="m1", priority=Priority.BAJA))
    assert queries.filter_tasks(state.tasks, combined) == ()  # sin resultados: tupla vacía


def test_closure_captura_su_criterio(state):
    de_ana = queries.by_assignee("m1")
    de_luis = queries.by_assignee("m2")
    assert ids(queries.filter_tasks(state.tasks, de_ana)) == ["t1"]
    assert ids(queries.filter_tasks(state.tasks, de_luis)) == ["t2"]  # cada closure conserva el suyo


def test_all_of_sin_predicados_acepta_todo(state):
    assert queries.all_of()(state.tasks[0]) is True


# ------------------------------------------------------------------------ orden
def test_orden_por_prioridad_y_luego_titulo(state):
    ordered = queries.sort_tasks(state.tasks, queries.priority_then_title)
    assert ids(ordered) == ["t1", "t3", "t2"]  # Alta, Media, Baja


def test_orden_con_lambda_por_titulo(state):
    assert ids(queries.sort_tasks(state.tasks, queries.by_title_key)) == ["t1", "t2", "t3"]


def test_desempate_alfabetico_ignora_mayusculas():
    a, b = Task("a", "beta", "k", Priority.ALTA), Task("b", "Alfa", "k", Priority.ALTA)
    assert ids(queries.sort_tasks([a, b], queries.priority_then_title)) == ["b", "a"]


# --------------------------------------------------------------------- tablero
def test_tablero_siempre_tiene_las_cuatro_columnas(state):
    board = queries.board(state.tasks)
    assert list(board) == list(Status)
    assert ids(board[Status.PENDIENTE]) == ["t1", "t3", "t2"]
    assert board[Status.TERMINADA] == ()


def test_tablero_refleja_el_estado_actual(state):
    state = unwrap(wbs.move_task(state, "t1", Status.EN_PROGRESO))
    board = queries.board(state.tasks)
    assert ids(board[Status.EN_PROGRESO]) == ["t1"]
    assert "t1" not in ids(board[Status.PENDIENTE])


# ------------------------------------------------------- pendientes y progreso
def test_pendientes_por_integrante(state):
    assert queries.pending_by_member(state) == {"m1": 1, "m2": 1, UNASSIGNED: 1}


def test_terminadas_no_cuentan_como_pendientes(state):
    for status in (Status.EN_PROGRESO, Status.EN_REVISION, Status.TERMINADA):
        state = unwrap(wbs.move_task(state, "t1", status))
    assert queries.pending_by_member(state)["m1"] == 0  # integrante sin pendientes sigue apareciendo


@pytest.mark.parametrize("n_done,expected", [(0, 0), (1, 33), (3, 100)])
def test_porcentaje_de_avance(n_done, expected):
    tasks = tuple(
        Task(str(i), "t", "k", status=Status.TERMINADA if i < n_done else Status.PENDIENTE) for i in range(3)
    )
    assert queries.progress_percent(tasks) == expected


def test_avance_sin_tareas_es_cero():
    assert queries.progress_percent(()) == 0


# -------------------------------------------------------------------------- EDT
def test_esquema_de_la_edt_respeta_jerarquia(state):
    outline = [(p.id, depth) for p, depth in queries.wbs_outline(state.packages)]
    assert outline == [("k1", 0), ("k2", 1)]


def test_conteo_por_estado_incluye_las_cuatro_claves(state):
    state = unwrap(wbs.move_task(state, "t1", Status.EN_PROGRESO))
    assert queries.count_by_status(state.tasks) == {
        Status.PENDIENTE: 2, Status.EN_PROGRESO: 1, Status.EN_REVISION: 0, Status.TERMINADA: 0,
    }
    assert sum(queries.count_by_status(()).values()) == 0