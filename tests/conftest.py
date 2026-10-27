import pytest

from app.core import wbs
from app.core.result import Ok
from app.domain.models import Priority


def unwrap(result):
    """Ayuda de pruebas: extrae el valor de un Ok o falla con un mensaje claro."""
    assert isinstance(result, Ok), f"se esperaba Ok y llegó {result}"
    return result.value


@pytest.fixture
def state():
    """Proyecto con 2 integrantes, un paquete con subpaquete y 3 tareas."""
    s = unwrap(wbs.create_project("p1", "Proyecto demo"))
    s = unwrap(wbs.add_member(s, "m1", "Ana"))
    s = unwrap(wbs.add_member(s, "m2", "Luis"))
    s = unwrap(wbs.add_package(s, "k1", "Diseño"))
    s = unwrap(wbs.add_package(s, "k2", "Mockups", parent_id="k1"))
    s = unwrap(wbs.add_task(s, "t1", "Boceto", "k2", Priority.ALTA, "m1"))
    s = unwrap(wbs.add_task(s, "t2", "Paleta de colores", "k1", Priority.BAJA, "m2"))
    s = unwrap(wbs.add_task(s, "t3", "Revisión final", "k1", Priority.MEDIA, None))
    return s
