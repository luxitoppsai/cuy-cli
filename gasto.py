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
PRECIOS = pathlib.Path(os.environ.get("CUY_PRECIOS", CARPETA / "precios.json"))
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
    print(f"\nTarifas: {'declaradas en ' + str(PRECIOS) if PRECIOS.exists() else 'estimadas'}"
          f"  |  ${usd_dbu} por DBU")
    if not PRECIOS.exists():
        print("  Databricks cobra en DBU por millón de tokens, no en dólares por token.")
        print("  Para usar las de tu contrato, creá ese archivo (valores en DBU):")
        print('  {"databricks-claude-opus-4-1": {"entrada": 214.286, "salida": 1071.43}}')
        print("  Y si tu dólar por DBU no es 0.07:  CUY_USD_POR_DBU=0.05")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
