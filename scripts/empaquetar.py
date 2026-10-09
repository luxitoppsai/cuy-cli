"""Prepara una distribución sin fuentes en el sistema donde se ejecuta."""

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import sysconfig

RAIZ = Path(__file__).resolve().parents[1]


def preparar(version: str, motor: Path, presupuesto: float, salida: Path) -> Path:
    """Congela el lanzador y comprueba política y contenido antes de archivar.

    :param version: Versión fija del paquete.
    :param motor: Motor compilado para el sistema y arquitectura de este Python.
    :param presupuesto: Importe positivo aprobado por el mantenedor al preparar.
    :param salida: Carpeta de artefactos de distribución.
    :returns: Archivo ZIP instalable.
    """
    if not math.isfinite(presupuesto) or presupuesto <= 0:
        raise ValueError("El presupuesto de distribución debe ser positivo y finito.")
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){2}(?:-[A-Za-z0-9.-]+)?", version):
        raise ValueError("Usá una versión semántica fija.")
    resultado = subprocess.run([str(motor.resolve()), "--cuy-policy"], check=True,
                               capture_output=True, text=True, timeout=180 if os.name == "nt" else 30)
    politica = json.loads(resultado.stdout)
    if politica != {"bundled": True, "budget": presupuesto}:
        raise ValueError("El motor no incorpora los plugins o el presupuesto de esta distribución.")
    sistema = {"Darwin": "darwin", "Windows": "windows", "Linux": "linux"}[platform.system()]
    arquitectura = {"x86_64": "x64", "AMD64": "x64", "arm64": "arm64", "aarch64": "arm64"}[platform.machine()]
    if arquitectura_motor(motor) != arquitectura:
        raise ValueError("El motor y el runtime Python no tienen la misma arquitectura.")
    carpeta = salida / f"cuy-{version}-{sistema}-{arquitectura}"
    if carpeta.exists():
        raise ValueError("La carpeta de distribución ya existe. Elegí otra salida o versión.")
    trabajo = salida / f"build-{version}-{sistema}-{arquitectura}"
    trabajo.mkdir(parents=True, exist_ok=True)
    # Only the staging entry point's directory overrides politica; no source-tree mutation.
    (trabajo / "politica.py").write_text(f"LIMITE_USD = {presupuesto!r}\n", encoding="utf-8")
    shutil.copy2(RAIZ / "aplicacion.py", trabajo / "entrada.py")
    nombre = "cuy.exe" if sistema == "windows" else "cuy"
    recursos = trabajo / "recursos"
    recursos.mkdir(exist_ok=True)
    for origen in ("codegraph-release.json", "instrucciones", "tema"):
        ruta = RAIZ / origen
        if ruta.is_dir():
            shutil.copytree(ruta, recursos / origen, dirs_exist_ok=True)
        else:
            shutil.copy2(ruta, recursos / origen)
    licencias = recursos / "licencias"
    licencias.mkdir(exist_ok=True)
    shutil.copy2(RAIZ / "vendor/opencode/LICENSE", licencias / "OpenCode.txt")
    licencia_python = Path(sysconfig.get_path("stdlib")) / "LICENSE.txt"
    if not licencia_python.is_file():
        licencia_python = Path(sys.base_prefix) / "LICENSE.txt"
    if not licencia_python.is_file():
        raise ValueError("Falta la licencia del runtime Python; no se prepara el paquete.")
    shutil.copy2(licencia_python, licencias / "Python.txt")
    instalador = importlib.metadata.distribution("pyinstaller")
    for fichero in instalador.files or []:
        if fichero.name in ("COPYING.txt", "LICENSE.txt"):
            shutil.copy2(instalador.locate_file(fichero), licencias / f"PyInstaller-{fichero.name}")
    comando = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onedir", "--console",
               "--name", "cuy", "--paths", str(RAIZ), "--distpath", str(trabajo / "dist"),
               "--workpath", str(trabajo / "work"), "--specpath", str(trabajo),
               "--add-data", f"{recursos}{os.pathsep}.",
               "--add-binary", f"{motor.resolve()}{os.pathsep}motor", str(trabajo / "entrada.py")]
    subprocess.run(comando, cwd=trabajo, check=True)
    shutil.move(trabajo / "dist/cuy", carpeta)
    incorporado = carpeta / "_internal/motor" / motor.name
    destino_motor = incorporado.with_name(nombre)
    if incorporado != destino_motor:
        incorporado.rename(destino_motor)
    (carpeta / "LEEME.txt").write_text(
        "Cuy — instalación sin repositorio ni Python externo\n\n"
        "1. Conservá esta carpeta completa, incluido _internal.\n"
        "2. En una terminal ejecutá ./cuy instalar (Windows: .\\cuy.exe instalar).\n"
        "3. Usá la ruta instalada que muestra el comando y ejecutá cuy configurar.\n"
        "4. Abrí Cuy desde la carpeta de tu proyecto. Git se requiere para operaciones Git.\n\n"
        "cuy configurar solicita el token de forma oculta. No lo compartas.\n"
        "cuy gasto muestra el consumo y presupuesto de la distribución.\n"
        "cuy doctor permite diagnosticar sin llamar al modelo.\n"
        "Para actualizar, instalá el paquete nuevo: los datos se conservan.\n",
        encoding="utf-8",
    )
    # Imported Python modules are bytecode in PYZ, never shipped as .py source files.
    if any(p.suffix in (".py", ".js", ".ts") for p in carpeta.rglob("*")):
        raise ValueError("El paquete contiene fuentes inesperadas; no se publica.")
    subprocess.run([str(carpeta / nombre), "--version"], check=True, timeout=180 if os.name == "nt" else 30)
    archivo = Path(shutil.make_archive(str(carpeta), "zip", root_dir=carpeta.parent, base_dir=carpeta.name))
    manifiesto = {"version": version, "platform": f"{sistema}-{arquitectura}",
                  "artifact": archivo.name, "sha256": hashlib.sha256(archivo.read_bytes()).hexdigest()}
    archivo.with_suffix(".json").write_text(json.dumps(manifiesto, indent=2) + "\n", encoding="utf-8")
    return archivo


