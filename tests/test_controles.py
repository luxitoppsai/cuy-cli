"""Regresiones en fronteras: contratos, instalación y ejecución desde otros proyectos."""
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cuy
import generar_config as gc
import instalar
from configuracion import validar_host, numero_entorno, leer_gasto


class Controles(unittest.TestCase):
    """Controles de red y de configuración que no dependen del workspace."""

    def test_rechaza_hosts_inseguros(self):
        for host in ("http://example.com", "https://user:pass@example.com", "https://x/a", "https://x?q=1", "https://x#f"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                validar_host(host)
        self.assertEqual(validar_host("https://example.com/"), "https://example.com")

    def test_no_acepta_nan_ni_limites_negativos(self):
        for value in ("nan", "inf", "-1", "abc"):
            with patch.dict(os.environ, {"CUY_LIMITE_USD": value}), self.assertRaises(ValueError):
                numero_entorno("CUY_LIMITE_USD", 10)

    def test_unknown_no_es_compatible(self):
        config = gc.construir_config("https://example.com", [{"name": "x"}],
                                      {"x": {"forma": "desconocido", "limite": 100}})
        self.assertEqual(config["provider"], {})

    def test_nativo_no_depende_del_primer_endpoint(self):
        def respuesta(host, headers, body):
            """Responde como el workspace, para no depender de uno real."""
            return (200, {}) if body["model"] == "claude-b" else (404, {})
        with patch.object(gc, "_pedir_anthropic", side_effect=respuesta):
            resultado = gc.detectar_anthropic("https://x", "fake", ["databricks-claude-a", "databricks-claude-b"])
        self.assertEqual(resultado["modelos"], {"databricks-claude-b": "claude-b"})

    def test_verificar_claude_usa_messages_y_nombre_nativo(self):
        config = {"model": "cuy-claude/claude-sonnet-4-5", "provider": {"cuy-claude": {
            "npm": "@ai-sdk/anthropic", "options": {
                "baseURL": "https://example.com" + gc.RUTA_ANTHROPIC,
                "headers": {"Authorization": "Bearer {env:DATABRICKS_TOKEN}"},
            }}}}
        with patch.object(gc, "_pedir_anthropic", return_value=(200, {"content": [{"type": "text", "text": "ok"}]})) as nativo, patch.object(gc, "_pedir") as compatible:
            self.assertTrue(instalar.verificar("https://example.com", "fake", config))
        compatible.assert_not_called()
        self.assertEqual(nativo.call_args.args[0], "https://example.com")
        self.assertEqual(nativo.call_args.args[2]["model"], "claude-sonnet-4-5")
        self.assertEqual(nativo.call_args.args[1]["Authorization"], "Bearer fake")

    def test_lanzador_conserva_cwd_y_carga_politica_fuente(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(cuy, "RAIZ", Path(temp)):
            config = gc.construir_config("https://example.com", [{"name": "x"}], {"x": {"forma": "string", "limite": 100}})
            config["permission"] = {"*": "allow"}  # instalación anterior
            (Path(temp) / "opencode.json").write_text(json.dumps(config))
            anterior = Path.cwd()
            env = cuy.entorno_agente()
            self.assertEqual(Path.cwd(), anterior)
            efectiva = json.loads(env["OPENCODE_CONFIG_CONTENT"])
            self.assertNotIn("*", efectiva["permission"])
            self.assertEqual(efectiva["agent"]["plan"]["permission"]["*"], "deny")
            self.assertEqual(len(efectiva["plugin"]), 3)
            self.assertTrue(all(p.startswith(Path(temp).as_uri()) for p in efectiva["plugin"]))
            self.assertEqual(env["OPENCODE_DISABLE_PROJECT_CONFIG"], "1")

    def test_instalacion_seleccionada_no_es_sombreada_por_descarga_vieja(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(cuy, "RAIZ", Path(temp)):
            root = Path(temp)
            (root / "bin").mkdir()
            (root / "bin" / "cuy").touch()
            elegido = root / "nuevo"
            elegido.touch()
            (root / "bin" / "seleccion.json").write_text(json.dumps({"path": str(elegido)}))
            self.assertEqual(cuy.buscar_binario(), elegido)

    def test_checksum_incorrecto_preserva_binario(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(instalar, "RAIZ", Path(temp)), patch.object(instalar, "ES_WINDOWS", False), patch("platform.system", return_value="Darwin"), patch("platform.machine", return_value="arm64"):
            root = Path(temp)
            (root / "bin").mkdir()
            destino = root / "bin" / "cuy"
            destino.write_bytes(b"anterior")
            manifest = root / "release.json"
            manifest.write_text(json.dumps({"version": "v1.0.0", "sha256": {"cuy-darwin-arm64": hashlib.sha256(b"correcto").hexdigest()}}))
            with patch("urllib.request.urlopen", return_value=io.BytesIO(b"incorrecto")), self.assertRaises(SystemExit):
                instalar.descargar_binario(manifest)
            self.assertEqual(destino.read_bytes(), b"anterior")
            self.assertEqual(list((root / "bin").iterdir()), [destino])

    def test_release_latest_se_rechaza_antes_de_descargar(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(instalar, "RAIZ", Path(temp)), patch("platform.system", return_value="Darwin"), patch("platform.machine", return_value="arm64"):
            manifest = Path(temp) / "release.json"
            manifest.write_text('{"version":"latest"}')
            with patch("urllib.request.urlopen") as red, self.assertRaises(SystemExit):
                instalar.descargar_binario(manifest)
            red.assert_not_called()


class DiagnosticoYContabilidad(unittest.TestCase):
    """El diagnóstico detecta lo que falta y la contabilidad no asume gasto cero."""

    def test_lector_python_rechaza_corrupcion_como_el_plugin(self):
        with tempfile.TemporaryDirectory() as temp:
            ruta = Path(temp) / "gasto.json"
            for contenido in ('[]', '{"2026-09": -1}', '{"2026-09": "gratis"}', '{"_eventos": []}', '{roto'):
                ruta.write_text(contenido)
                with self.subTest(contenido=contenido), self.assertRaises(ValueError):
                    leer_gasto(ruta)

    def test_doctor_no_expone_credencial(self):
        import diagnostico
        from types import SimpleNamespace
        config = gc.construir_config("https://example.com", [{"name": "databricks-claude-sonnet-4"}],
            {"databricks-claude-sonnet-4": {"forma": "string", "limite": 100}})
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"DATABRICKS_TOKEN": "token-sintetico", "CUY_GASTO": str(Path(temp) / "gasto.json")}), patch.object(cuy, "buscar_binario", return_value=Path("fake")), patch.object(cuy, "entorno_agente", return_value={"OPENCODE_CONFIG_CONTENT": json.dumps(config)}), patch.object(diagnostico.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="1.18.32")):
            reporte = diagnostico.diagnosticar()
        self.assertTrue(reporte["ok"])
        self.assertNotIn("token-sintetico", json.dumps(reporte))
