"""Garantiza que la separación núcleo/infraestructura sea REAL: el núcleo no importa infraestructura."""
import ast
from pathlib import Path

FORBIDDEN = {"reactpy", "fastapi", "starlette", "uvicorn", "sqlite3", "os", "pathlib", "uuid",
             "random", "time", "datetime", "logging", "app.adapters", "app.ui", "app.shell"}
PURE_DIRS = ["app/domain", "app/core"]


def imported_modules(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_el_nucleo_no_importa_infraestructura():
    root = Path(__file__).resolve().parents[2]
    offenders = []
    for folder in PURE_DIRS:
        for file in (root / folder).glob("*.py"):
            for module in imported_modules(file):
                if any(module == f or module.startswith(f + ".") for f in FORBIDDEN):
                    offenders.append(f"{file.relative_to(root)} importa {module}")
    assert not offenders, offenders
