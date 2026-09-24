"""Muestra qué binario se está usando y por qué, para no adivinar.

La pregunta típica es "¿por qué sigo viendo el logo de OpenCode?", y la respuesta
siempre está en cuál de los tres binarios posibles eligió el lanzador.

Uso::

    python diagnostico.py
"""

import os
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
import cuy  # noqa: E402


def main() -> int:
    print("cuy-cli — diagnóstico\n")
    print(f"Sistema       : {os.name} ({sys.platform})")
    print(f"Carpeta       : {RAIZ}")
    print()

    descargado = RAIZ / "bin" / ("cuy.exe" if cuy.ES_WINDOWS else "cuy")
    compilado = sorted((RAIZ / "vendor" / "opencode" / "packages" / "opencode" / "dist").glob("*/bin/opencode*"))
    base_npm = RAIZ / "node_modules" / ".bin"
    npm = [c for c in (base_npm / "opencode.cmd", base_npm / "opencode.exe", base_npm / "opencode") if c.exists()]

    print("Binarios disponibles:")
    marca = lambda existe: "✓" if existe else "·"
    print(f"  {marca(descargado.exists())} descargado : {descargado}")
    print(f"  {marca(bool(compilado))} compilado  : {compilado[0] if compilado else '(no hay)'}")
    print(f"  {marca(bool(npm))} de npm     : {npm[0] if npm else '(no hay)'}")
    print()

    elegido = cuy.buscar_binario()
    if not elegido:
        print("Ninguno instalado. Corré:  python instalar.py")
        return 1

    print(f"El lanzador usa : {elegido}")
    tiene_marca = "node_modules" not in str(elegido)
    print(f"Marca esperada  : {'cuy-cli' if tiene_marca else 'OpenCode (binario de npm)'}")
    print()

    # La prueba definitiva: preguntarle al binario, en vez de deducirlo de la ruta.
    print("Lo que imprime el binario:")
    try:
        entorno = {**os.environ, **cuy.BLINDAJE}
        salida = subprocess.run([str(elegido), "--help"], capture_output=True, text=True,
                                timeout=60, shell=cuy.ES_WINDOWS, env=entorno)
        for linea in (salida.stdout or salida.stderr or "").splitlines()[:5]:
            print(f"  {linea}")
    except Exception as e:
        print(f"  (no se pudo ejecutar: {e})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
