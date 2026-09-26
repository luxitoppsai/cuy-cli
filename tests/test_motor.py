"""Contrato con el ejecutable real y un proveedor SSE sintético, sin tokens ni Databricks.

CUY_TEST_BINARIO=/ruta/al/binario python3 -m unittest discover -s tests -p test_motor.py
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import sys
import threading
import unittest
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cuy
import generar_config as gc


@unittest.skipUnless(os.environ.get("CUY_TEST_BINARIO"), "Requiere CUY_TEST_BINARIO para probar el motor real")
class Motor(unittest.TestCase):
    """Contrato con el binario real: permisos por agente, edición y tope de gasto."""

    def setUp(self):
        """Levanta un proveedor SSE sintético y un proyecto temporal."""
        self.temp = tempfile.TemporaryDirectory(prefix="cuy-motor-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.requests = []
        self.schemas = []
        self.structured = False
        owner = self

        class Handler(BaseHTTPRequestHandler):
            """Proveedor SSE sintético: responde como Databricks sin serlo."""

            def log_message(self, *_):
                """Silencia el log del servidor para no ensuciar la salida del test."""
                pass

            def do_POST(self):
                """Devuelve un stream fijo de eventos con forma de respuesta real."""
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                owner.requests.append(body)
                tools = [t["function"]["name"] for t in body.get("tools", [])]
                owner.schemas.append(tools)
                already = any(m.get("role") == "tool" for m in body.get("messages", []))
                if "write" in tools and not already:
                    delta = {"role": "assistant", "tool_calls": [{"index": 0, "id": "call_1", "type": "function", "function": {
                        "name": "write", "arguments": json.dumps({"filePath": "resultado.txt", "content": "prueba correcta\n"}),
                    }}]}
                    finish = "tool_calls"
                else:
                    delta = {"role": "assistant", "content": json.dumps({"resumen": "Archivo creado.", "referencias": [{"archivo": "resultado.txt", "linea": 1, "explicacion": "Resultado de la tarea."}], "hallazgos": []}) if owner.structured else "Verificado"}
                    finish = "stop"
                if not body.get("stream"):
                    response = {"id": "fake", "object": "chat.completion", "model": "prueba", "choices": [{"index": 0, "message": {"role": "assistant", "content": "Verificado"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
                    raw = json.dumps(response).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(raw)
                    return
                chunks = [
                    {"id": "fake", "object": "chat.completion.chunk", "created": 1, "model": "prueba", "choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
                    {"id": "fake", "object": "chat.completion.chunk", "created": 1, "model": "prueba", "choices": [{"index": 0, "delta": {}, "finish_reason": finish}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}},
                ]
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                for chunk in chunks:
                    self.wfile.write(("data: " + json.dumps(chunk) + "\n\n").encode())
                self.wfile.write(b"data: [DONE]\n\n")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def entorno(self, agotado=False):
        """Arma el entorno del motor, opcionalmente con el presupuesto agotado."""
        config = gc.construir_config("https://example.invalid", [{"name": "prueba"}], {"prueba": {"forma": "string", "limite": 1000}})
        config["provider"]["cuy"]["options"] = {"baseURL": f"http://127.0.0.1:{self.server.server_port}", "apiKey": "fake"}
        config["provider"]["cuy"]["models"]["prueba"]["cost"] = {"input": 3, "output": 15}
        config["plugin"] = [(cuy.RAIZ / "plugin" / f"{name}.js").as_uri() for name in ("presupuesto", "auditoria", "secretos")]
        config["share"] = "disabled"
        config["agent"]["build"]["steps"] = 3
        env = {k: v for k, v in os.environ.items() if not k.startswith(("DATABRICKS_", "OPENCODE_", "CUY_", "ANTHROPIC_", "OPENAI_"))}
        env.update(cuy.BLINDAJE)
        env.update({f"XDG_{kind}_HOME": str(self.root / kind.lower()) for kind in ("CONFIG", "DATA", "CACHE", "STATE")})
        env.update({"OPENCODE_TEST_HOME": str(self.root), "PWD": str(self.root), "OPENCODE_CONFIG_CONTENT": json.dumps(config), "CUY_GASTO": str(self.root / "gasto.json"), "CUY_AUDITORIA": str(self.root / "auditoria.jsonl"), "CUY_LIMITE_USD": "10"})
        (self.root / "gasto.json").write_text(json.dumps({datetime.now().strftime("%Y-%m"): 10 if agotado else 0}))
        return env

    def ejecutar(self, agente="build", agotado=False):
        """Corre el binario real contra el proveedor sintético y devuelve su salida."""
        env = self.entorno(agotado)
        return subprocess.run([os.environ["CUY_TEST_BINARIO"], "run", "--format", "json", "--agent", agente, "Escribe resultado.txt con prueba correcta."], cwd=self.root, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45)

    def test_presupuesto_impide_request_real(self):
        result = self.ejecutar(agotado=True)
        self.assertEqual(self.requests, [], (result.stdout + result.stderr)[-3000:])
        self.assertIn("Tope mensual", result.stdout + result.stderr)

    def test_build_edita_y_audita_resultado(self):
        result = self.ejecutar()
        self.assertTrue((self.root / "resultado.txt").exists(), (result.stdout + result.stderr)[-3000:])
        self.assertEqual((self.root / "resultado.txt").read_text(), "prueba correcta\n")
        audit = [json.loads(line) for line in (self.root / "auditoria.jsonl").read_text().splitlines()]
        self.assertTrue(any(r.get("evento") == "herramienta.resultado" and r.get("estado") == "completed" for r in audit))
        self.assertGreater(json.loads((self.root / "gasto.json").read_text())[datetime.now().strftime("%Y-%m")], 0)

    def test_plan_no_expone_herramientas_de_escritura(self):
        result = self.ejecutar(agente="plan")
        self.assertTrue(self.requests, (result.stdout + result.stderr)[-3000:])
        self.assertFalse((self.root / "resultado.txt").exists())
        for schema in self.schemas:
            self.assertFalse(set(schema) & {"write", "edit", "apply_patch", "bash", "task"}, schema)

    def test_flujo_corregir_aisla_y_verifica_antes_despues(self):
        import tareas
        self.structured = True
        repo = self.root / "proyecto"
        repo.mkdir()
        (repo / "README.md").write_text("Proyecto de prueba\n")
        for args in (("init",), ("config", "user.email", "test@example.invalid"),
                     ("config", "user.name", "Test"), ("add", "."), ("commit", "-m", "fixture")):
            tareas.git(repo, *args)
        informe = tareas.correr_tarea("corregir", "Crear resultado.txt con prueba correcta.", repo,
            Path(os.environ["CUY_TEST_BINARIO"]), self.entorno(), self.root / "tareas",
            [[sys.executable, "-c", "from pathlib import Path; assert Path('resultado.txt').read_text().strip() == 'prueba correcta'"]], 45)
        self.assertEqual(informe["estado"], "verificada", informe)
        self.assertFalse((repo / "resultado.txt").exists())
        self.assertEqual(informe["archivos"], ["resultado.txt"])
        self.assertIn("+prueba correcta", Path(informe["diff"]).read_text())
        tareas.git(repo, "apply", "--check", informe["diff"])
        self.assertNotEqual(informe["pruebas"][0]["antes"], 0)
        self.assertEqual(informe["pruebas"][0]["codigo"], 0)
