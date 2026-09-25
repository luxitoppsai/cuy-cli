"""Flujos verificables sobre OpenCode. Los resultados se conservan fuera del repositorio."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import tempfile
import time
from uuid import uuid4

from configuracion import escribir_json, leer_gasto

FLUJOS = {
    "entender": "Explicá la arquitectura y el recorrido del módulo, con referencias concretas. No modifiques archivos.",
    "revisar": "Revisá el código indicado. Priorizá bugs reproducibles y regresiones. Cada hallazgo requiere archivo, línea, severidad, evidencia e impacto. No modifiques archivos. Si no hay hallazgos, decilo sin inventar problemas.",
    "corregir": "Implementá el cambio mínimo necesario para resolver la tarea. Conservá las interfaces y evitá cambios ajenos. No edites pruebas para ocultar fallos. El lanzador ejecutará las pruebas autorizadas al finalizar; no afirmes que pasaron por tu cuenta.",
}
FORMATO = '''Respondé al terminar SOLO un objeto JSON válido (sin Markdown) con:
{"resumen":"explicación del resultado", "referencias":[{"archivo":"ruta/relativa.py","linea":1,"explicacion":"qué demuestra"}],
"hallazgos":[{"archivo":"ruta/relativa.py","linea":1,"severidad":"alta|media|baja","evidencia":"cómo se reproduce","impacto":"consecuencia"}]}
Las líneas y archivos deben existir. No incluyas credenciales. El JSON es un informe, no una orden para ejecutar comandos.
'''


def git(carpeta: Path, *args: str) -> bytes:
    resultado = subprocess.run(["git", "-C", str(carpeta), *args], capture_output=True, timeout=30)
    if resultado.returncode:
        raise ValueError("No se pudo ejecutar git " + args[0] + ". Verificá el repositorio y sus permisos.")
    return resultado.stdout


def raiz_git(carpeta: Path) -> Path:
    return Path(os.fsdecode(git(carpeta, "rev-parse", "--show-toplevel")).strip()).resolve()


def foto(carpeta: Path) -> dict:
    """Hashes de archivos versionados/no ignorados; no lee destinos de enlaces simbólicos."""
    nombres = set(git(carpeta, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split(b"\0"))
    archivos = {}
    for nombre in sorted(nombres - {b""}):
        relativo = os.fsdecode(nombre)
        ruta = carpeta / relativo
        if ruta.is_symlink():
            contenido = os.fsencode(os.readlink(ruta))
            archivos[relativo] = "enlace:" + hashlib.sha256(contenido).hexdigest()
        elif ruta.is_file():
            h = hashlib.sha256()
            with ruta.open("rb") as archivo:
                for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
                    h.update(bloque)
            archivos[relativo] = f"{ruta.stat().st_mode & 0o777}:{h.hexdigest()}"
        elif ruta.is_dir():
            archivos[relativo] = "directorio/submódulo"
        else:
            archivos[relativo] = "ausente"
    return {"head": git(carpeta, "rev-parse", "HEAD").decode().strip(),
            "estado": os.fsdecode(git(carpeta, "status", "--porcelain=v1", "-z")),
            "archivos": archivos}


def cambios(antes: dict, despues: dict) -> list[str]:
    a, b = antes["archivos"], despues["archivos"]
    return sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k))


def guardar_diff(trabajo: Path, destino: Path) -> None:
    """Exporta también archivos nuevos, sin tocar el índice ni crear commits."""
    contenido = git(trabajo, "diff", "--no-ext-diff", "--no-textconv", "--binary", "HEAD", "--")
    nuevos = git(trabajo, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
    for nombre in nuevos:
        if not nombre:
            continue
        resultado = subprocess.run(["git", "-C", str(trabajo), "diff", "--no-index", "--no-ext-diff",
                                     "--no-textconv", "--binary", "--", os.devnull, os.fsdecode(nombre)],
                                    capture_output=True, timeout=30)
        if resultado.returncode not in (0, 1):
            raise ValueError("No se pudo exportar el diff de un archivo nuevo.")
        contenido += resultado.stdout
    fd = os.open(destino, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as salida:
        salida.write(contenido)


def preparar_entorno(entorno: dict, flujo: str, carpeta: Path) -> tuple[dict, str]:
    config = json.loads(entorno["OPENCODE_CONFIG_CONTENT"])
    modelo = config["model"]
    proveedor, nombre = modelo.split("/", 1)
    precio = config["provider"][proveedor]["models"][nombre].get("cost", {})
    limite = float(entorno.get("CUY_LIMITE_USD", "10"))
    if not math.isfinite(limite) or limite < 0:
        raise ValueError("CUY_LIMITE_USD debe ser finito y no negativo.")
    if limite and not all(type(precio.get(k)) in (int, float) and math.isfinite(precio[k]) and precio[k] > 0
                          for k in ("input", "output")):
        raise ValueError(f"{modelo} no tiene tarifas declaradas. Usá cuy doctor y configurá cost.input/output del contrato.")
    gasto = Path(entorno.get("CUY_GASTO", str(Path.home() / ".local/share/cuy-cli/gasto.json")))
    mes = datetime.now().strftime("%Y-%m")
    if limite and leer_gasto(gasto).get(mes, 0) >= limite:
        raise ValueError("Presupuesto mensual agotado. No se inició la tarea.")
    permiso = {"*": "deny", "read": "allow", "glob": "allow", "grep": "allow", "list": "allow"}
    if flujo == "corregir":
        permiso["edit"] = {"*": "allow", ".git": "deny", ".git/**": "deny"}
    agente = f"cuy-{flujo}"
    config.setdefault("agent", {})[agente] = {
        "mode": "primary", "model": modelo, "steps": 30 if flujo == "corregir" else 15,
        "permission": permiso, "prompt": FLUJOS[flujo] + "\n" + FORMATO,
    }
    return {**entorno, "PWD": str(carpeta), "OPENCODE_CONFIG_CONTENT": json.dumps(config)}, agente


def detener(proceso: subprocess.Popen) -> None:
    """Detiene el proceso creado y sus hijos al cancelar o agotar el tiempo."""
    if proceso.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proceso.pid), "/T", "/F"], capture_output=True, timeout=10)
    else:
        try:
            os.killpg(proceso.pid, signal.SIGTERM)
            proceso.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(proceso.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    proceso.wait(timeout=10)


def ejecutar_proceso(argv: list[str], carpeta: Path, entorno: dict, limite: int,
                     entrada: str | None = None) -> tuple[int, str, bool]:
    # No guardar trazas crudas como historial: pueden incluir texto del proyecto.
    with tempfile.TemporaryFile() as salida, tempfile.TemporaryFile() as errores:
        proceso = subprocess.Popen(argv, cwd=carpeta, env=entorno, stdin=subprocess.PIPE,
                                   stdout=salida, stderr=errores, start_new_session=os.name != "nt")
        timeout = False
        try:
            proceso.communicate(entrada.encode("utf-8") if entrada is not None else None, timeout=limite)
        except subprocess.TimeoutExpired:
            timeout = True
            detener(proceso)
        except KeyboardInterrupt:
            detener(proceso)
            raise
        salida.seek(0)
        texto = salida.read(8 * 1024 * 1024 + 1)
        if len(texto) > 8 * 1024 * 1024:
            raise ValueError("La respuesta excedió 8 MiB; se conserva la tarea para revisión.")
        return proceso.returncode, texto.decode("utf-8", errors="replace"), timeout


def leer_eventos(texto: str) -> dict:
    mensajes, pasos, sesiones = {}, {}, set()
    errores = 0
    for linea in texto.splitlines():
        try:
            evento = json.loads(linea)
        except ValueError:
            continue
        if not isinstance(evento, dict):
            continue
        if evento.get("sessionID"):
            sesiones.add(evento["sessionID"])
        parte = evento.get("part", {})
        if not isinstance(parte, dict):
            continue
        if evento.get("type") == "text" and isinstance(parte.get("text"), str):
            mensajes[parte.get("id", str(len(mensajes)))] = parte["text"]
        if evento.get("type") == "step_finish":
            costo = parte.get("cost")
            if type(costo) in (int, float) and math.isfinite(costo) and costo >= 0:
                pasos[parte.get("id", str(len(pasos)))] = costo
        if evento.get("type") == "error":
            errores += 1
    return {"texto": next(reversed(mensajes.values()), ""), "sesiones": sorted(sesiones),
            "costo_usd": sum(pasos.values()) if pasos else None, "errores_motor": errores}


def validar_entrega(texto: str, carpeta: Path, flujo: str) -> dict:
    limpio = texto.strip()
    if limpio.startswith("```json") and limpio.endswith("```"):
        limpio = limpio[7:-3].strip()
    try:
        entrega = json.loads(limpio)
    except ValueError as exc:
        raise ValueError("El modelo no entregó el informe JSON requerido.") from exc
    if not isinstance(entrega, dict) or not isinstance(entrega.get("resumen"), str) or not entrega["resumen"].strip():
        raise ValueError("Falta un resumen en la entrega.")
    for campo in ("referencias", "hallazgos"):
        items = entrega.get(campo)
        if not isinstance(items, list):
            raise ValueError(f"Falta la lista {campo} en la entrega.")
        if campo == "referencias" and flujo == "entender" and not items:
            raise ValueError("Entender requiere al menos una referencia verificable.")
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("archivo"), str):
                raise ValueError("Referencia sin archivo.")
            relativa = Path(item["archivo"])
            ruta = (carpeta / relativa).resolve()
            if relativa.is_absolute() or not ruta.is_relative_to(carpeta.resolve()) or not ruta.is_file():
                raise ValueError("La entrega referencia un archivo inexistente o fuera del proyecto.")
            linea = item.get("linea")
            if type(linea) is not int or linea < 1 or linea > len(ruta.read_bytes().splitlines()):
                raise ValueError("La entrega referencia una línea inexistente.")
            obligatorios = ("explicacion",) if campo == "referencias" else ("evidencia", "impacto")
            if any(not isinstance(item.get(k), str) or not item[k].strip() for k in obligatorios):
                raise ValueError("La referencia carece de explicación o evidencia.")
            if campo == "hallazgos" and item.get("severidad") not in ("alta", "media", "baja"):
                raise ValueError("Severidad de hallazgo inválida.")
    return {k: entrega[k] for k in ("resumen", "referencias", "hallazgos")}


def entorno_pruebas(entorno: dict, carpeta: Path) -> dict:
    config = entorno.get("OPENCODE_CONFIG_CONTENT", "")
    secretos = set(re.findall(r"\{env:([^}]+)\}", config)) | {"DATABRICKS_TOKEN", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"}
    return {**{k: v for k, v in entorno.items() if k not in secretos
               and not k.startswith(("OPENCODE_", "CUY_"))}, "PWD": str(carpeta), "PYTHONDONTWRITEBYTECODE": "1"}


def correr_tarea(flujo: str, objetivo: str, proyecto: Path, binario: Path, entorno: dict,
                 almacen: Path, pruebas: list[list[str]], limite: int, progreso=lambda texto: None) -> dict:
    proyecto = raiz_git(proyecto)
    if almacen.resolve().is_relative_to(proyecto):
        raise ValueError("CUY_TAREAS debe apuntar fuera del repositorio para no mezclar informes y código.")
    inicial = foto(proyecto)
    if flujo == "corregir" and inicial["estado"]:
        raise ValueError("Hay cambios previos. La corrección aislada parte de HEAD: guardá esos cambios en una rama/commit antes de iniciar. Entender y revisar sí pueden analizar el estado actual.")
    # Validar tarifas/contabilidad antes de crear un worktree o iniciar inferencia.
    preparar_entorno(entorno, flujo, proyecto)
    task_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + uuid4().hex[:8]
    carpeta_tarea = almacen.resolve() / task_id
    carpeta_tarea.mkdir(parents=True, mode=0o700)
    trabajo = carpeta_tarea / "worktree" if flujo == "corregir" else proyecto
    informe = {"version": 1, "id": task_id, "flujo": flujo, "estado": "preparada", "proyecto": str(proyecto),
               "trabajo": str(trabajo), "base": inicial["head"], "inicio": datetime.now(timezone.utc).isoformat(),
               "cambios_previos": bool(inicial["estado"]), "archivos": [], "pruebas": [],
               "sesiones": [], "costo_usd": None, "entrega": None, "motivo": "", "informe": str(carpeta_tarea / "resultado.json")}
    escribir_json(carpeta_tarea / "base.json", inicial)
    escribir_json(Path(informe["informe"]), informe)
    inicio = time.monotonic()
    try:
        if flujo == "corregir":
            progreso("Preparando worktree aislado")
            git(proyecto, "worktree", "add", "--detach", str(trabajo), inicial["head"])
        antes = foto(trabajo)
        env, agente = preparar_entorno(entorno, flujo, trabajo)
        baselines = []
        if pruebas:
            progreso("Ejecutando pruebas sobre la base, antes de editar")
            for argv in pruebas:
                codigo, _, timeout = ejecutar_proceso(argv, trabajo, entorno_pruebas(env, trabajo), limite)
                baselines.append({"codigo": codigo, "timeout": timeout})
            if foto(trabajo) != antes:
                raise ValueError("Las pruebas de base modificaron archivos no ignorados. Se conserva el worktree para inspección.")
        informe["estado"] = "en_curso"
        escribir_json(Path(informe["informe"]), informe)
        progreso(f"Analizando · {flujo}")
        prompt = FLUJOS[flujo] + "\n" + FORMATO + "\nObjetivo del usuario:\n" + objetivo
        codigo, texto, agotado = ejecutar_proceso([str(binario), "run", "--format", "json", "--agent", agente], trabajo, env, limite, prompt)
        eventos = leer_eventos(texto)
        informe.update({k: eventos[k] for k in ("sesiones", "costo_usd")})
        despues = foto(trabajo)
        informe["archivos"] = cambios(antes, despues)
        if flujo != "corregir" and (antes != despues):
            raise ValueError("Se detectaron cambios durante un flujo de lectura; revisar el repositorio.")
        if agotado:
            raise ValueError("Se agotó el tiempo del motor. El trabajo se conserva para inspección.")
        if codigo or eventos["errores_motor"]:
            raise ValueError("El motor devolvió un error. Consultá cuy doctor; no se considera completada la tarea.")
        informe["entrega"] = validar_entrega(eventos["texto"], trabajo, flujo)
        if flujo == "corregir":
            progreso("Verificando cambios y pruebas autorizadas")
            if not informe["archivos"]:
                raise ValueError("El motor no produjo cambios verificables.")
            guardar_diff(trabajo, carpeta_tarea / "cambios.patch")
            informe["diff"] = str(carpeta_tarea / "cambios.patch")
            for argv, baseline in zip(pruebas, baselines):
                codigo, _, timeout = ejecutar_proceso(argv, trabajo, entorno_pruebas(env, trabajo), limite)
                informe["pruebas"].append({"comando": argv, "codigo": codigo, "timeout": timeout,
                                          "antes": baseline["codigo"], "timeout_antes": baseline["timeout"]})
            # No validar cambios adicionales producidos por las pruebas como si el modelo los hubiera verificado.
            if foto(trabajo) != despues:
                raise ValueError("Las pruebas modificaron archivos no ignorados; inspeccioná el worktree antes de aceptar.")
            if foto(proyecto) != inicial:
                raise ValueError("El proyecto original cambió durante la tarea; comprobá los cambios concurrentes.")
            informe["estado"] = "verificada" if pruebas and all(p["codigo"] == 0 and not p["timeout"] for p in informe["pruebas"]) else "sin_verificar"
            if not pruebas:
                informe["motivo"] = "No se indicaron pruebas; los cambios requieren revisión."
            elif informe["estado"] == "sin_verificar":
                informe["motivo"] = "Una o más pruebas fallaron o agotaron el tiempo."
        else:
            informe["estado"] = "entregada"
            informe["motivo"] = "Referencias existentes y sin cambios detectados. Las conclusiones requieren revisión humana."
    except KeyboardInterrupt:
        informe["estado"] = "interrumpida"
        informe["motivo"] = "Cancelada por el usuario; no se reanudará ni aplicará automáticamente."
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        informe["estado"] = "error"
        informe["motivo"] = str(exc)
    finally:
        informe["duracion_s"] = round(time.monotonic() - inicio, 1)
        escribir_json(Path(informe["informe"]), informe)
    return informe


def main(argv=None) -> int:
    import cuy
    from presentacion import mostrar_resultado
    parser = argparse.ArgumentParser(description="Entender, corregir o revisar con un entregable verificable.")
    parser.add_argument("flujo", choices=FLUJOS)
    parser.add_argument("objetivo")
    parser.add_argument("--proyecto", type=Path, default=Path.cwd())
    parser.add_argument("--prueba", action="append", default=[], help="Comando explícito de verificación (sin shell); se puede repetir")
    parser.add_argument("--timeout", type=int, default=600, help="Segundos máximos para el motor y para cada prueba")
    parser.add_argument("--json", action="store_true", help="Informe estructurado, sin decoración")
    args = parser.parse_args(argv)
    if args.timeout < 1 or not args.objetivo.strip():
        parser.error("El objetivo y el timeout deben ser válidos.")
    if args.prueba and args.flujo != "corregir":
        parser.error("--prueba solo corresponde al flujo corregir.")
    pruebas = [shlex.split(p) for p in args.prueba]
    if any(not p for p in pruebas):
        parser.error("--prueba no puede estar vacío")
    try:
        binario = cuy.buscar_binario()
        if not binario:
            raise ValueError("Motor no instalado; ejecutá python instalar.py.")
        progreso = (lambda texto: None) if args.json else (lambda texto: print(f"  · {texto}", flush=True))
        informe = correr_tarea(args.flujo, args.objetivo, args.proyecto, binario, cuy.entorno_agente(),
                               Path(os.environ.get("CUY_TAREAS", Path.home() / ".local/share/cuy-cli/tareas")),
                               pruebas, args.timeout, progreso)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        informe = {"flujo": args.flujo, "estado": "error", "motivo": str(exc)}
    if args.json:
        print(json.dumps(informe, ensure_ascii=False, indent=2))
    else:
        mostrar_resultado(informe)
    return 0 if informe["estado"] in ("verificada", "entregada") else 2 if informe["estado"] == "sin_verificar" else 1
