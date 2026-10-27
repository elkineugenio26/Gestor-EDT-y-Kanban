"""Prueba de humo de la interfaz: maneja los componentes ReactPy como lo haría el navegador
(escribir en campos, elegir opciones, pulsar botones) sobre un SQLite en memoria.
No necesita navegador: usa el `Layout` de ReactPy y entrega los eventos directamente.
"""
import asyncio

from reactpy.core.layout import Layout

from app.adapters.sqlite_repository import SqliteProjectRepository
from app.shell.service import AppService
from app.ui.app import make_app


class Driver:
    def __init__(self, service):
        self.layout = Layout(make_app(service)())
        self.model = None

    async def __aenter__(self):
        await self.layout.__aenter__()
        self._pump = asyncio.create_task(self._pump_updates())
        await self.settle()
        return self

    async def __aexit__(self, *exc):
        self._pump.cancel()
        await self.layout.__aexit__(*exc)

    async def _pump_updates(self):
        while True:
            update = await self.layout.render()
            self._apply(update["path"], update["model"])

    def _apply(self, path, model):
        if not path:
            self.model = model
            return
        node = self.model
        tokens = path.strip("/").split("/")
        for tok in tokens[:-1]:
            node = node[int(tok)] if isinstance(node, list) else node[tok]
        last = tokens[-1]
        if isinstance(node, list):
            node[int(last)] = model
        else:
            node[last] = model

    async def settle(self):
        await asyncio.sleep(0.15)

    # ---- búsqueda en el árbol
    def _walk(self, node=None):
        node = self.model if node is None else node
        if isinstance(node, dict):
            yield node
            for child in node.get("children", []):
                yield from self._walk(child)

    def text(self, node=None):
        node = self.model if node is None else node
        if isinstance(node, str):
            return node
        if isinstance(node, dict):
            return "".join(self.text(c) for c in node.get("children", []))
        return ""

    def page_text(self):
        return self.text()

    def find(self, tag, **attrs):
        for n in self._walk():
            if n.get("tagName") == tag and all(n.get("attributes", {}).get(k) == v for k, v in attrs.items()):
                return n
        raise AssertionError(f"no se encontró <{tag}> con {attrs}")

    def buttons(self, text):
        return [n for n in self._walk() if n.get("tagName") == "button" and self.text(n) == text]

    # ---- acciones
    async def _fire(self, node, event, data):
        handler = node["eventHandlers"][event]
        await self.layout.deliver({"type": "layout-event", "target": handler["target"], "data": [data]})
        await self.settle()

    async def click(self, text, index=0):
        await self._fire(self.buttons(text)[index], "on_click", {})

    async def type(self, placeholder, value):
        await self._fire(self.find("input", placeholder=placeholder), "on_change", {"target": {"value": value}})

    async def choose(self, label, value):
        await self._fire(self.find("select", **{"aria-label": label}), "on_change", {"target": {"value": value}})


def run(coro):
    return asyncio.run(coro)


def test_flujo_completo_edt_kanban():
    async def scenario():
        service = AppService(SqliteProjectRepository(":memory:"))
        async with Driver(service) as ui:
            assert "Todavía no hay proyectos" in ui.page_text()

            # Dato inválido → mensaje comprensible, no se crea nada
            await ui.click("Crear proyecto")
            assert "no puede estar vacío" in ui.page_text()

            await ui.type("Nombre del proyecto", "Demo")
            await ui.click("Crear proyecto")
            assert "Proyecto «Demo» creado." in ui.page_text()
            assert "Este proyecto aún no tiene tareas." in ui.page_text()
            assert "Primero agrega un paquete" in ui.page_text()

            await ui.type("Nombre del integrante", "Ana")
            await ui.click("Agregar integrante")
            assert "Ana" in ui.page_text() and "0 pendientes" in ui.page_text()

            await ui.type("Nuevo entregable / paquete", "Backend")
            await ui.click("Agregar a la EDT")
            assert "Backend" in ui.page_text()

            await ui.type("Título de la tarea", "Crear API")
            await ui.click("Crear tarea")  # sin elegir paquete → error claro
            assert "Debes elegir un paquete." in ui.page_text()

            pkg_id = service.load(service.list_projects().value[0].id).value.packages[0].id
            await ui.choose("Paquete", pkg_id)
            await ui.click("Crear tarea")
            assert "Tarea creada." in ui.page_text()

            # La tarjeta Pendiente solo ofrece la transición válida
            assert len(ui.buttons("→ En progreso")) == 1
            assert not ui.buttons("→ Terminada")

            await ui.click("→ En progreso")
            assert "Tarea movida a «En progreso»." in ui.page_text()
            assert len(ui.buttons("→ En revisión")) == 1 and len(ui.buttons("→ Pendiente")) == 1

            # Persistió de verdad
            project_id = service.list_projects().value[0].id
            assert service.load(project_id).value.tasks[0].status.value == "En progreso"

            # Filtro sin resultados → estado vacío informativo
            await ui.choose("Filtrar por estado", "Terminada")
            assert "Ninguna tarea coincide con los filtros." in ui.page_text()
            await ui.click("Limpiar filtros")
            assert "Ninguna tarea coincide" not in ui.page_text()

    run(scenario())
