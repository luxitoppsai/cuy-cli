"""Tests del paso de descubrimiento del instalador.

Esta función solo se ejecuta contra un workspace vivo, así que nunca se recorría en
seco: un ``NameError`` —una referencia a ``PROVEEDOR`` sin el prefijo del módulo—
sobrevivió a toda la suite y reventó recién en la máquina del trabajo, a mitad de la
instalación. Los tests de acá reemplazan las tres llamadas de red por datos fijos para
que el camino se recorra entero sin workspace.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import instalar  # noqa: E402
import generar_config as gc  # noqa: E402

HOST = "https://ejemplo.cloud.databricks.com"

ENDPOINTS = [
    {"name": "databricks-claude-sonnet-4", "task": "llm/v1/chat"},
    {"name": "databricks-claude-haiku-4-5", "task": "llm/v1/chat"},
]


def _fingir(formas):
    """Reemplaza las tres llamadas de red por respuestas fijas.

    :param formas: Forma de respuesta por endpoint (``"texto"`` o ``"bloques"``).
    :returns: Un context manager que aplica los tres parches.
    """
    return mock.patch.multiple(
        instalar.gc,
        listar_endpoints=mock.Mock(return_value=ENDPOINTS),
        detectar_forma=mock.Mock(side_effect=lambda h, t, n: formas[n]),
        sondear_limite=mock.Mock(return_value=8192),
        # Sin fingirlo, el test sale a la red de verdad contra un host inventado.
        detectar_anthropic=mock.Mock(return_value=None),
    )


class Generar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # Sin esto se pisaría el opencode.json real del repo.
        destino = Path(self.tmp.name) / "opencode.json"
        parche = mock.patch.object(instalar, "CONFIG", destino)
        parche.start()
        self.addCleanup(parche.stop)
        self.destino = destino

    def test_escribe_la_config_cuando_hay_endpoints_usables(self):
        formas = {e["name"]: "texto" for e in ENDPOINTS}
        with _fingir(formas):
            config = instalar.generar(HOST, "token-falso", rapido=True)

        self.assertTrue(self.destino.exists())
        escrito = json.loads(self.destino.read_text())
        self.assertEqual(escrito, config)
        self.assertEqual(
            sorted(config["provider"][gc.PROVEEDOR]["models"]),
            sorted(e["name"] for e in ENDPOINTS),
        )

    def test_aborta_si_todos_los_endpoints_devuelven_bloques(self):
        formas = {e["name"]: "bloques" for e in ENDPOINTS}
        with _fingir(formas), self.assertRaises(SystemExit):
            instalar.generar(HOST, "token-falso", rapido=True)
        self.assertFalse(self.destino.exists())

    def test_descarta_solo_el_endpoint_que_devuelve_bloques(self):
        formas = {"databricks-claude-sonnet-4": "texto",
                  "databricks-claude-haiku-4-5": "bloques"}
        with _fingir(formas):
            config = instalar.generar(HOST, "token-falso", rapido=True)

        self.assertEqual(
            config["provider"][gc.PROVEEDOR]["models"],
            {"databricks-claude-sonnet-4": mock.ANY},
        )


if __name__ == "__main__":
    unittest.main()
