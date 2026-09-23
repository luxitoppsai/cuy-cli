"""Pruebas de la lógica pura de `generar_config.py`.

Solo se prueba lo que no toca la red: la estimación de tamaño y el armado de la
config. El descubrimiento contra un workspace real se valida corriendo el script.

Correr con::

    python3 -m unittest discover tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import generar_config as gc  # noqa: E402


class TamanoEstimado(unittest.TestCase):
    def test_ordena_las_familias_claude(self):
        """Es el orden que importa en el workspace del trabajo."""
        claude = ["databricks-claude-opus-4-1", "databricks-claude-haiku-4-5",
                  "databricks-claude-sonnet-4-5"]
        self.assertEqual(
            sorted(claude, key=gc._tamano_estimado),
            ["databricks-claude-haiku-4-5", "databricks-claude-sonnet-4-5",
             "databricks-claude-opus-4-1"],
        )

    def test_lee_la_cantidad_de_parametros(self):
        self.assertEqual(gc._tamano_estimado("databricks-meta-llama-3-1-8b-instruct"), 8)
        self.assertEqual(gc._tamano_estimado("databricks-gpt-oss-120b"), 120)

    def test_usa_el_total_y_no_los_parametros_activos(self):
        """'qwen35-122b-a10b' son 122B totales con 10B activos: manda el total."""
        self.assertEqual(gc._tamano_estimado("databricks-qwen35-122b-a10b"), 122)

    def test_desconocido_no_es_lo_mismo_que_chico(self):
        """Si el nombre no dice el tamaño, no debe terminar elegido como el barato."""
        desconocido = gc._tamano_estimado("databricks-llama-4-maverick")
        self.assertGreater(desconocido, gc._tamano_estimado("databricks-meta-llama-3-1-8b-instruct"))


class ConstruirConfig(unittest.TestCase):
    HOST = "https://ejemplo.cloud.databricks.com"

    def _config(self, detalles):
        endpoints = [{"name": n} for n in detalles]
        return gc.construir_config(self.HOST, endpoints, detalles)

    def test_descarta_los_que_devuelven_bloques(self):
        """Cuelgan al cliente OpenAI-compatible sin dar error: no deben entrar."""
        c = self._config({
            "databricks-gpt-oss-120b": {"forma": "bloques", "limite": 24000},
            "databricks-meta-llama-3-3-70b-instruct": {"forma": "string", "limite": 8192},
        })
        modelos = c["provider"]["databricks"]["models"]
        self.assertNotIn("databricks-gpt-oss-120b", modelos)
        self.assertIn("databricks-meta-llama-3-3-70b-instruct", modelos)

    def test_elige_principal_y_auxiliar_por_capacidad(self):
        c = self._config({
            "databricks-claude-opus-4-1": {"forma": "string", "limite": 32000},
            "databricks-claude-haiku-4-5": {"forma": "string", "limite": 8192},
        })
        self.assertEqual(c["model"], "databricks/databricks-claude-opus-4-1")
        self.assertEqual(c["small_model"], "databricks/databricks-claude-haiku-4-5")

    def test_declara_small_model_siempre(self):
        """Sin esto OpenCode apunta a un modelo del catálogo que no existe: 404 silencioso."""
        c = self._config({"databricks-gemma-3-12b": {"forma": "string", "limite": 8192}})
        self.assertIn("small_model", c)

    def test_el_limite_va_por_modelo(self):
        """Cada endpoint tiene su tope y el error no dice cuál es."""
        c = self._config({
            "databricks-qwen3-next-80b-a3b-instruct": {"forma": "string", "limite": 10000},
            "databricks-llama-4-maverick": {"forma": "string", "limite": 8192},
        })
        modelos = c["provider"]["databricks"]["models"]
        self.assertEqual(modelos["databricks-qwen3-next-80b-a3b-instruct"]["limit"]["output"], 10000)
        self.assertEqual(modelos["databricks-llama-4-maverick"]["limit"]["output"], 8192)

    def test_nunca_escribe_el_token(self):
        """La credencial se referencia por entorno; el archivo se versiona."""
        c = self._config({"databricks-gemma-3-12b": {"forma": "string", "limite": 8192}})
        self.assertEqual(c["provider"]["databricks"]["options"]["apiKey"], "{env:DATABRICKS_TOKEN}")

    def test_arma_bien_la_base_url(self):
        c = self._config({"databricks-gemma-3-12b": {"forma": "string", "limite": 8192}})
        self.assertEqual(
            c["provider"]["databricks"]["options"]["baseURL"],
            self.HOST + "/serving-endpoints",
        )


if __name__ == "__main__":
    unittest.main()
