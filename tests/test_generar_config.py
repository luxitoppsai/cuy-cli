"""Pruebas de la lógica pura de `generar_config.py`.

Solo se prueba lo que no toca la red: la estimación de tamaño y el armado de la
config. El descubrimiento contra un workspace real se valida corriendo el script.

Correr con::

    python3 -m unittest discover tests
"""

import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

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



def _ref(endpoint):
    """Traduce endpoint a `proveedor/modelo` como lo hace construir_config."""
    return f"{gc.PROVEEDOR}/{endpoint}"


class RuteoPorRol(unittest.TestCase):
    """D3 del RFC: cada rol usa el modelo que le corresponde, sin tocar el harness."""

    def test_ejecutar_y_planificar_usan_sonnet(self):
        """Opus queda fuera de los roles: se elige a mano cuando la tarea lo pide."""
        agentes = gc.construir_agentes([
            "databricks-claude-haiku-4-5",
            "databricks-claude-sonnet-4-5",
            "databricks-claude-opus-4-1",
        ], _ref)
        self.assertEqual(agentes["build"]["model"], f"{gc.PROVEEDOR}/databricks-claude-sonnet-4-5")
        self.assertEqual(agentes["plan"]["model"], f"{gc.PROVEEDOR}/databricks-claude-sonnet-4-5")

    def test_los_subagentes_de_lectura_usan_el_barato(self):
        agentes = gc.construir_agentes(["databricks-gemma-3-12b", "databricks-gpt-oss-120b"], _ref)
        for rol in ("explore",):
            self.assertEqual(agentes[rol]["model"], f"{gc.PROVEEDOR}/databricks-gemma-3-12b")

    def test_con_un_solo_modelo_conserva_restricciones(self):
        """Los permisos siguen aplicándose aunque solo haya un modelo."""
        self.assertEqual(gc.construir_agentes(["databricks-gemma-3-12b"], _ref)["plan"]["permission"]["*"], "deny")

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


class TarifaUsd(unittest.TestCase):
    """La tarifa que se declara en `opencode.json` para que OpenCode muestre el gasto.

    Antes este cálculo vivía en el plugin de presupuesto y se hacía a mano. Ahora se
    declara una vez y OpenCode calcula: estas pruebas son las que se mudaron de
    `presupuesto.test.mjs`.
    """

    def test_las_tarifas_de_claude_son_las_reales_de_databricks(self):
        # A $0.07/DBU: Haiku $1/$5, Sonnet $3/$15, Opus $5/$25 por millón.
        self.assertEqual(gc.tarifa_usd("databricks-claude-haiku-4-5"),
                         {"input": 1.0, "output": 5.0})
        self.assertEqual(gc.tarifa_usd("databricks-claude-sonnet-4"),
                         {"input": 3.0, "output": 15.0})
        self.assertEqual(gc.tarifa_usd("databricks-claude-opus-4-1"),
                         {"input": 5.0, "output": 25.0})

    def test_opus_no_cuesta_lo_que_la_lista_de_anthropic(self):
        """Databricks lo factura a un tercio: $25 la salida, no $75."""
        self.assertLess(gc.tarifa_usd("databricks-claude-opus-4-1")["output"], 30)

    def test_la_clave_mas_especifica_gana(self):
        """'llama-3-1-8b' no debe caer en una coincidencia más corta."""
        self.assertEqual(gc.tarifa_usd("databricks-meta-llama-3-1-8b-instruct"),
                         gc.tarifa_usd("llama-3-1-8b"))

    def test_un_modelo_desconocido_no_tiene_tarifa(self):
        """Preferible a inventar un número."""
        self.assertIsNone(gc.tarifa_usd("databricks-gemma-3-12b"))

    def test_otro_dolar_por_dbu_cambia_el_costo_proporcionalmente(self):
        normal = gc.tarifa_usd("databricks-claude-sonnet-4", 0.07)
        doble = gc.tarifa_usd("databricks-claude-sonnet-4", 0.14)
        self.assertAlmostEqual(doble["input"], normal["input"] * 2, places=4)

    def test_la_config_declara_el_costo_de_cada_modelo_conocido(self):
        """Sin `cost`, OpenCode calcula cero y la TUI no muestra el gasto."""
        c = gc.construir_config(
            "https://ejemplo.cloud.databricks.com",
            [{"name": "databricks-claude-sonnet-4"}, {"name": "databricks-gemma-3-12b"}],
            {"databricks-claude-sonnet-4": {"forma": "string", "limite": 8192},
             "databricks-gemma-3-12b": {"forma": "string", "limite": 8192}},
        )
        modelos = c["provider"][gc.PROVEEDOR]["models"]
        self.assertEqual(modelos["databricks-claude-sonnet-4"]["cost"],
                         {"input": 3.0, "output": 15.0})
        # El desconocido se queda sin `cost` en vez de con un precio inventado.
        self.assertNotIn("cost", modelos["databricks-gemma-3-12b"])


