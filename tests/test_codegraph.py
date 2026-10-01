"""Regresiones del índice local; CUY_TEST_CODEGRAPH habilita el contrato nativo."""

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import codegraph as cg
import cuy
import generar_config as gc


class Indice(unittest.TestCase):
    """Fronteras de archivos, descarga, permisos y protocolo sin dependencias reales."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cuy-indice-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.estado = self.root / cg.ESTADO
        self.estado.mkdir(parents=True)

    def test_copia_reutiliza_y_actualiza_archivos(self):
        fuente = self.root / "modulo.py"
        fuente.write_text("def alpha(): return 1\n", encoding="utf-8")
        primero, accion = cg._sincronizar(self.root, self.estado)
        self.assertEqual(accion, "creando")
        cg._json(self.estado / "manifest.json", primero)
        copia = self.estado / "source" / "modulo.py"
        inicial = copia.stat().st_mtime_ns
        segundo, accion = cg._sincronizar(self.root, self.estado)
        self.assertEqual(accion, "comprobando")
        self.assertEqual(primero, segundo)
        self.assertEqual(copia.stat().st_mtime_ns, inicial)
        fuente.write_text("def gamma(): return 2\n", encoding="utf-8")
        tercero, accion = cg._sincronizar(self.root, self.estado)
        self.assertEqual(accion, "actualizando")
        self.assertNotEqual(tercero, segundo)
        self.assertEqual(copia.read_bytes(), fuente.read_bytes())

    def test_borrados_invalidan_cache_y_copia(self):
        fuente = self.root / "modulo.py"
        fuente.write_text("def alpha(): return 1\n", encoding="utf-8")
        manifest, _ = cg._sincronizar(self.root, self.estado)
        cg._json(self.estado / "manifest.json", manifest)
        cache = self.estado / "home" / ".codegraph"
        cache.mkdir(parents=True)
        (cache / "obsoleto").write_text("cache")
        fuente.unlink()
        nuevo, accion = cg._sincronizar(self.root, self.estado)
        self.assertEqual(accion, "reconstruyendo")
        self.assertEqual(nuevo["archivos"], {})
        self.assertFalse(cache.exists())
        self.assertFalse((self.estado / "source" / "modulo.py").exists())

    def test_fuentes_respeta_git_y_excluye_secretos(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, capture_output=True)
        (self.root / ".gitignore").write_text("privado.py\n*.log\n", encoding="utf-8")
        nombres = {"normal.py": "token = response.token\n", "privado.py": "no incluir",
                   ".env": "no incluir", "credentials.json": "no incluir",
                   "imagen.png": "\0binario", "grande.py": "x" * (cg.MAX_ARCHIVO + 1)}
        for nombre, contenido in nombres.items():
            (self.root / nombre).write_text(contenido, encoding="utf-8")
        # Los secretos convencionales se excluyen incluso si ya fueron versionados.
        subprocess.run(["git", "-C", str(self.root), "add", "credentials.json"], check=True)
        (self.root / "node_modules").mkdir()
        (self.root / "node_modules" / "dep.js").write_text("const x=1")
        self.assertEqual(set(cg.fuentes(self.root)), {"normal.py"})

    def test_fuentes_no_sigue_enlaces(self):
        (self.root / "normal.py").write_text("def alpha(): return 1")
        try:
            (self.root / "enlace.py").symlink_to(self.root / "normal.py")
            (self.root / "directorio").symlink_to(self.root, target_is_directory=True)
        except OSError:
            self.skipTest("El equipo no permite crear symlinks")
        self.assertEqual(set(cg.fuentes(self.root)), {"normal.py"})
        # No seguir un estado preexistente que apunta afuera.
        shutil_target = self.root / "alternativo"
        shutil_target.mkdir()
        (self.estado / "source").symlink_to(shutil_target, target_is_directory=True)
        with self.assertRaises(ValueError):
            cg._sincronizar(self.root, self.estado)

    def test_gitignore_preserva_crlf_y_no_duplica(self):
        ruta = self.root / ".gitignore"
        ruta.write_bytes(b"# equipo\r\n*.log")
        cg.ignorar_estado(self.root)
        primero = ruta.read_bytes()
        self.assertTrue(primero.startswith(b"# equipo\r\n*.log\r\n"))
        cg.ignorar_estado(self.root)
        self.assertEqual(primero, ruta.read_bytes())
        for patron in cg.IGNORADOS_GIT:
            self.assertEqual(primero.count(patron.encode()), 1)

    def test_indice_separa_repos_y_traduce_rutas(self):
        (self.root / "a.py").write_text("def alpha(): return 1")
        otro = self.root / "otro"
        otro.mkdir()
        (otro / "b.py").write_text("def beta(): return 2")
        estado_otro = otro / cg.ESTADO
        estado_otro.mkdir(parents=True)
        a, _ = cg._sincronizar(self.root, self.estado)
        b, _ = cg._sincronizar(otro, estado_otro)
        self.assertNotEqual(a["raiz"], b["raiz"])
        self.assertIn("b.py", b["archivos"])
        copia = self.estado / "source"
        valor = {"location": {"file": str(copia / "a.py"), "line": 1}}
        self.assertEqual(cg._traducir(valor, copia, self.root)["location"]["file"], str(self.root / "a.py"))

    def test_argumentos_uri_con_espacios_y_limite_del_proyecto(self):
        fuente = self.root / "módulo con espacios.py"
        fuente.write_text("def alpha(): return 1", encoding="utf-8")
        cg._sincronizar(self.root, self.estado)
        copia = self.estado / "source"
        args = cg._argumentos({"uri": fuente.as_uri(), "line": 0}, self.root, copia)
        self.assertEqual(args["uri"], (copia / fuente.name).as_uri())
        self.assertEqual(cg._traducir(args["uri"], copia, self.root), fuente.as_uri())
        for uri in ((self.root.parent / "externo.py").as_uri(), "https://example.invalid/file",
                    (self.root / ".env").as_uri()):
            with self.subTest(uri=uri), self.assertRaises(ValueError):
                cg._argumentos({"uri": uri}, self.root, copia)

    def test_descarga_rechaza_checksum_sin_reemplazar(self):
        nombre = "codegraph-server-darwin-arm64"
        carpeta = self.root / "bin" / "codegraph" / cg.VERSION
        carpeta.mkdir(parents=True)
        destino = carpeta / nombre
        destino.write_bytes(b"anterior")
        (self.root / "codegraph-release.json").write_text(json.dumps({"version": cg.VERSION,
            "sha256": {nombre: hashlib.sha256(b"correcto").hexdigest()}}))
        respuesta = io.BytesIO(b"incorrecto")
        respuesta.geturl = lambda: "https://example.invalid/asset"
        with patch.object(cg, "RAIZ", self.root), patch.object(cg, "_plataforma", return_value=nombre), \
                patch.object(cg.urllib.request, "urlopen", return_value=respuesta), self.assertRaises(ValueError):
            cg.asegurar_binario()
        self.assertEqual(destino.read_bytes(), b"anterior")
        self.assertEqual(list(carpeta.iterdir()), [destino])

    def test_descarga_verificada_se_reutiliza(self):
        nombre = "codegraph-server-darwin-arm64"
        contenido = b"binario-verificado"
        (self.root / "codegraph-release.json").write_text(json.dumps({"version": cg.VERSION,
            "sha256": {nombre: hashlib.sha256(contenido).hexdigest()}}))
        respuesta = io.BytesIO(contenido)
        respuesta.geturl = lambda: "https://example.invalid/asset"
        with patch.object(cg, "RAIZ", self.root), patch.object(cg, "_plataforma", return_value=nombre), \
                patch.object(cg.urllib.request, "urlopen", return_value=respuesta) as red:
            ruta = cg.asegurar_binario()
            self.assertEqual(ruta.read_bytes(), contenido)
            self.assertEqual(cg.asegurar_binario(), ruta)
            self.assertEqual(red.call_count, 1)

    def test_entorno_nativo_no_recibe_credenciales(self):
        with patch.dict(os.environ, {"DATABRICKS_TOKEN": "sintetico", "OPENAI_API_KEY": "sintetico",
                                     "OTRO_SECRETO": "sintetico"}):
            entorno = cg._entorno(self.estado)
        self.assertNotIn("DATABRICKS_TOKEN", entorno)
        self.assertNotIn("OPENAI_API_KEY", entorno)
        self.assertNotIn("OTRO_SECRETO", entorno)
        self.assertEqual(entorno["HOME"], str(self.estado / "home"))

    def test_bloqueo_entre_sesiones(self):
        with cg._bloqueo(self.estado):
            with self.assertRaises(ValueError):
                with cg._bloqueo(self.estado):
                    self.fail("Dos sesiones no deben escribir la misma caché")
        with cg._bloqueo(self.estado):
            pass

    def test_plataformas_y_sidecar_windows(self):
        with patch.object(cg.platform, "system", return_value="Windows"), \
                patch.object(cg.platform, "machine", return_value="ARM64"), self.assertRaises(ValueError):
            cg._plataforma()
        with patch.object(cg.platform, "system", return_value="Linux"), \
                patch.object(cg.platform, "machine", return_value="aarch64"):
            self.assertEqual(cg._plataforma(), "codegraph-server-linux-arm64")
        nombre = "codegraph-server-win32-x64.exe"
        valores = {nombre: b"motor", "onnxruntime.dll": b"sidecar"}
        (self.root / "codegraph-release.json").write_text(json.dumps({"version": cg.VERSION,
            "sha256": {n: hashlib.sha256(v).hexdigest() for n, v in valores.items()}}))
        def responder(url, **_):
            respuesta = io.BytesIO(valores[url.rsplit("/", 1)[1]])
            respuesta.geturl = lambda: url
            return respuesta
        with patch.object(cg, "RAIZ", self.root), patch.object(cg, "_plataforma", return_value=nombre), \
                patch.object(cg.urllib.request, "urlopen", side_effect=responder):
            binario = cg.asegurar_binario()
        self.assertEqual(binario.read_bytes(), b"motor")
        self.assertEqual((binario.parent / "onnxruntime.dll").read_bytes(), b"sidecar")

    def test_configuracion_y_arranque_de_conversacion(self):
        config = gc.construir_config("https://example.invalid", [{"name": "x"}],
                                    {"x": {"forma": "string", "limite": 100}})
        entorno = {"OPENCODE_CONFIG_CONTENT": json.dumps(config)}
        with patch.object(cg, "asegurar_binario", return_value=Path("fake")), \
                patch.object(cg, "preparar") as preparar:
            nuevo = cg.configurar(entorno, self.root)
        preparar.assert_called_once_with(self.root, Path("fake"))
        efectiva = json.loads(nuevo["OPENCODE_CONFIG_CONTENT"])
        self.assertIn("cuy_codegraph", efectiva["mcp"])
        for nombre in cg.HERRAMIENTAS:
            self.assertEqual(efectiva["agent"]["plan"]["permission"][f"cuy_codegraph_{nombre}"], "allow")
        self.assertEqual(efectiva["agent"]["plan"]["permission"]["*"], "deny")
        with patch.object(cuy, "buscar_binario", return_value=Path("fake")), \
                patch.object(cuy, "cargar_env"), patch.object(cuy, "entorno_agente", return_value=entorno), \
                patch.object(cg, "configurar", return_value=nuevo) as configurar, \
                patch.object(sys, "argv", ["cuy"]), patch.object(cuy.subprocess, "call", return_value=0) as motor:
            self.assertEqual(cuy.main(), 0)
        configurar.assert_called_once_with(entorno, Path.cwd())
        self.assertEqual(motor.call_args.kwargs["env"], nuevo)

    def test_no_indexa_cli_y_resuelve_directorios(self):
        for argumentos in (["--version"], ["--help"], ["mcp", "list"], ["serve"],
                           ["run", "--attach=http://localhost:123", "hola"]):
            self.assertIsNone(cg.carpeta_conversacion(argumentos))
        self.assertEqual(cg.carpeta_conversacion(["run", "--dir", str(self.root), "hola"]), self.root)
        self.assertEqual(cg.carpeta_conversacion([str(self.root)]), self.root)
        self.assertEqual(cg.carpeta_conversacion(["--model", "x"]), Path.cwd())
        self.assertEqual(cg.carpeta_conversacion(["--model", "x", str(self.root)]), self.root)

    def test_fallo_del_indice_conserva_entorno(self):
        original = {"OPENCODE_CONFIG_CONTENT": "{}"}
        with patch.object(cg, "asegurar_binario", side_effect=OSError("offline")), \
                patch.object(sys, "stderr", io.StringIO()) as salida:
            self.assertIs(cg.configurar(original, self.root), original)
        self.assertIn("Continúa", salida.getvalue())
        self.assertNotIn("offline", salida.getvalue())

    def test_mcp_solo_expone_y_ejecuta_lectura(self):
        tools = [{"name": nombre, "inputSchema": {"type": "object"}} for nombre in cg.HERRAMIENTAS]
        peticiones = [{"id": 1, "method": "initialize"}, {"method": "notifications/initialized"},
                     {"id": 2, "method": "tools/list"},
                     {"id": 3, "method": "tools/call", "params": {"name": "codegraph_reindex_workspace"}}]
        entrada = io.StringIO("".join(json.dumps(p) + "\n" for p in peticiones))
        with patch.object(cg, "_esquemas", return_value=tools), patch.object(sys, "stdin", entrada), \
                patch.object(sys, "stdout", io.StringIO()) as salida, patch.object(cg, "_nativo") as nativo:
            self.assertEqual(cg.servir(self.root, Path("fake")), 0)
        respuestas = [json.loads(l) for l in salida.getvalue().splitlines()]
        self.assertEqual(len(respuestas), 3)  # notificaciones sin respuesta
        self.assertEqual({t["name"] for t in respuestas[1]["result"]["tools"]}, cg.HERRAMIENTAS)
        self.assertTrue(respuestas[2]["result"]["isError"])
        nativo.assert_not_called()


@unittest.skipUnless(os.environ.get("CUY_TEST_CODEGRAPH"), "Requiere CUY_TEST_CODEGRAPH para el contrato nativo")
class CodeGraphReal(unittest.TestCase):
    """Búsquedas contra el ejecutable publicado, sin modelos ni llamadas a Databricks."""

    def test_indice_real_actualiza_altas_cambios_y_borrados(self):
        binario = Path(os.environ["CUY_TEST_CODEGRAPH"])
        with tempfile.TemporaryDirectory(prefix="cuy-graph-real-") as temp:
            raiz = Path(temp).resolve()
            fuente = raiz / "modulo.py"
            fuente.write_text("def alpha():\n    return 1\n\ndef beta():\n    return alpha()\n", encoding="utf-8")
            herramientas = cg.preparar(raiz, binario)
            self.assertEqual({t["name"] for t in herramientas}, cg.HERRAMIENTAS)
            def buscar(nombre):
                return cg.consultar(raiz, binario, "codegraph_symbol_search", {"query": nombre})
            alpha = buscar("alpha")
            self.assertEqual(alpha["total_matches"], 1)
            self.assertEqual(alpha["results"][0]["symbol"]["location"]["file"], str(fuente))
            # El resolvedor nativo usa las líneas almacenadas desde 1; consultar
            # dentro del cuerpo evita su ambigüedad con el nodo CodeFile en línea 1.
            info = cg.consultar(raiz, binario, "codegraph_get_symbol_info", {"uri": fuente.as_uri(), "line": 5})
            self.assertIn("beta", json.dumps(info))
            copia = raiz / cg.ESTADO / "source" / "modulo.py"
            antes = copia.stat().st_mtime_ns
            cg.preparar(raiz, binario)
            self.assertEqual(copia.stat().st_mtime_ns, antes)
            fuente.write_text("def gamma():\n    return 2\n", encoding="utf-8")
            self.assertEqual(buscar("gamma")["total_matches"], 1)
            self.assertEqual(buscar("alpha")["total_matches"], 0)
            otro = raiz / "otro.py"
            otro.write_text("def delta():\n    return 3\n", encoding="utf-8")
            self.assertEqual(buscar("delta")["total_matches"], 1)
            fuente.unlink()
            self.assertEqual(buscar("gamma")["total_matches"], 0)
            self.assertEqual(buscar("delta")["total_matches"], 1)

    def test_servidor_mcp_real_responde_a_consulta(self):
        with tempfile.TemporaryDirectory(prefix="cuy-graph-mcp-") as temp:
            raiz = Path(temp).resolve()
            (raiz / "modulo.py").write_text("def alpha(): return 1\n", encoding="utf-8")
            binario = Path(os.environ["CUY_TEST_CODEGRAPH"]).resolve()
            cg.preparar(raiz, binario)
            peticiones = [{"jsonrpc": "2.0", "id": 1, "method": "initialize"},
                         {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                         {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
                             "name": "codegraph_symbol_search", "arguments": {"query": "alpha"}}}]
            result = subprocess.run([sys.executable, str(cg.RAIZ / "codegraph.py"), "serve", str(raiz), str(binario)],
                input="".join(json.dumps(p) + "\n" for p in peticiones), capture_output=True,
                text=True, encoding="utf-8", timeout=cg.TIMEOUT)
            self.assertEqual(result.returncode, 0, result.stderr)
            respuestas = [json.loads(l) for l in result.stdout.splitlines()]
            self.assertEqual(len(respuestas[1]["result"]["tools"]), 12)
            valor = json.loads(respuestas[2]["result"]["content"][0]["text"])
            self.assertEqual(valor["total_matches"], 1)
