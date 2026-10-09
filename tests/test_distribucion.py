"""Instalación y política local, con contratos opcionales del paquete real."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import aplicacion
import distribucion
from scripts.empaquetar import arquitectura_motor, preparar
from politica import LIMITE_USD


class Distribucion(unittest.TestCase):
    def test_empaquetado_rechaza_version_y_presupuesto_invalidos(self):
        with tempfile.TemporaryDirectory() as temp:
            for importe in (0, -1, float("nan"), float("inf")):
                with self.assertRaisesRegex(ValueError, "positivo y finito"):
                    preparar("0.4.4", Path("motor"), importe, Path(temp))
            with self.assertRaisesRegex(ValueError, "versión semántica"):
                preparar("../../salida", Path("motor"), 10, Path(temp))

    def test_arquitectura_de_motores_por_formato(self):
        mach = b"\xcf\xfa\xed\xfe" + (0x100000c).to_bytes(4, "little") + bytes(56)
        elf = bytearray(64)
        elf[:6] = b"\x7fELF\x02\x01"
        elf[18:20] = (62).to_bytes(2, "little")
        pe = bytearray(70)
        pe[:2] = b"MZ"
        pe[60:64] = (64).to_bytes(4, "little")
        pe[64:70] = b"PE\x00\x00" + (0x8664).to_bytes(2, "little")
        with tempfile.TemporaryDirectory() as temp:
            archivo = Path(temp) / "motor"
            for cabecera, esperado in ((mach, "arm64"), (elf, "x64"), (pe, "x64")):
                archivo.write_bytes(cabecera)
                self.assertEqual(arquitectura_motor(archivo), esperado)
            archivo.write_bytes(b"no es un ejecutable")
            with self.assertRaisesRegex(ValueError, "formato ejecutable"):
                arquitectura_motor(archivo)

    def test_rechaza_paquete_con_politica_distinta_del_motor(self):
        with tempfile.TemporaryDirectory() as temp, patch("scripts.empaquetar.subprocess.run", return_value=SimpleNamespace(stdout=json.dumps({"bundled": True, "budget": 14}))):
            with self.assertRaisesRegex(ValueError, "presupuesto de esta distribución"):
                preparar("0.4.4", Path("motor"), 10, Path(temp))

    def test_politica_ignora_overrides_de_presupuesto(self):
        with patch.dict(os.environ, {"CUY_LIMITE_USD": "0", "CUY_AVISO_PORCENTAJE": "1000"}):
            distribucion.politica_entorno()
            self.assertEqual(float(os.environ["CUY_LIMITE_USD"]), LIMITE_USD)
            self.assertEqual(os.environ["CUY_AVISO_PORCENTAJE"], "80")

    def test_instalacion_y_reinstalacion_conservan_datos(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            origen = root / "descarga"
            origen.mkdir()
            nombre = "cuy.exe" if os.name == "nt" else "cuy"
            (origen / nombre).write_bytes(b"fixture ejecutable")
            (origen / "_internal/motor").mkdir(parents=True)
            usuario = root / "usuario"
            usuario.mkdir()
            for archivo in (".env", "opencode.json", "gasto.json"):
                (usuario / archivo).write_text("datos previos", encoding="utf-8")
            destino = usuario / "app"
            for _ in range(2):
                instalado = aplicacion.instalar_aplicacion(origen, destino)
                self.assertEqual(instalado.read_bytes(), b"fixture ejecutable")
                for archivo in (".env", "opencode.json", "gasto.json"):
                    self.assertEqual((usuario / archivo).read_text(), "datos previos")

    def test_paquete_incompleto_no_crea_instalacion(self):
        with tempfile.TemporaryDirectory() as temp:
            destino = Path(temp) / "app"
            with self.assertRaisesRegex(ValueError, "Paquete incompleto"):
                aplicacion.instalar_aplicacion(Path(temp), destino)
            self.assertFalse(destino.exists())

    def test_configuracion_usa_utilidades_incorporadas_sin_descargar_motor(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(aplicacion, "datos", return_value=Path(temp)), patch("instalar.resolver_host", return_value="https://example.invalid"), patch("instalar.resolver_credencial", return_value="credencial de prueba"), patch("instalar.generar", return_value={"model": "cuy/prueba"}), patch("cuy.buscar_binario", return_value=Path("motor")), patch("instalar.verificar", return_value=True) as verificar, patch("instalar.descargar_binario") as descarga:
            self.assertEqual(aplicacion.configurar([]), 0)
            verificar.assert_called_once()
            descarga.assert_not_called()


@unittest.skipUnless(os.environ.get("CUY_TEST_PAQUETE"), "Requiere paquete compilado")
class PaqueteReal(unittest.TestCase):
    def setUp(self):
        self.ejecutable = Path(os.environ["CUY_TEST_PAQUETE"]).resolve()
        self.temp = tempfile.TemporaryDirectory(prefix="cuy-paquete-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("DATABRICKS_", "OPENCODE_", "CUY_"))}
        self.env.update({"HOME": str(self.root), "USERPROFILE": str(self.root), "PATH": str(self.root / "sin-interpretes"), "CUY_LIMITE_USD": "0"})

    def correr(self, *args, input=None):
        return subprocess.run([str(self.ejecutable), *args], env=self.env, cwd=self.root,
                              input=input, capture_output=True, text=True, encoding="utf-8", timeout=180 if os.name == "nt" else 60)

    def test_paquete_no_entrega_fuentes_ni_credenciales(self):
        archivos = [p for p in self.ejecutable.parent.rglob("*") if p.is_file()]
        self.assertTrue(archivos)
        self.assertFalse([p for p in archivos if p.suffix in (".py", ".js", ".ts") or p.name in (".env", "opencode.json")])
        self.assertTrue((self.ejecutable.parent / "_internal/motor").is_dir())

    def test_instalacion_ayuda_y_version_sin_interpretes(self):
        instalado = self.correr("instalar")
        self.assertEqual(instalado.returncode, 0, instalado.stderr)
        datos = self.root / ".local/share/cuy-cli"
        (datos / "opencode.json").write_text("preservar", encoding="utf-8")
        (datos / ".env").write_text("fixture sin credenciales", encoding="utf-8")
        (datos / "gasto.json").write_text("{}", encoding="utf-8")
        self.assertEqual(self.correr("instalar").returncode, 0)
        self.assertEqual((datos / "opencode.json").read_text(), "preservar")
        for args in (("--version",), ("--help",), ("configurar", "--help")):
            result = self.correr(*args)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_diagnostico_y_gasto_del_paquete_sin_modelo(self):
        resultado = self.correr("doctor", "--json")
        controles = json.loads(resultado.stdout)["controles"]
        self.assertTrue(next(c["ok"] for c in controles if c["control"] == "ejecutable"))
        self.assertTrue(next(c["ok"] for c in controles if c["control"] == "versión del motor"))
        self.assertEqual(self.correr("gasto").returncode, 0)

    @unittest.skipUnless(os.environ.get("CUY_TEST_CODEGRAPH"), "Requiere indexador real")
    def test_mcp_desde_paquete_sin_python_externo(self):
        import codegraph
        (self.root / "modulo.py").write_text("def alpha(): return 1\n", encoding="utf-8")
        codegraph.preparar(self.root, Path(os.environ["CUY_TEST_CODEGRAPH"]).resolve())
        mensajes = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "codegraph_symbol_search", "arguments": {"query": "alpha"}}},
        ]
        result = self.correr("_codegraph", str(self.root), str(Path(os.environ["CUY_TEST_CODEGRAPH"]).resolve()), input="\n".join(json.dumps(m) for m in mensajes) + "\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        respuestas = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertTrue(any(r.get("id") == 2 and "alpha" in json.dumps(r) for r in respuestas), respuestas)
        self.assertNotIn(".cuy/codegraph/source", json.dumps(respuestas))