class DetectarForma(unittest.TestCase):
    """El sondeo que decide si un endpoint entra en la config.

    La primera versión preguntaba "di: ok" sin streaming. Sonnet 4.5 pasaba y después
    reventaba en la primera tarea real con ``expected string, received array``: el
    razonamiento llega como lista dentro de ``delta.content``, y solo aparece cuando el
    modelo de verdad razona y en el camino de streaming.
    """

    HOST = "https://ejemplo.cloud.databricks.com"

    def _respuesta_sse(self, fragmentos):
        """Simula una respuesta SSE como la devuelve Databricks."""
        lineas = [f"data: {json.dumps(f)}\n".encode() for f in fragmentos]
        lineas.append(b"data: [DONE]\n")
        respuesta = io.BytesIO(b"".join(lineas))
        respuesta.status = 200
        respuesta.__enter__ = lambda s: s
        respuesta.__exit__ = lambda s, *a: None
        return respuesta

    def _detectar(self, fragmentos):
        with mock.patch.object(gc.urllib.request, "urlopen",
                               return_value=self._respuesta_sse(fragmentos)):
            return gc.detectar_forma(self.HOST, "t", "un-endpoint")

    def test_detecta_bloques_en_el_stream(self):
        """El caso que se escapó: el razonamiento llega como lista."""
        forma = self._detectar([
            {"choices": [{"delta": {"role": "assistant", "content": [
                {"type": "reasoning_summary", "summary": [{"type": "summary_text", "text": "..."}]}
            ]}}]},
        ])
        self.assertEqual(forma, "bloques")

    def test_acepta_el_stream_de_texto(self):
        forma = self._detectar([
            {"choices": [{"delta": {"role": "assistant", "content": "El primero"}}]},
            {"choices": [{"delta": {"content": " llega antes."}}]},
        ])
        self.assertEqual(forma, "string")

    def test_un_bloque_tardio_tambien_descarta(self):
        """Empieza bien y razona después: igual hay que descartarlo."""
        forma = self._detectar([
            {"choices": [{"delta": {"content": "Veamos"}}]},
            {"choices": [{"delta": {"content": [{"type": "reasoning_summary"}]}}]},
        ])
        self.assertEqual(forma, "bloques")

    def test_la_pregunta_sonda_da_trabajo(self):
        """Con un saludo trivial el modelo contesta directo y nunca razona."""
        self.assertGreater(len(gc.PREGUNTA_SONDA), 60)