def arquitectura_motor(motor: Path) -> str:
    """Lee el encabezado nativo para no distribuir motores incompatibles con el runtime."""
    with motor.open("rb") as archivo:
        cabecera = archivo.read(64)
        if len(cabecera) < 64:
            raise ValueError("El motor no tiene un formato ejecutable reconocido: encabezado incompleto.")
        if cabecera[:4] == b"\x7fELF":
            endian = "little" if cabecera[5] == 1 else "big"
            cpu = int.from_bytes(cabecera[18:20], endian)
            return {62: "x64", 183: "arm64"}.get(cpu, "desconocida")
        if cabecera[:4] in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf"):
            endian = "little" if cabecera[0] == 0xcf else "big"
            cpu = int.from_bytes(cabecera[4:8], endian)
            return {0x1000007: "x64", 0x100000c: "arm64"}.get(cpu, "desconocida")
        if cabecera[:2] == b"MZ":
            archivo.seek(int.from_bytes(cabecera[60:64], "little"))
            pe = archivo.read(6)
            if pe[:4] == b"PE\x00\x00":
                return {0x8664: "x64", 0xaa64: "arm64"}.get(int.from_bytes(pe[4:6], "little"), "desconocida")
    raise ValueError("El motor no tiene un formato ejecutable reconocido.")


def main() -> None:
    """Procesa opciones exclusivas del mantenedor; no se incluye en el paquete."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("--motor", required=True, type=Path)
    parser.add_argument("--presupuesto-usd", type=float, default=10)
    parser.add_argument("--salida", type=Path, default=RAIZ / "dist-release")
    args = parser.parse_args()
    print(preparar(args.version, args.motor, args.presupuesto_usd, args.salida.resolve()))


if __name__ == "__main__":
    main()
