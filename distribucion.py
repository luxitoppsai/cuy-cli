"""Rutas de recursos y datos para fuentes y aplicaciones empaquetadas."""

from pathlib import Path
import sys


def empaquetado() -> bool:
    """Indica si se ejecuta el programa distribuido con runtime incluido."""
    return bool(getattr(sys, "frozen", False))


def recursos() -> Path:
    """Devuelve los recursos de solo lectura incorporados a la aplicación."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def datos() -> Path:
    """Devuelve datos persistentes del usuario, separados del paquete instalado."""
    return Path.home() / ".local" / "share" / "cuy-cli" if empaquetado() else recursos()


def politica_entorno() -> None:
    """Aplica el presupuesto incorporado y elimina los antiguos overrides locales."""
    import os
    from politica import LIMITE_USD
    os.environ["CUY_LIMITE_USD"] = str(LIMITE_USD)
    os.environ["CUY_AVISO_PORCENTAJE"] = "80"
    if empaquetado():
        os.environ["CUY_GASTO"] = str(datos() / "gasto.json")
