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

    print(f"\nPrecios: {'declarados en ' + str(PRECIOS) if PRECIOS.exists() else 'estimados con tarifas públicas de Anthropic'}")
    if not PRECIOS.exists():
        print("  Para usar los de tu contrato, creá ese archivo:")
        print('  {"databricks-claude-opus-4-1": {"entrada": 15, "salida": 75}}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
