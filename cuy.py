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
import pathlib
import subprocess
import sys

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
}


def cargar_env() -> None:
    """Carga `.env` sin pisar lo que ya venga del entorno.

    Lo que el usuario exporta a mano manda sobre el archivo: es lo que espera quien
    hace ``CUY_LIMITE_TOKENS=50000 python cuy.py``.
    """
    env = RAIZ / ".env"
    if not env.exists():
        return
    for linea in env.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip())


def buscar_binario() -> pathlib.Path | None:
    """Ubica el ejecutable a usar, prefiriendo el compilado desde el fork propio.

    Orden de preferencia: el descargado de la release, el compilado localmente, y
    por último el de npm. Los dos primeros traen la marca de cuy-cli.

    En Windows npm crea un envoltorio ``.cmd``; en el resto, un enlace sin extensión.

    :returns: Ruta del ejecutable, o ``None`` si no hay ninguno.
    """
    # 1) El descargado desde la release (camino por defecto del instalador).
    descargado = RAIZ / "bin" / ("cuy.exe" if ES_WINDOWS else "cuy")
    if descargado.exists():
        return descargado
    # 2) El compilado acá con --compilar.
    propio = sorted((RAIZ / "vendor" / "opencode" / "packages" / "opencode" / "dist").glob("*/bin/opencode*"))
    if propio:
        return propio[0]
    # 3) El oficial de npm, sin la marca propia.
    base = RAIZ / "node_modules" / ".bin"
    candidatos = [base / "opencode.cmd", base / "opencode.exe"] if ES_WINDOWS else [base / "opencode"]
    return next((c for c in candidatos if c.exists()), None)


def main() -> int:
    cargar_env()
    os.environ.update(BLINDAJE)
    os.environ.setdefault("CUY_LIMITE_TOKENS", "300000")

    binario = buscar_binario()
    if not binario:
        print("OpenCode no está instalado. Corré:")
        print(f"    {'python' if ES_WINDOWS else 'python3'} instalar.py")
        return 1

    try:
        # `shell=True` en Windows porque el envoltorio de npm es un .cmd, que no se
        # puede ejecutar directamente.
        return subprocess.call([str(binario)] + sys.argv[1:], shell=ES_WINDOWS)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
