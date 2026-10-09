"""Entrada del paquete compilado: instalación, configuración y conversación libre."""

import argparse
import os
from pathlib import Path
import shutil
import sys

from distribucion import datos, politica_entorno


def instalar_aplicacion(origen: Path, destino: Path) -> Path:
    """Instala el paquete completo sin modificar credenciales ni gasto del usuario.

    :param origen: Directorio que contiene el ejecutable y su runtime.
    :param destino: Directorio de aplicación dentro de los datos del usuario.
    :returns: Ruta del lanzador instalado.
    """
    nombre = "cuy.exe" if sys.platform == "win32" else "cuy"
    if not (origen / nombre).is_file() or not (origen / "_internal" / "motor").is_dir():
        raise ValueError("Paquete incompleto. Descargá y extraé nuevamente la distribución de Cuy.")
    if origen.resolve() != destino.resolve():
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(origen, destino, dirs_exist_ok=True)
    return destino / nombre


def configurar(argumentos: list[str]) -> int:
    """Configura Databricks usando las utilidades incorporadas al ejecutable."""
    import instalar
    import cuy

    parser = argparse.ArgumentParser(description="Configurar la conexión de Cuy a Databricks")
    parser.add_argument("--host")
    parser.add_argument("--renovar-token", action="store_true")
    parser.add_argument("--rapido", action="store_true")
    parser.add_argument("--sin-verificar", action="store_true")
    args = parser.parse_args(argumentos)
    datos().mkdir(parents=True, exist_ok=True)
    host = instalar.resolver_host(args.host)
    token = instalar.resolver_credencial(args.renovar_token)
    config = instalar.generar(host, token, args.rapido)
    if not cuy.buscar_binario():
        raise ValueError("Falta el motor incorporado. Reinstalá el paquete de Cuy.")
    if not args.sin_verificar and not instalar.verificar(host, token, config):
        print("La conexión quedó configurada, pero no se confirmó respuesta. Ejecutá cuy doctor.")
        return 1
    print("Configuración guardada. Abrí Cuy desde la carpeta del proyecto.")
    return 0


def main() -> int:
    """Despacha operaciones del ejecutable sin depender de intérpretes externos."""
    # Frozen Python ignores PYTHONUTF8; pipes on Windows otherwise use the ANSI code page.
    for flujo in (sys.stdin, sys.stdout, sys.stderr):
        if flujo is not None:
            flujo.reconfigure(encoding="utf-8")
    politica_entorno()
    argumentos = sys.argv[1:]
    try:
        if argumentos[:1] == ["_codegraph"]:
            if len(argumentos) != 3:
                raise ValueError("Argumentos MCP inválidos")
            from codegraph import servir
            return servir(Path(argumentos[1]).resolve(), Path(argumentos[2]).resolve())
        if argumentos[:1] == ["instalar"]:
            parser = argparse.ArgumentParser(description="Instalar Cuy para este usuario")
            parser.parse_args(argumentos[1:])
            ejecutable = instalar_aplicacion(Path(sys.executable).parent, datos() / "app")
            print(f"Cuy instalado: {ejecutable}")
            print(f'Configurá la conexión: "{ejecutable}" configurar')
            print("Podés añadir la carpeta de ese ejecutable al PATH para usar cuy desde cualquier proyecto.")
            return 0
        if argumentos[:1] == ["configurar"]:
            return configurar(argumentos[1:])
        if argumentos[:1] == ["upgrade"]:
            print("Descargá el nuevo paquete de tu equipo y ejecutá cuy instalar. Los datos se conservan.")
            return 0
        if not (datos() / "opencode.json").is_file() and not any(a in ("--help", "-h", "--version", "-v") for a in argumentos) and argumentos[:1] not in (["doctor"], ["inicio"], ["demo"], ["gasto"]):
            print("Configurá la conexión primero: cuy configurar --host https://TU-WORKSPACE")
            return 1
        import cuy
        # Version and help do not need credentials, config, index or inference.
        if any(a in ("--help", "-h", "--version", "-v") for a in argumentos):
            import subprocess
            motor = cuy.buscar_binario()
            if motor is None:
                raise ValueError("Paquete incompleto. Reinstalá Cuy.")
            if argumentos in (["--help"], ["-h"]):
                print("Comandos de distribución: instalar · configurar [--host URL] [--renovar-token]", flush=True)
            return subprocess.call([str(motor), *argumentos], env={**os.environ, **cuy.BLINDAJE})
        return cuy.main()
    except (OSError, ValueError, KeyError) as exc:
        print(f"No se pudo iniciar Cuy: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