class ViaNativaDeAnthropic(unittest.TestCase):
    """Claude por su API Messages en vez del contrato OpenAI.

    Es lo que evita `Invalid input: expected string, received array`: Sonnet 4.5 manda
    el razonamiento como lista de bloques, que por la vía nativa es contrato válido y
    por la compatible es un error del que el cliente no se recupera.
    """

    HOST = "https://ejemplo.cloud.databricks.com"

    def _config(self, detalles, anthropic):
        endpoints = [{"name": n} for n in detalles]
        return gc.construir_config(self.HOST, endpoints, detalles, anthropic)

    def _solo_claude(self, auth="bearer"):
        nombres = ["databricks-claude-sonnet-4-5", "databricks-claude-haiku-4-5"]
        detalles = {n: {"forma": "nativa", "limite": 8192} for n in nombres}
        anthropic = {"auth": auth, "cabeceras": {},
                     "modelos": {n: n.removeprefix("databricks-") for n in nombres}}
        return self._config(detalles, anthropic)

    def test_claude_va_por_el_proveedor_nativo(self):
        c = self._solo_claude()
        self.assertEqual(list(c["provider"]), [gc.PROVEEDOR_CLAUDE])
        proveedor = c["provider"][gc.PROVEEDOR_CLAUDE]
        self.assertEqual(proveedor["npm"], "@ai-sdk/anthropic")
        self.assertTrue(proveedor["options"]["baseURL"].endswith(gc.RUTA_ANTHROPIC))

    def test_usa_el_nombre_de_anthropic_no_el_del_endpoint(self):
        """El passthrough no conoce `databricks-claude-sonnet-4-5`."""
        c = self._solo_claude()
        self.assertIn("claude-sonnet-4-5", c["provider"][gc.PROVEEDOR_CLAUDE]["models"])
        self.assertEqual(c["model"], f"{gc.PROVEEDOR_CLAUDE}/claude-sonnet-4-5")

    def test_inyecta_bearer_solo_cuando_hace_falta(self):
        """El SDK manda x-api-key; si el workspace quiere Bearer, se agrega la cabecera."""
        con_bearer = self._solo_claude("bearer")["provider"][gc.PROVEEDOR_CLAUDE]["options"]
        self.assertEqual(con_bearer["headers"]["Authorization"], "Bearer {env:DATABRICKS_TOKEN}")
        con_clave = self._solo_claude("x-api-key")["provider"][gc.PROVEEDOR_CLAUDE]["options"]
        self.assertNotIn("headers", con_clave)

    def test_los_roles_apuntan_al_proveedor_nativo(self):
        agentes = self._solo_claude()["agent"]
        for rol in ("build", "plan", "explore"):
            self.assertTrue(agentes[rol]["model"].startswith(gc.PROVEEDOR_CLAUDE + "/"))

    def test_un_workspace_mixto_usa_los_dos_proveedores(self):
        detalles = {
            "databricks-claude-sonnet-4-5": {"forma": "nativa", "limite": 8192},
            "databricks-meta-llama-3-1-8b-instruct": {"forma": "string", "limite": 8192},
        }
        anthropic = {"auth": "bearer", "cabeceras": {},
                     "modelos": {"databricks-claude-sonnet-4-5": "claude-sonnet-4-5"}}
        c = self._config(detalles, anthropic)
        self.assertEqual(sorted(c["provider"]), sorted([gc.PROVEEDOR, gc.PROVEEDOR_CLAUDE]))
        self.assertEqual(c["enabled_providers"], list(c["provider"]))
        self.assertIn("databricks-meta-llama-3-1-8b-instruct",
                      c["provider"][gc.PROVEEDOR]["models"])

    def test_sin_via_nativa_todo_sigue_como_antes(self):
        detalles = {"databricks-claude-sonnet-4-5": {"forma": "string", "limite": 8192},
                    "databricks-claude-haiku-4-5": {"forma": "string", "limite": 8192}}
        c = self._config(detalles, None)
        self.assertEqual(list(c["provider"]), [gc.PROVEEDOR])
        self.assertEqual(c["model"], f"{gc.PROVEEDOR}/databricks-claude-sonnet-4-5")

    def test_el_filtro_de_bloques_no_aplica_a_la_via_nativa(self):
        """Por la nativa los bloques son contrato, no un defecto: no debe descartarse."""
        detalles = {"databricks-claude-sonnet-4-5": {"forma": "bloques", "limite": 8192}}
        anthropic = {"auth": "bearer", "cabeceras": {},
                     "modelos": {"databricks-claude-sonnet-4-5": "claude-sonnet-4-5"}}
        c = self._config(detalles, anthropic)
        self.assertIn("claude-sonnet-4-5", c["provider"][gc.PROVEEDOR_CLAUDE]["models"])

    def test_prueba_el_nombre_de_anthropic_antes_que_el_del_endpoint(self):
        self.assertEqual(gc.nombres_anthropic("databricks-claude-opus-4-1"),
                         ["claude-opus-4-1", "databricks-claude-opus-4-1"])

    def test_reconoce_los_endpoints_de_claude(self):
        self.assertTrue(gc.es_claude("databricks-claude-sonnet-4-5"))
        self.assertFalse(gc.es_claude("databricks-meta-llama-3-1-8b-instruct"))



class VentanaDeContexto(unittest.TestCase):
    """El denominador del porcentaje que muestra la TUI.

    No es cosmético: es el número con el que uno decide si ya hay que compactar. Estaba
    fijo en 128k para todos, así que en Claude —que tiene 200k— el porcentaje salía
    inflado un 56%.
    """

    def test_claude_tiene_200k(self):
        self.assertEqual(gc.contexto_de("databricks-claude-sonnet-4-5"), 200_000)

    def test_un_modelo_desconocido_usa_el_valor_por_defecto(self):
        self.assertEqual(gc.contexto_de("databricks-gemma-3-12b"), gc.CONTEXTO_POR_DEFECTO)

    def test_la_config_declara_el_contexto_de_cada_modelo(self):
        c = gc.construir_config(
            "https://ejemplo.cloud.databricks.com",
            [{"name": "databricks-claude-sonnet-4-5"}],
            {"databricks-claude-sonnet-4-5": {"forma": "string", "limite": 8192}},
        )
        limite = c["provider"][gc.PROVEEDOR]["models"]["databricks-claude-sonnet-4-5"]["limit"]
        self.assertEqual(limite["context"], 200_000)


if __name__ == "__main__":
    unittest.main()
