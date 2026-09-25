"""Lanza OpenCode en modo blindado, en cualquier sistema.

La lógica vive acá y no en un script de shell porque el destino de este proyecto es una
máquina **Windows**, donde un `.sh` no se ejecuta. Python ya es requisito del instalador,
así que un único lanzador sirve para los tres sistemas y no hay dos versiones que
mantener en paralelo.

**Qué hace y por qué.** Sin estas variables, OpenCode contacta `api.opencode.ai` en cada
sesión aunque el proveedor configurado sea propio (medido; ver `spike/RED.md`). El
lanzador las aplica siempre, porque depender de que cada persona exporte seis variables
es depender de que nadie se olvide nunca.

Uso::

    python cuy.py                      # sesión interactiva
    python cuy.py run "arreglá el test"

En macOS y Linux también sirve ``./cuy``; en Windows, ``cuy.cmd``.
"""

import os
import json
import pathlib
import subprocess
import sys

from configuracion import numero_entorno, cargar_archivo_env, validar_token
from ejecutables import validar_windows

RAIZ = pathlib.Path(__file__).resolve().parent
ES_WINDOWS = os.name == "nt"

# Cada variable cierra una salida de red distinta. La más importante es la de compartir:
# subiría la conversación —con el código adentro— a un servidor de terceros.
BLINDAJE = {
    "OPENCODE_DISABLE_AUTOUPDATE": "1",   # evita la llamada a api.opencode.ai
    "OPENCODE_DISABLE_MODELS_FETCH": "1",  # el catálogo lo genera generar_config.py
    "OPENCODE_DISABLE_SHARE": "1",
    "OPENCODE_AUTO_SHARE": "0",
    "OPENCODE_DISABLE_LSP_DOWNLOAD": "1",
    "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
    "OPENCODE_DISABLE_PROJECT_CONFIG": "1",
}


def cargar_env() -> None:
    """Carga `.env` sin pisar lo que ya venga del entorno.

    Lo que el usuario exporta a mano manda sobre el archivo: es lo que espera quien
    hace ``CUY_LIMITE_USD=5 python cuy.py``.
    """
    cargar_archivo_env(RAIZ / ".env")
    if os.environ.get("DATABRICKS_TOKEN"):
        os.environ["DATABRICKS_TOKEN"] = validar_token(os.environ["DATABRICKS_TOKEN"])


def buscar_binario() -> pathlib.Path | None:
    """Ubica el ejecutable a usar, prefiriendo el compilado desde el fork propio.

    Respeta la selección persistida por el instalador. En instalaciones anteriores,
    conserva la preferencia histórica: descarga, compilado y paquete npm.
    Ejecuta el binario nativo directamente, sin pasar prompts por cmd.exe.

    :returns: Ruta del ejecutable, o ``None`` si no hay ninguno.
    """
    seleccion = RAIZ / "bin" / "seleccion.json"
    if seleccion.exists():
        elegido = pathlib.Path(json.loads(seleccion.read_text(encoding="utf-8"))["path"])
        if not elegido.is_file():
            raise ValueError("El ejecutable seleccionado ya no existe; repetí la instalación.")
        return validar_windows(elegido) if ES_WINDOWS else elegido
    # Compatibilidad con instalaciones anteriores.
    descargado = RAIZ / "bin" / ("cuy.exe" if ES_WINDOWS else "cuy")
    if descargado.exists():
        return validar_windows(descargado) if ES_WINDOWS else descargado
    # 2) El compilado acá con --compilar.
    propio = sorted((RAIZ / "vendor" / "opencode" / "packages" / "opencode" / "dist").glob("*/bin/opencode*"))
    if ES_WINDOWS:
        propio = [p for p in propio if p.suffix.lower() == ".exe"
                  and p.parent.parent.name.startswith("opencode-windows-")]
    if propio:
        return validar_windows(propio[0]) if ES_WINDOWS else propio[0]
    # 3) El oficial de npm, sin la marca propia.
    base = RAIZ / "node_modules" / ".bin"
    candidatos = [RAIZ / "node_modules" / "opencode-ai" / "bin" / "opencode.exe"]
    if not ES_WINDOWS:
        candidatos.append(base / "opencode")
    encontrado = next((c for c in candidatos if c.is_file()), None)
    return validar_windows(encontrado) if ES_WINDOWS and encontrado else encontrado


def entorno_agente() -> dict:
    """Aplica la configuración de Cuy sin cambiar el directorio de trabajo."""
    from generar_config import construir_permisos, permisos_lectura

    numero_entorno("CUY_LIMITE_USD", 10)
    numero_entorno("CUY_USD_POR_DBU", 0.07)
    config_path = RAIZ / "opencode.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    # Migra también las instalaciones anteriores sin volver a sondear la red.
    config["permission"] = construir_permisos()
    lectura = permisos_lectura()
    agentes = config.setdefault("agent", {})
    for nombre in ("plan", "explore"):
        agente = agentes.setdefault(nombre, {})
        agente["permission"] = dict(lectura)
        agente["steps"] = 15
    agentes["plan"]["model"] = config["model"]
    agentes["explore"]["mode"] = "subagent"
    agentes["scout"] = {"disable": True}
    agentes.setdefault("build", {})["steps"] = 30
    config["share"] = "disabled"
    config["enabled_providers"] = list(config["provider"])
    config["plugin"] = [(RAIZ / "plugin" / f"{nombre}.js").as_uri()
                        for nombre in ("presupuesto", "auditoria", "secretos")]
    entorno = {**os.environ, **BLINDAJE}
    entorno["PWD"] = str(pathlib.Path.cwd())
    entorno.pop("OPENCODE_CONFIG_DIR", None)
    entorno["OPENCODE_CONFIG"] = str(config_path)
    entorno["OPENCODE_CONFIG_CONTENT"] = json.dumps(config)
    entorno.setdefault("CUY_LIMITE_USD", "10")
    return entorno


def main() -> int:
    cargar_env()
    if sys.argv[1:2] == ["tarea"]:
        from tareas import main as tarea
        return tarea(sys.argv[2:])
    if sys.argv[1:2] == ["inicio"]:
        from presentacion import inicio
        return inicio()
    if sys.argv[1:2] == ["demo"]:
        from presentacion import demo
        return demo(sys.argv[2:])
    if sys.argv[1:2] == ["doctor"]:
        from diagnostico import main as doctor
        return doctor(sys.argv[2:])
    if sys.argv[1:2] == ["gasto"]:
        from gasto import main as gasto
        return gasto()

    try:
        binario = buscar_binario()
    except (OSError, ValueError, KeyError) as exc:
        print(f"No se pudo seleccionar el ejecutable: {exc}", file=sys.stderr)
        return 1
    if not binario:
        print("OpenCode no está instalado. Corré:")
        print(f"    {'python' if ES_WINDOWS else 'python3'} instalar.py")
        return 1

    try:
        return subprocess.call([str(binario)] + sys.argv[1:], env=entorno_agente())
    except (OSError, ValueError, KeyError) as exc:
        print(f"No se pudo iniciar Cuy: {exc}", file=sys.stderr)
        if getattr(exc, "winerror", None) in (193, 216):
            print("Windows rechazó el formato o la arquitectura del agente. "
                  "Ejecutá: python instalar.py --reparar-motor", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
