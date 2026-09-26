"""Diagnóstico local sin inferencia. `cuy doctor --verificar` prueba el proveedor."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

import cuy
from configuracion import numero_entorno, validar_host, leer_gasto


def diagnosticar() -> dict:
    """Revisa que la instalación esté completa y utilizable.

    Cada control se ejecuta aunque el anterior falle, para que un solo diagnóstico
    muestre todo lo que hay que arreglar en vez de la primera causa.

    :returns: ``{"controles": [...], "ok": bool}``.
    """
    checks = []

    def anotar(nombre, ok, detalle):
        """Agrega el resultado de un control a la lista.

        :param nombre: Qué se comprobó.
        :param ok: Si pasó.
        :param detalle: Explicación o siguiente paso.
        """
        checks.append({"control": nombre, "ok": ok, "detalle": detalle})

    try:
        binario = cuy.buscar_binario()
        anotar("ejecutable", bool(binario), str(binario or "Ejecutá python instalar.py"))
    except (OSError, ValueError, KeyError) as exc:
        binario = None
        anotar("ejecutable", False, str(exc))
    config = None
    try:
        entorno = cuy.entorno_agente()
        config = json.loads(entorno["OPENCODE_CONFIG_CONTENT"])
        anotar("configuración", True, str(cuy.RAIZ / "opencode.json"))
        anotar("modelo principal", bool(config.get("model")), config.get("model", "ausente"))
        for pid, proveedor in config["provider"].items():
            from urllib.parse import urlsplit
            url = urlsplit(proveedor["options"]["baseURL"])
            validar_host(f"{url.scheme}://{url.netloc}")
            sin_tarifa = [m for m, data in proveedor["models"].items()
                          if not all(isinstance(data.get("cost", {}).get(k), (int, float))
                                     and data["cost"][k] > 0 for k in ("input", "output"))]
            anotar(f"tarifas {pid}", not sin_tarifa or numero_entorno("CUY_LIMITE_USD", 10) == 0,
                   "Faltan: " + ", ".join(sin_tarifa) if sin_tarifa else "Declaradas; estimaciones según contrato")
        for nombre in ("presupuesto", "auditoria", "secretos"):
            archivo = cuy.RAIZ / "plugin" / f"{nombre}.js"
            anotar(f"plugin {nombre}", archivo.is_file(), str(archivo))
        anotar("permisos", True, "plan/explore: solo lectura; proyecto no sobreescribe la política de Cuy")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        anotar("configuración", False, str(exc))
    anotar("credencial", bool(os.environ.get("DATABRICKS_TOKEN")),
           "Presente (valor oculto)" if os.environ.get("DATABRICKS_TOKEN") else "Falta DATABRICKS_TOKEN")
    archivo = Path(os.environ.get("CUY_GASTO", Path.home() / ".local/share/cuy-cli/gasto.json"))
    try:
        leer_gasto(archivo)
        anotar("contabilidad", True, str(archivo))
        anotar("lock contable", not Path(str(archivo) + ".lock").exists(),
               "Si persiste, verificá que no haya sesiones activas antes de recuperarlo")
    except (OSError, ValueError) as exc:
        anotar("contabilidad", False, str(exc))
    if binario:
        try:
            salida = subprocess.run([str(binario), "--version"], env={**os.environ, **cuy.BLINDAJE},
                                    capture_output=True, text=True, timeout=20, encoding="utf-8")
            anotar("versión del motor", salida.returncode == 0, salida.stdout.strip() or "No respondió")
        except (OSError, subprocess.TimeoutExpired) as exc:
            anotar("versión del motor", False, type(exc).__name__)
    return {"ok": all(c["ok"] for c in checks), "proyecto": str(Path.cwd()), "controles": checks}


def main(argv=None) -> int:
    """Punto de entrada de ``cuy doctor``: imprime el diagnóstico de la instalación.

    :returns: Código de salida; distinto de 0 si algún control falló.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Salida apta para soporte/CI, sin credenciales")
    parser.add_argument("--verificar", action="store_true", help="Hacer una llamada real y facturable al modelo")
    args = parser.parse_args(argv)
    cuy.cargar_env()
    reporte = diagnosticar()
    if args.verificar and reporte["ok"]:
        import instalar
        import contextlib
        config = json.loads(cuy.entorno_agente()["OPENCODE_CONFIG_CONTENT"])
        proveedor = config["provider"][config["model"].split("/", 1)[0]]
        # Los detalles de la respuesta remota no se incluyen en el informe compartible.
        with contextlib.redirect_stdout(sys.stderr):
            ok = instalar.verificar(proveedor["options"]["baseURL"], os.environ["DATABRICKS_TOKEN"], config)
        reporte["controles"].append({"control": "inferencia", "ok": ok, "detalle": "Contrato del proveedor"})
        reporte["ok"] &= ok
    if args.json:
        print(json.dumps(reporte, ensure_ascii=False, indent=2))
    else:
        print(f"Cuy — proyecto: {reporte['proyecto']}")
        for check in reporte["controles"]:
            print(f"{'OK' if check['ok'] else 'ERROR'}  {check['control']}: {check['detalle']}")
        print("Diagnóstico local: no acredita firewall, carga efectiva de hooks ni gobierno del servidor.")
    return 0 if reporte["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
