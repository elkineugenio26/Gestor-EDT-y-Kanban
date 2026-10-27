import logging

from app.core import validation
from app.core.errors import ValidationError
from app.core.result import Err, Ok
from app.shell.decorators import logged


def test_validadores_se_componen():
    v = validation.all_validators(validation.non_empty("n"), validation.max_length("n", 3))
    assert v("  ab ") == Ok("ab")
    assert v("   ") == Err(ValidationError("n", "no puede estar vacío"))
    assert v("abcd") == Err(ValidationError("n", "no puede superar 3 caracteres"))


def test_decorador_conserva_resultado_y_metadatos(caplog):
    @logged("operación demo")
    def suma(a, b):
        """Suma dos números."""
        return Ok(a + b)

    with caplog.at_level(logging.INFO, logger="gestor"):
        assert suma(1, 2) == Ok(3)  # el decorador no altera el resultado
    assert suma.__name__ == "suma" and suma.__doc__ == "Suma dos números."
    assert "operación demo: ok" in caplog.text


def test_decorador_registra_los_errores(caplog):
    @logged("falla")
    def falla():
        return Err("boom")

    with caplog.at_level(logging.WARNING, logger="gestor"):
        assert falla() == Err("boom")
    assert "falla: error boom" in caplog.text
