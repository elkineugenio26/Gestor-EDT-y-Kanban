"""Componentes ReactPy SIN lógica de negocio: reciben datos y callbacks por props.

Las reglas (transiciones, filtros, orden, conteos) se calculan en `app.core`;
aquí solo se dibujan resultados y se avisa de eventos.
"""
from __future__ import annotations

from reactpy import component, html, use_state

from app.core import kanban
from app.domain.models import Priority, Status

# Una clase CSS por estado: de ahí salen los colores del semáforo (columnas, barra, botones).
STATUS_CLASS = {
    Status.PENDIENTE: "pendiente",
    Status.EN_PROGRESO: "progreso",
    Status.EN_REVISION: "revision",
    Status.TERMINADA: "terminada",
}

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;700&family=Figtree:wght@400;500;600;700&display=swap');

:root {
  --pizarra: #d5dae1; --papel: #f7f8fa; --tinta: #1f2937; --suave: #5b6778; --linea: #c3cad5;
  --rojo: #e5484d; --ambar: #f5b700; --azul: #3b6fe0; --verde: #2ea66a;
  --indigo: #4357d9; --teal: #0e9f8e; --violeta: #7656d6; --naranja: #f0762c;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--pizarra); color: var(--tinta);
       font-family: Figtree, "Segoe UI", system-ui, sans-serif; font-size: 15px; line-height: 1.45; }
h1, h2, h3 { font-family: "Bricolage Grotesque", Figtree, "Segoe UI", sans-serif; margin: 0; }
.app { max-width: 1280px; margin: 0 auto; padding: 20px 20px 56px; }
.app.narrow { max-width: 640px; padding-top: 48px; }
.muted { color: var(--suave); font-size: 13px; }

/* ---------- Portada (centrada) ---------- */
.welcome { text-align: center; margin-bottom: 24px; }
.welcome h1 { font-size: 36px; letter-spacing: -0.02em; }
.welcome p { margin: 6px 0 0; color: var(--suave); }

