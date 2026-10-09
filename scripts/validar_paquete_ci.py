"""Empaqueta y ejecuta contratos nativos sin publicar una release."""

import os
from pathlib import Path
import subprocess
import sys
import hashlib
import json
import shutil
import tempfile

from empaquetar import preparar, RAIZ


def main() -> None:
    """Verifica el motor y la distribución producidos por el runner nativo."""
    nombre = "opencode.exe" if os.name == "nt" else "opencode"
    candidatos = list((RAIZ / "vendor/opencode/packages/opencode/dist").glob(f"*/bin/{nombre}"))
    if len(candidatos) != 1:
        raise ValueError("Se esperaba un único motor nativo recién compilado.")
    motor = candidatos[0].resolve()
    presupuesto = float(os.environ.get("CUY_BUILD_PRESUPUESTO_USD", "10"))
    archivo = preparar(os.environ["OPENCODE_VERSION"], motor, presupuesto, RAIZ / "dist-release")
    ejecutable = archivo.with_suffix("") / ("cuy.exe" if os.name == "nt" else "cuy")
    entorno = {**os.environ, "CUY_TEST_BINARIO": str(motor), "CUY_TEST_PAQUETE": str(ejecutable),
               "CUY_TEST_PRESUPUESTO_USD": str(presupuesto)}
    for prueba in ("test_motor.py", "test_distribucion.py"):
        subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", prueba],
                       cwd=RAIZ, env=entorno, check=True)
    if os.name == "nt" and "windows-x64" in archivo.name:
        compilador = shutil.which("ISCC.exe")
        if not compilador:
            candidato = Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6/ISCC.exe"
            compilador = str(candidato) if candidato.is_file() else None
        if not compilador:
            raise ValueError("Falta Inno Setup 6 para producir el instalador de Windows.")
        version = os.environ["OPENCODE_VERSION"]
        subprocess.run([compilador, f"/DVersion={version}", f"/DFileVersion={version.split('-')[0]}", f"/DPackage={archivo.with_suffix('')}",
                        f"/DOutput={archivo.parent}", str(RAIZ / "scripts/cuy-windows.iss")], check=True)
        instalador = archivo.parent / f"cuy-instalar-{version}-windows-x64.exe"
        with tempfile.TemporaryDirectory(prefix="cuy-instalar-ci-") as temp:
            subprocess.run([str(instalador), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                            f"/DIR={temp}"], check=True, timeout=180)
            subprocess.run([str(Path(temp) / "cuy.exe"), "--version"], check=True, timeout=60)
        instalador.with_suffix(".json").write_text(json.dumps({"version": version,
            "artifact": instalador.name, "sha256": hashlib.sha256(instalador.read_bytes()).hexdigest()}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
