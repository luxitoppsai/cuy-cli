"""Flujos con git real en temporales y respuestas sintéticas del motor."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import tareas
import presentacion


class Tareas(unittest.TestCase):
    """Flujos de tarea: aislamiento, verificación y validación de la entrega."""

    def setUp(self):
        """Crea un repositorio git temporal donde correr los flujos."""
        self.tmp = tempfile.TemporaryDirectory(prefix="cuy-flujos-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        for args in (("init",), ("config", "user.email", "test@example.invalid"), ("config", "user.name", "Test")):
            tareas.git(self.repo, *args)
        (self.repo / "app.py").write_text("valor = 1\n", encoding="utf-8")
        tareas.git(self.repo, "add", ".")
        tareas.git(self.repo, "commit", "-m", "fixture")
        self.config = {"model": "cuy/test", "provider": {"cuy": {"models": {"test": {"cost": {"input": 1, "output": 2}}}}}}
        self.env = {**os.environ, "CUY_LIMITE_USD": "10", "CUY_GASTO": str(self.root / "gasto.json"),
                    "OPENCODE_CONFIG_CONTENT": json.dumps(self.config), "DATABRICKS_TOKEN": "solo-prueba"}
        self.ejecutor = tareas.ejecutar_proceso

    def respuesta(self, carpeta, corregir=False):
        """Devuelve la entrega JSON que simula la respuesta del agente."""
        if corregir:
            (carpeta / "app.py").write_text("valor = 2\n", encoding="utf-8")
        entrega = {"resumen": "Módulo revisado.", "referencias": [{"archivo": "app.py", "linea": 1, "explicacion": "Define el valor."}], "hallazgos": []}
        return json.dumps({"type": "text", "sessionID": "ses-demo", "part": {"id": "p1", "text": json.dumps(entrega)}})

    def motor(self, argv, carpeta, entorno, limite, entrada=None):
        """Reemplaza la ejecución del motor por una respuesta fija."""
        if argv[0] != "motor-falso":
            return self.ejecutor(argv, carpeta, entorno, limite, entrada)
        cfg = json.loads(entorno["OPENCODE_CONFIG_CONTENT"])
        agente = cfg["agent"][argv[-1]]
        self.assertEqual(agente["permission"]["*"], "deny")
        self.assertNotIn("bash", agente["permission"])
        return 0, self.respuesta(carpeta, argv[-1] == "cuy-corregir"), False

    def correr(self, flujo="entender", pruebas=None):
        """Corre un flujo completo con el motor fingido."""
        with patch.object(tareas, "ejecutar_proceso", side_effect=self.motor):
            return tareas.correr_tarea(flujo, "Objetivo", self.repo, Path("motor-falso"), self.env,
                                       self.root / "tareas", pruebas or [], 20)

    def test_entender_entrega_referencias_y_no_cambia_archivos(self):
        antes = tareas.foto(self.repo)
        reporte = self.correr()
        self.assertEqual(reporte["estado"], "entregada")
        self.assertEqual(antes, tareas.foto(self.repo))
        self.assertEqual(reporte["sesiones"], ["ses-demo"])
        self.assertEqual(json.loads(Path(reporte["informe"]).read_text())["estado"], "entregada")

    def test_corregir_worktree_y_regresion_antes_despues(self):
        comando = [sys.executable, "-c", "import app; assert app.valor == 2"]
        reporte = self.correr("corregir", [comando])
        self.assertEqual(reporte["estado"], "verificada", reporte)
        self.assertNotEqual(Path(reporte["trabajo"]), self.repo)
        self.assertEqual((self.repo / "app.py").read_text(), "valor = 1\n")
        self.assertEqual(reporte["archivos"], ["app.py"])
        self.assertIn("+valor = 2", Path(reporte["diff"]).read_text())
        tareas.git(self.repo, "apply", "--check", reporte["diff"])
        self.assertNotEqual(reporte["pruebas"][0]["antes"], 0)
        self.assertEqual(reporte["pruebas"][0]["codigo"], 0)
        # No commits, no staging ni aplicación automática.
        self.assertEqual(tareas.git(self.repo, "status", "--porcelain"), b"")
        self.assertEqual(tareas.git(Path(reporte["trabajo"]), "rev-parse", "HEAD").decode().strip(), reporte["base"])

    def test_diff_incluye_archivos_nuevos_sin_staging(self):
        (self.repo / "nuevo.py").write_text("print('nuevo')\n")
        destino = self.root / "cambios.patch"
        tareas.guardar_diff(self.repo, destino)
        self.assertIn("+print('nuevo')", destino.read_text())
        self.assertEqual(tareas.git(self.repo, "diff", "--cached"), b"")
        (self.repo / "nuevo.py").unlink()
        tareas.git(self.repo, "apply", "--check", str(destino))

    def test_sin_pruebas_no_declara_verificada(self):
        self.assertEqual(self.correr("corregir")["estado"], "sin_verificar")

    def test_fallo_de_pruebas_no_declara_verificada(self):
        reporte = self.correr("corregir", [[sys.executable, "-c", "raise SystemExit(2)"]])
        self.assertEqual(reporte["estado"], "sin_verificar")
        self.assertEqual(reporte["pruebas"][0]["codigo"], 2)

    def test_cambios_previos_se_preservan_y_no_arranca_correccion(self):
        (self.repo / "app.py").write_text("cambio del usuario\n")
        with self.assertRaisesRegex(ValueError, "cambios previos"):
            self.correr("corregir")
        self.assertEqual((self.repo / "app.py").read_text(), "cambio del usuario\n")
        self.assertEqual(self.correr("revisar")["estado"], "entregada")

    def test_respuesta_invalida_y_error_motor_exit_cero_no_se_aceptan(self):
        for text in ('{"type":"text","part":{"text":"terminé"}}', '{"type":"error","error":{}}'):
            with patch.object(tareas, "ejecutar_proceso", return_value=(0, text, False)):
                reporte = tareas.correr_tarea("entender", "x", self.repo, Path("motor-falso"), self.env, self.root / "tareas", [], 20)
            self.assertEqual(reporte["estado"], "error")

    def test_rechaza_lineas_inventadas_y_escape_de_ruta(self):
        for archivo, linea in (("app.py", 99), ("../fuera", 1), (str(self.repo / "app.py"), 1)):
            entrega = {"resumen": "x", "referencias": [{"archivo": archivo, "linea": linea, "explicacion": "x"}], "hallazgos": []}
            with self.assertRaises(ValueError):
                tareas.validar_entrega(json.dumps(entrega), self.repo, "entender")

    def test_pruebas_no_reciben_token_ni_configuracion_del_motor(self):
        env = tareas.entorno_pruebas(self.env, self.repo)
        self.assertNotIn("DATABRICKS_TOKEN", env)
        self.assertNotIn("OPENCODE_CONFIG_CONTENT", env)

    def test_timeout_conserva_informe_sin_exito(self):
        with patch.object(tareas, "ejecutar_proceso", return_value=(-15, "", True)):
            reporte = tareas.correr_tarea("entender", "x", self.repo, Path("motor-falso"), self.env, self.root / "tareas", [], 20)
        self.assertEqual(reporte["estado"], "error")
        self.assertIn("tiempo", reporte["motivo"])

    def test_presupuesto_desconocido_no_inicia_motor(self):
        self.config["provider"]["cuy"]["models"]["test"]["cost"] = {}
        self.env["OPENCODE_CONFIG_CONTENT"] = json.dumps(self.config)
        with self.assertRaisesRegex(ValueError, "tarifas"):
            self.correr()
        self.assertFalse((self.root / "tareas").exists())


class Presentacion(unittest.TestCase):
    """El informe se muestra sin interpretar escapes de terminal."""

    def test_terminal_no_interpreta_escapes_del_modelo(self):
        reporte = {"flujo": "revisar", "estado": "error", "motivo": "\x1b[2Jborra pantalla\u202etexto"}
        salida = presentacion.render_resultado(reporte, 40)
        self.assertNotIn("\x1b", salida)
        self.assertNotIn("\u202e", salida)
        self.assertTrue(all(len(line) <= 40 for line in salida.splitlines()))

    def test_demo_html_sin_scripts_inyectados_por_resultados(self):
        with tempfile.TemporaryDirectory() as tmp:
            archivo = Path(tmp) / "demo.html"
            with patch.object(presentacion, "ejemplos", return_value=[{"estado": "error", "motivo": "<script>malicioso()</script>"}]):
                presentacion.html_demo(archivo)
            html = archivo.read_text()
            self.assertIn("&lt;script&gt;malicioso()&lt;/script&gt;", html)
            self.assertNotIn("<script>malicioso()", html)

    def test_deduplica_costos_y_no_inventa_costo_cuando_falta(self):
        evento = json.dumps({"type": "step_finish", "part": {"id": "p", "cost": .1}})
        self.assertEqual(tareas.leer_eventos(evento + "\n" + evento)["costo_usd"], .1)
        self.assertIsNone(tareas.leer_eventos("")["costo_usd"])
