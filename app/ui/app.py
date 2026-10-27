"""Componente raíz ReactPy (parte de la shell).

Cada evento sigue el mismo flujo:
    evento → `service.execute(comando)` → Ok: actualizar estado visual / Err: mostrar mensaje.
Las reglas viven en `app.core`; aquí NO hay `if` de negocio.
"""
from __future__ import annotations

from reactpy import component, html, use_state

from app.core import commands, queries
from app.core.errors import describe
from app.core.queries import UNASSIGNED, TaskFilter
from app.core.result import Err, Ok
from app.domain.models import Priority, Status
from app.shell.service import AppService, new_id
from app.ui import views


def _enum_or_none(enum_cls, raw: str):
    return enum_cls(raw) if raw else None


def make_app(service: AppService):
    """Fábrica: inyecta el servicio sin usar globales."""

    def initial_projects():
        match service.list_projects():
            case Ok(projects):
                return projects
            case Err():
                return ()

    @component
    def App():
        projects, set_projects = use_state(initial_projects)
        state, set_state = use_state(None)
        message, set_message = use_state(None)
        flt, set_flt = use_state(TaskFilter())

        def ok(text):
            set_message(("ok", text))

        def fail(error):
            set_message(("error", describe(error)))

        # ---------------------------------------------------------------- eventos
        def create_project(values) -> bool:
            match service.create_project(values["name"], values["description"]):
                case Err(e):
                    fail(e)
                    return False
                case Ok(new_state):
                    match service.list_projects():
                        case Ok(ps):
                            set_projects(ps)
                    set_state(new_state)
                    set_flt(TaskFilter())
                    ok(f"Proyecto «{new_state.project.name}» creado.")
                    return True

        def open_project(project_id: str):
            match service.load(project_id):
                case Err(e):
                    fail(e)
                case Ok(loaded):
                    set_state(loaded)
                    set_flt(TaskFilter())
                    set_message(None)

        def run(command, success_text: str) -> bool:
            if state is None:
                return False
            match service.execute(state.project.id, command):
                case Err(e):
                    fail(e)  # el estado visual NO cambia: coincide con lo guardado
                    return False
                case Ok(new_state):
                    set_state(new_state)
                    ok(success_text)
                    return True

        add_member = lambda v: run(commands.AddMember(new_id(), v["name"]), "Integrante agregado.")
        add_package = lambda name, parent: run(commands.AddPackage(new_id(), name, parent), "Paquete agregado a la EDT.")
        add_task = lambda title, pkg, prio, who: run(commands.AddTask(new_id(), title, pkg, prio, who), "Tarea creada.")
        move = lambda task_id, status: run(commands.MoveTask(task_id, status), f"Tarea movida a «{status.value}».")
        assign = lambda task_id, who: run(commands.AssignTask(task_id, who), "Responsable actualizado.")

        # ------------------------------------------------------- pantalla de inicio
        if state is None:
            return html.div(
                {"class": "app narrow"}, html.style(views.CSS),
                html.div({"class": "welcome"},
                         html.h1("Gestor de proyectos"),
                         html.p("Planifica el trabajo con una EDT y sigue su avance en un tablero Kanban.")),
                views.banner(message),
                html.div({"class": "panel p-kanban"}, html.h2("Crear proyecto"),
                         views.TextForm([("name", "Nombre del proyecto"), ("description", "Descripción (opcional)")],
                                        "Crear proyecto", create_project)),
                html.div({"class": "panel p-edt"}, html.h2("Proyectos guardados"),
                         *([html.button({"key": p.id, "class": "project-item",
                                         "on_click": lambda _e, pid=p.id: open_project(pid)},
                                        html.span(p.name)) for p in projects]
                           or [html.div({"class": "empty"}, "Todavía no hay proyectos. Crea el primero arriba.")])),
            )

        # ------------------------------------------------------ pantalla del proyecto
        outline = queries.wbs_outline(state.packages)
        package_names = {p.id: p.name for p in state.packages}
        per_package = {p.id: len(queries.filter_tasks(state.tasks, lambda t, pid=p.id: t.package_id == pid))
                       for p in state.packages}
        visible = queries.filter_tasks(state.tasks, queries.build_predicate(flt))
        columns = queries.board(visible)
        percent = queries.progress_percent(state.tasks)
        counts = queries.count_by_status(state.tasks)

        if not state.tasks:
            board_notice = html.div({"class": "notice"}, "Este proyecto aún no tiene tareas.")
        elif not visible:
            board_notice = html.div({"class": "notice"}, "Ninguna tarea coincide con los filtros.")
        else:
            board_notice = html.div()

        return html.div(
            {"class": "app"}, html.style(views.CSS),
            html.div(
                {"class": "band"},
                html.div({"class": "band-top"},
                         html.button({"class": "btn-light", "on_click": lambda _e: (set_state(None), set_message(None))},
                                     "← Proyectos"),
                         html.h1(state.project.name),
                         html.span({"class": "summary"}, f"{percent}% terminado · {len(state.tasks)} tareas")),
                html.p({"class": "desc"}, state.project.description) if state.project.description else html.div(),
                views.StatusMeter(counts),
            ),
            views.banner(message),
            html.div(
                {"class": "layout"},
                html.div(
                    html.div({"class": "panel p-team"}, html.h2("Equipo"),
                             views.MembersList(state.members, queries.pending_by_member(state)),
                             views.TextForm([("name", "Nombre del integrante")], "Agregar integrante", add_member,
                                            "btn-team")),
                    html.div({"class": "panel p-edt"}, html.h2("EDT: qué trabajo hay que hacer"),
                             views.WbsOutline(outline, per_package),
                             views.PackageForm(outline, add_package)),
                    html.div({"class": "panel p-task"}, html.h2("Nueva tarea"),
                             views.TaskForm(outline, state.members, add_task)),
                ),
                html.div(
                    {"class": "panel p-kanban"}, html.h2("Kanban: en qué estado está"),
                    html.div(
                        {"class": "filters"},
                        views.select(flt.status.value if flt.status else "",
                                     lambda v: set_flt(TaskFilter(_enum_or_none(Status, v), flt.assignee_id, flt.priority)),
                                     views.STATUS_FILTER, "Filtrar por estado"),
                        views.select(flt.assignee_id or "",
                                     lambda v: set_flt(TaskFilter(flt.status, v or None, flt.priority)),
                                     [("", "Todos los responsables"), (UNASSIGNED, "Sin responsable")]
                                     + [(m.id, m.name) for m in state.members], "Filtrar por responsable"),
                        views.select(flt.priority.value if flt.priority else "",
                                     lambda v: set_flt(TaskFilter(flt.status, flt.assignee_id, _enum_or_none(Priority, v))),
                                     views.PRIORITY_FILTER, "Filtrar por prioridad"),
                        html.button({"class": "btn-ghost", "on_click": lambda _e: set_flt(TaskFilter())},
                                    "Limpiar filtros"),
                    ),
                    board_notice,
                    views.Board(columns, package_names, state.members, move, assign),
                ),
            ),
        )

    return App