/* ---------- Paneles: cada uno con su color ---------- */
.panel { --accent: var(--indigo); --accent-soft: #e0e5fb; --accent-ink: #2b3a9e;
         background: var(--papel); border-radius: 18px; border-top: 6px solid var(--accent);
         padding: 16px 18px 18px; margin-bottom: 16px; box-shadow: 0 2px 8px #1f293722; }
.panel h2 { font-size: 19px; margin-bottom: 12px; color: var(--accent-ink); }
.p-team { --accent: var(--teal); --accent-soft: #d3f2ee; --accent-ink: #0b6b60; }
.p-edt { --accent: var(--violeta); --accent-soft: #e9e3fb; --accent-ink: #4b35a8; }
.p-task { --accent: var(--naranja); --accent-soft: #fde6d6; --accent-ink: #9a3d08; }
.p-kanban { --accent: var(--indigo); --accent-soft: #e0e5fb; --accent-ink: #2b3a9e; }

/* ---------- Formularios ---------- */
.stack { display: flex; flex-direction: column; gap: 8px; }
.field-label { font-size: 13px; font-weight: 600; color: var(--suave); margin-bottom: -2px; }
input, select { font: inherit; color: var(--tinta); background: #fff; border: 1.5px solid var(--linea);
                border-radius: 10px; padding: 9px 12px; transition: border-color .15s, box-shadow .15s; }
.stack input, .stack select { width: 100%; }
input:focus, select:focus { outline: none; border-color: var(--accent, var(--indigo));
                            box-shadow: 0 0 0 3px #4357d933; }

/* ---------- Botones: el color lo da una variable ---------- */
button { font: inherit; font-weight: 600; cursor: pointer; border: 0; border-radius: 10px; padding: 9px 16px;
         background: var(--btn, var(--indigo)); color: var(--btn-ink, #fff);
         box-shadow: 0 2px 0 #00000026; transition: transform .12s, filter .12s, box-shadow .12s; }
button:hover { filter: brightness(1.08); transform: translateY(-1px); box-shadow: 0 5px 12px #1f293730; }
button:active { transform: translateY(1px); box-shadow: none; }
button:focus-visible, input:focus-visible, select:focus-visible { outline: 3px solid #4357d966; outline-offset: 2px; }
.btn-team { --btn: var(--teal); } .btn-edt { --btn: var(--violeta); } .btn-task { --btn: var(--naranja); }
.btn-ghost { --btn: #e3e7ee; --btn-ink: var(--tinta); box-shadow: none; }
.btn-light { --btn: #ffffff26; box-shadow: none; }
.btn-block { width: 100%; }
button.small { padding: 4px 11px; font-size: 12px; border-radius: 999px; margin: 2px 4px 0 0; box-shadow: none; }
.mv-pendiente { --btn: var(--rojo); } .mv-progreso { --btn: var(--ambar); --btn-ink: #3b2f00; }
.mv-revision { --btn: var(--azul); } .mv-terminada { --btn: var(--verde); }

/* ---------- Mensajes ---------- */
.msg { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-radius: 14px;
       margin: 0 0 16px; font-weight: 600; }
.msg .ico { flex: none; width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center;
            color: #fff; font-weight: 800; }
.msg.ok { background: #d6f3e3; color: #14532d; } .msg.ok .ico { background: var(--verde); }
.msg.error { background: #fde1e1; color: #7f1d1d; } .msg.error .ico { background: var(--rojo); }
.empty { color: var(--suave); font-size: 14px; }
.notice { margin: 0 0 12px; padding: 10px 14px; border-radius: 12px; background: #fff3c4; color: #5c4400; font-weight: 500; }

/* ---------- Banda del proyecto + barra segmentada ---------- */
.band { background: var(--tinta); color: #fff; border-radius: 20px; padding: 18px 24px 20px; margin-bottom: 18px; }
.band-top { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.band h1 { font-size: 30px; letter-spacing: -0.02em; }
.band .desc { margin: 4px 0 14px; color: #cbd5e1; }
.summary { margin-left: auto; font-weight: 600; background: #ffffff1f; border-radius: 999px; padding: 4px 14px; }
.meter { display: flex; gap: 2px; height: 16px; border-radius: 999px; overflow: hidden; background: #ffffff26; }
.meter .seg { height: 100%; transition: width .35s ease; }
.seg.pendiente, .dot.pendiente { background: var(--rojo); } .seg.progreso, .dot.progreso { background: var(--ambar); }
.seg.revision, .dot.revision { background: var(--azul); } .seg.terminada, .dot.terminada { background: var(--verde); }
.legend { display: flex; flex-wrap: wrap; gap: 6px 18px; margin-top: 10px; font-size: 13px; color: #e2e8f0; }
.legend .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }

/* ---------- Distribución ---------- */
.layout { display: grid; grid-template-columns: 320px minmax(0, 1fr); gap: 20px; align-items: start; }
.board { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.filters { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; background: #e6e9f5;
           border-radius: 14px; padding: 10px 12px; margin-bottom: 14px; }
.filters select { margin: 0; }

/* ---------- Columnas semáforo ---------- */
.col { --c: var(--rojo); --tint: #fde8e8; --c-ink: #fff; background: var(--tint);
       border-radius: 16px; padding: 10px; min-height: 160px; }
.col.pendiente { --c: var(--rojo); --tint: #fde8e8; --c-ink: #fff; }
.col.progreso { --c: var(--ambar); --tint: #fff3c4; --c-ink: #3b2f00; }
.col.revision { --c: var(--azul); --tint: #e0e9fc; --c-ink: #fff; }
.col.terminada { --c: var(--verde); --tint: #dcf3e6; --c-ink: #fff; }
.col h3 { display: flex; justify-content: space-between; align-items: center; font-size: 15px;
          background: var(--c); color: var(--c-ink); border-radius: 10px; padding: 7px 12px; margin-bottom: 10px; }
.count { background: #ffffff59; border-radius: 999px; padding: 0 10px; font-size: 13px; }
.col-empty { border: 2px dashed #1f293733; border-radius: 12px; padding: 18px 8px; text-align: center;
             color: var(--suave); font-size: 14px; }

/* ---------- Tarjetas ---------- */
.card { background: #fff; border-radius: 12px; border-left: 5px solid var(--c); padding: 12px;
        margin-bottom: 10px; box-shadow: 0 1px 3px #1f293726; transition: transform .15s, box-shadow .15s; }
.card:hover { transform: translateY(-2px); box-shadow: 0 6px 14px #1f293726; }
.card .title { font-weight: 700; margin-bottom: 6px; overflow-wrap: anywhere; }
.card .meta { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-bottom: 8px; }
.card select { width: 100%; margin: 0 0 8px; padding: 6px 10px; font-size: 14px; }
.chip { background: #ece8fb; color: #4b35a8; border-radius: 8px; padding: 2px 9px; font-size: 12px; font-weight: 600; }
.badge { border-radius: 999px; padding: 2px 10px; font-size: 12px; font-weight: 700; }
.badge.Alta { background: #c2255c; color: #fff; } .badge.Media { background: #f3a6c4; color: #5b1233; }
.badge.Baja { background: #e5e8ec; color: #475467; }

/* ---------- Equipo, EDT y proyectos ---------- */
.member { display: flex; align-items: center; gap: 10px; padding: 7px 0; border-bottom: 1px solid var(--linea); }
.member:last-of-type { border-bottom: 0; margin-bottom: 8px; }
.avatar { flex: none; width: 32px; height: 32px; border-radius: 50%; display: grid; place-items: center;
          color: #fff; font-weight: 700; }
.pill { margin-left: auto; border-radius: 999px; padding: 2px 10px; font-size: 12px; font-weight: 600;
        background: var(--accent-soft); color: var(--accent-ink); white-space: nowrap; }
.wbs-item { display: flex; align-items: center; gap: 8px; padding: 7px 10px; margin: 5px 0;
            background: var(--accent-soft); border-left: 4px solid var(--accent); border-radius: 10px; font-weight: 500; }
.wbs-list { margin-bottom: 10px; }
.project-item { --btn: #fff; --btn-ink: var(--tinta); display: flex; flex-direction: column; align-items: flex-start;
                width: 100%; text-align: left; border: 1.5px solid var(--linea); border-left: 6px solid var(--accent);
                margin-bottom: 8px; padding: 10px 14px; box-shadow: none; }

/* ---------- Adaptable ---------- */
@media (max-width: 1100px) { .board { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 960px) { .layout { grid-template-columns: 1fr; } }
@media (max-width: 600px) { .board { grid-template-columns: 1fr; } .band h1 { font-size: 24px; } }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
"""

AVATAR_COLORS = ("#0e9f8e", "#7656d6", "#f0762c", "#3b6fe0", "#c2255c", "#2ea66a")


def select(value: str, on_change, choices: list[tuple[str, str]], label: str | None = None):
    """<select> controlado. `choices` = [(valor, texto)]."""
    return html.select(
        {"value": value, "on_change": lambda e: on_change(e["target"]["value"]), "aria-label": label or ""},
        *[html.option({"value": v, "key": v}, text) for v, text in choices],
    )


def banner(message):
    if message is None:
        return html.div()
    kind, text = message
    return html.div(
        {"class": f"msg {kind}", "role": "status"},
        html.span({"class": "ico"}, "✓" if kind == "ok" else "!"),
        html.span(text),
    )


@component
def TextForm(fields: list[tuple[str, str]], submit_label: str, on_submit, button_class: str = ""):
    """Formulario genérico de campos de texto. `on_submit(valores) -> bool` (True = se guardó → limpiar)."""
    values, set_values = use_state({name: "" for name, _ in fields})

    def change(name):
        return lambda e: set_values({**values, name: e["target"]["value"]})

    def submit(_event):
        if on_submit(values):
            set_values({name: "" for name, _ in fields})

    return html.div(
        {"class": "stack"},
        *[html.input({"key": n, "placeholder": ph, "value": values[n], "on_change": change(n), "aria-label": ph})
          for n, ph in fields],
        html.button({"class": f"btn-block {button_class}", "on_click": submit}, submit_label),
    )


@component
def PackageForm(packages_outline, on_add):
    name, set_name = use_state("")
    parent, set_parent = use_state("")
    choices = [("", "(primer nivel)")] + [(p.id, "— " * d + p.name) for p, d in packages_outline]

    def submit(_e):
        if on_add(name, parent or None):
            set_name("")

    return html.div(
        {"class": "stack"},
        html.input({"placeholder": "Nuevo entregable / paquete", "value": name,
                    "on_change": lambda e: set_name(e["target"]["value"])}),
        html.div({"class": "field-label"}, "Dentro de:"),
        select(parent, set_parent, choices, "Paquete padre"),
        html.button({"class": "btn-block btn-edt", "on_click": submit}, "Agregar a la EDT"),
    )


@component
def TaskForm(packages_outline, members, on_add):
    title, set_title = use_state("")
    package, set_package = use_state("")
    priority, set_priority = use_state(Priority.MEDIA.value)
    assignee, set_assignee = use_state("")

    def submit(_e):
        if on_add(title, package, Priority(priority), assignee or None):
            set_title("")

    if not packages_outline:
        return html.div({"class": "empty"}, "Primero agrega un paquete a la EDT para poder crear tareas.")

    package_choices = [("", "Elegir paquete…")] + [(p.id, "— " * d + p.name) for p, d in packages_outline]
    return html.div(
        {"class": "stack"},
        html.input({"placeholder": "Título de la tarea", "value": title,
                    "on_change": lambda e: set_title(e["target"]["value"])}),
        select(package, set_package, package_choices, "Paquete"),
        select(priority, set_priority, [(p.value, f"Prioridad {p.value}") for p in Priority], "Prioridad"),
        select(assignee, set_assignee, [("", "Sin responsable")] + [(m.id, m.name) for m in members], "Responsable"),
        html.button({"class": "btn-block btn-task", "on_click": submit}, "Crear tarea"),
    )


@component
def WbsOutline(outline, tasks_per_package):
    if not outline:
        return html.div({"class": "empty", "style": {"marginBottom": "10px"}}, "La EDT está vacía.")
    return html.div(
        {"class": "wbs-list"},
        *[
            html.div(
                {"key": p.id, "class": "wbs-item", "style": {"marginLeft": f"{d * 16}px"}},
                html.span(p.name),
                html.span({"class": "pill"}, f"{(n := tasks_per_package.get(p.id, 0))} {'tarea' if n == 1 else 'tareas'}"),
            )
            for p, d in outline
        ],
    )


@component
def MembersList(members, pending):
    if not members:
        return html.div({"class": "empty", "style": {"marginBottom": "10px"}}, "Aún no hay integrantes.")
    return html.div(*[
        html.div(
            {"key": m.id, "class": "member"},
            html.span({"class": "avatar",
                       "style": {"background": AVATAR_COLORS[sum(map(ord, m.name)) % len(AVATAR_COLORS)]}},
                      m.name[:1].upper()),
            html.span(m.name),
            html.span({"class": "pill"}, f"{(n := pending.get(m.id, 0))} {'pendiente' if n == 1 else 'pendientes'}"),
        )
        for m in members
    ])


@component
def StatusMeter(counts):
    """Barra segmentada con la misma paleta de las columnas. `counts` viene de `queries.count_by_status`."""
    total = sum(counts.values())
    segments = [
        html.div({"key": s.value, "class": f"seg {STATUS_CLASS[s]}", "title": f"{s.value}: {n}",
                  "style": {"width": f"{100 * n / total:.2f}%"}})
        for s, n in counts.items() if n
    ]
    legend = [
        html.span({"key": s.value}, html.span({"class": f"dot {STATUS_CLASS[s]}"}), f"{s.value} {n}")
        for s, n in counts.items()
    ]
    return html.div(
        html.div({"class": "meter", "role": "img",
                  "aria-label": ", ".join(f"{s.value}: {n}" for s, n in counts.items())}, *segments),
        html.div({"class": "legend"}, *legend),
    )


@component
def Card(task, package_name, members, on_move, on_assign):
    return html.div(
        {"class": "card"},
        html.div({"class": "title"}, task.title),
        html.div({"class": "meta"},
                 html.span({"class": "chip"}, package_name),
                 html.span({"class": f"badge {task.priority.value}"}, task.priority.value)),
        select(task.assignee_id or "", lambda v: on_assign(task.id, v or None),
               [("", "Sin responsable")] + [(m.id, m.name) for m in members], "Responsable"),
        html.div(*[  # solo se ofrecen las transiciones que la regla Kanban permite
            html.button({"key": s.value, "class": f"small mv-{STATUS_CLASS[s]}",
                         "on_click": lambda _e, s=s: on_move(task.id, s)},
                        f"→ {s.value}")
            for s in kanban.next_statuses(task.status)
        ]),
    )


@component
def Board(columns, package_names, members, on_move, on_assign):
    return html.div(
        {"class": "board"},
        *[
            html.div(
                {"key": status.value, "class": f"col {STATUS_CLASS[status]}"},
                html.h3(status.value, html.span({"class": "count"}, str(len(tasks)))),
                *([Card(t, package_names.get(t.package_id, "?"), members, on_move, on_assign, key=t.id) for t in tasks]
                  or [html.div({"class": "col-empty"}, "Sin tareas")]),
            )
            for status, tasks in columns.items()
        ],
    )


STATUS_FILTER = [("", "Todos los estados")] + [(s.value, s.value) for s in Status]
PRIORITY_FILTER = [("", "Todas las prioridades")] + [(p.value, p.value) for p in Priority]