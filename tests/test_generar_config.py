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
        modelos = c["provider"][gc.PROVEEDOR]["models"]
        self.assertNotIn("databricks-gpt-oss-120b", modelos)
        self.assertIn("databricks-meta-llama-3-3-70b-instruct", modelos)

    def test_elige_principal_y_auxiliar_por_capacidad(self):
        c = self._config({
            "databricks-claude-opus-4-1": {"forma": "string", "limite": 32000},
            "databricks-claude-haiku-4-5": {"forma": "string", "limite": 8192},
        })
        self.assertEqual(c["model"], f"{gc.PROVEEDOR}/databricks-claude-opus-4-1")
        self.assertEqual(c["small_model"], f"{gc.PROVEEDOR}/databricks-claude-haiku-4-5")

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
        modelos = c["provider"][gc.PROVEEDOR]["models"]
        self.assertEqual(modelos["databricks-qwen3-next-80b-a3b-instruct"]["limit"]["output"], 10000)
        self.assertEqual(modelos["databricks-llama-4-maverick"]["limit"]["output"], 8192)

    def test_nunca_escribe_el_token(self):
        """La credencial se referencia por entorno; el archivo se versiona."""
        c = self._config({"databricks-gemma-3-12b": {"forma": "string", "limite": 8192}})
        self.assertEqual(c["provider"][gc.PROVEEDOR]["options"]["apiKey"], "{env:DATABRICKS_TOKEN}")

    def test_arma_bien_la_base_url(self):
        c = self._config({"databricks-gemma-3-12b": {"forma": "string", "limite": 8192}})
        self.assertEqual(
            c["provider"][gc.PROVEEDOR]["options"]["baseURL"],
            self.HOST + "/serving-endpoints",
        )



class RuteoPorRol(unittest.TestCase):
    """D3 del RFC: cada rol usa el modelo que le corresponde, sin tocar el harness."""

    def test_ejecutar_usa_sonnet_y_planificar_haiku(self):
        """Opus queda fuera de los roles: se elige a mano cuando la tarea lo pide."""
        agentes = gc.construir_agentes([
            "databricks-claude-haiku-4-5",
            "databricks-claude-sonnet-4-5",
            "databricks-claude-opus-4-1",
        ])
        self.assertEqual(agentes["build"]["model"], f"{gc.PROVEEDOR}/databricks-claude-sonnet-4-5")
        self.assertEqual(agentes["plan"]["model"], f"{gc.PROVEEDOR}/databricks-claude-haiku-4-5")

    def test_los_subagentes_de_lectura_usan_el_barato(self):
        agentes = gc.construir_agentes(["databricks-gemma-3-12b", "databricks-gpt-oss-120b"])
        for rol in ("explore", "scout"):
            self.assertEqual(agentes[rol]["model"], f"{gc.PROVEEDOR}/databricks-gemma-3-12b")

    def test_con_un_solo_modelo_no_rutea(self):
        """Repartir roles entre un único modelo no aporta nada."""
        self.assertEqual(gc.construir_agentes(["databricks-gemma-3-12b"]), {})

if __name__ == "__main__":
    unittest.main()


class PreferenciasDeModelo(unittest.TestCase):
    """Sonnet de principal y Haiku de auxiliar; Opus queda para elegirlo a mano."""

    CLAUDE = [
        "databricks-claude-opus-4-1",
        "databricks-claude-opus-4-5",
        "databricks-claude-sonnet-4",
        "databricks-claude-haiku-4-5",
    ]

    def _config(self, nombres, limite=64000):
        detalles = {n: {"forma": "string", "limite": limite} for n in nombres}
        return gc.construir_config("https://x", [{"name": n} for n in nombres], detalles)

    def test_sonnet_es_el_principal_aunque_opus_sea_mas_capaz(self):
        c = self._config(self.CLAUDE)
        self.assertIn("sonnet", c["model"])
        self.assertNotIn("opus", c["model"])

    def test_haiku_es_el_auxiliar(self):
        c = self._config(self.CLAUDE)
        self.assertIn("haiku", c["small_model"])

    def test_opus_queda_disponible_para_elegirlo(self):
        """No se usa por defecto, pero tiene que estar en la lista."""
        c = self._config(self.CLAUDE)
        modelos = c["provider"][gc.PROVEEDOR]["models"]
        self.assertIn("databricks-claude-opus-4-1", modelos)

    def test_ningun_rol_usa_opus_por_defecto(self):
        c = self._config(self.CLAUDE)
        for rol, cfg in c.get("agent", {}).items():
            self.assertNotIn("opus", cfg["model"], f"el rol {rol} no debería usar Opus")

    def test_sin_claude_se_elige_por_tamano(self):
        """En un workspace de pesos abiertos las preferencias no aplican."""
        c = self._config([
            "databricks-qwen3-next-80b-a3b-instruct",
            "databricks-meta-llama-3-1-8b-instruct",
        ], limite=8000)
        self.assertIn("80b", c["model"])
        self.assertIn("8b", c["small_model"])

    def test_elige_la_version_mas_nueva_de_la_familia(self):
        c = self._config(["databricks-claude-sonnet-4", "databricks-claude-sonnet-4-5"])
        self.assertEqual(c["model"], f"{gc.PROVEEDOR}/databricks-claude-sonnet-4-5")
