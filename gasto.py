"""Muestra el gasto acumulado por mes y el tope vigente.

El plugin contabiliza en silencio; esto lo hace visible sin abrir el agente.

Uso::

    python gasto.py
"""

import json
import os
import pathlib
from datetime import datetime

CARPETA = pathlib.Path.home() / ".local" / "share" / "cuy-cli"
GASTO = pathlib.Path(os.environ.get("CUY_GASTO", CARPETA / "gasto.json"))
LIMITE = float(os.environ.get("CUY_LIMITE_USD", "10"))


def main() -> int:
    if not GASTO.exists():
        print(f"Sin gasto registrado todavía ({GASTO})")
        print("Se empieza a contar al usar el agente.")
        return 0

    datos = json.loads(GASTO.read_text())
    mes = datetime.now().strftime("%Y-%m")
    actual = float(datos.get(mes, 0))

    print(f"Mes en curso ({mes}): ${actual:.2f} de ${LIMITE:.2f}")
    if LIMITE > 0:
        porcentaje = actual / LIMITE * 100
        lleno = int(min(porcentaje, 100) / 5)
        print(f"  [{'█' * lleno}{'·' * (20 - lleno)}] {porcentaje:.0f}%")
        if actual >= LIMITE:
            print("  Tope alcanzado: el agente no ejecuta herramientas hasta el mes que viene.")

    otros = {k: v for k, v in datos.items() if k != mes}
    if otros:
        print("\nMeses anteriores:")
        for k in sorted(otros, reverse=True)[:6]:
            print(f"  {k}: ${float(otros[k]):.2f}")

    usd_dbu = os.environ.get("CUY_USD_POR_DBU", "0.07")
    print(f"\nTarifas: declaradas en opencode.json  |  ${usd_dbu} por DBU")
    print("  Databricks cobra en DBU por millón de tokens, no en dólares por token.")
    print("  Para cambiarlas: editá DBU_POR_MILLON en generar_config.py, o corré")
    print("  CUY_USD_POR_DBU=0.05 python generar_config.py  si tu contrato no es 0.07.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
