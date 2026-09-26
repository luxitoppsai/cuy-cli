"""Muestra el gasto acumulado por mes y el tope vigente.

El plugin contabiliza en silencio; esto lo hace visible sin abrir el agente.

Uso::

    python gasto.py
"""

import os
import pathlib
import re

from configuracion import numero_entorno, leer_gasto
from datetime import datetime

CARPETA = pathlib.Path.home() / ".local" / "share" / "cuy-cli"
GASTO = pathlib.Path(os.environ.get("CUY_GASTO", CARPETA / "gasto.json"))
LIMITE = numero_entorno("CUY_LIMITE_USD", 10)


def main() -> int:
    """Punto de entrada de ``cuy gasto``: muestra el acumulado del mes y el tope.

    :returns: Código de salida; 0 aunque todavía no haya gasto registrado.
    """
    if not GASTO.exists():
        print(f"Sin gasto registrado todavía ({GASTO})")
        print("Se empieza a contar al usar el agente.")
        return 0

    try:
        datos = leer_gasto(GASTO)
    except (OSError, ValueError) as exc:
        print(f"No se puede leer el gasto; no se asumirá cero: {exc}")
        return 1
    mes = datetime.now().strftime("%Y-%m")
    actual = float(datos.get(mes, 0))

    print(f"Estimación local ({mes}): ${actual:.4f} | límite ${LIMITE:.2f}")
    if LIMITE > 0:
        porcentaje = actual / LIMITE * 100
        lleno = int(min(porcentaje, 100) / 5)
        print(f"  [{'█' * lleno}{'·' * (20 - lleno)}] {porcentaje:.0f}%")
        if actual >= LIMITE:
            print("  Tope alcanzado: el agente bloquea nuevas inferencias y herramientas hasta el mes que viene.")

    otros = {k: v for k, v in datos.items() if k != mes and re.fullmatch(r"\d{4}-\d{2}", k)}
    if otros:
        print("\nMeses anteriores:")
        for k in sorted(otros, reverse=True)[:6]:
            print(f"  {k}: ${float(otros[k]):.2f}")

    usd_dbu = os.environ.get("CUY_USD_POR_DBU", "0.07")
    print(f"\nReferencia: ${usd_dbu}/DBU; depende de las tarifas configuradas por modelo.")
    print("No es una factura: solo incluye pasos registrados por esta instalación.")
    print("No incluye necesariamente sondeos de instalación, solicitudes fallidas, otros equipos ni cargos del gateway.")
    print("Ejecutá cuy costos para auditar las tarifas y compararlas con el gasto real del mismo alcance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
