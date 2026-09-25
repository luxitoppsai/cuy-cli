"""Lee el registro de auditoría y responde las preguntas que uno se hace de verdad.

Un JSONL sin forma de consultarlo no es auditoría, es un archivo. Esto responde: quién
usó el agente, qué comandos corrió, qué archivos tocó y qué bloqueó la política.

Uso::

    python3 auditar.py                    # resumen de los últimos 7 días
    python3 auditar.py --dias 30
    python3 auditar.py --usuario luis
    python3 auditar.py --comandos          # todos los comandos ejecutados
    python3 auditar.py --archivos          # todos los archivos modificados

Sin dependencias.
"""

import argparse
import collections
import json
import os
import pathlib
from datetime import datetime, timedelta, timezone

DESTINO = pathlib.Path(
    os.environ.get("CUY_AUDITORIA", pathlib.Path.home() / ".local/share/cuy-cli/auditoria.jsonl")
)


def leer(ruta: pathlib.Path, dias: int, usuario: str | None) -> list[dict]:
    """Carga las entradas del registro dentro del período pedido.

    Las líneas ilegibles se saltan en silencio: un registro al que se le apendea desde
    varias sesiones puede quedar con una línea a medias, y eso no debe impedir leer el
    resto.

    :param ruta: Archivo JSONL.
    :param dias: Ventana hacia atrás; 0 trae todo.
    :param usuario: Si se indica, filtra por esa persona.
    :returns: Entradas ordenadas por fecha.
    """
    if not ruta.exists():
        return []
    desde = datetime.now(timezone.utc) - timedelta(days=dias) if dias else None
    entradas = []
    for linea in ruta.read_text(errors="replace").splitlines():
        if not linea.strip():
            continue
        try:
            entrada = json.loads(linea)
            cuando = datetime.fromisoformat(entrada["cuando"].replace("Z", "+00:00"))
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            continue
        if cuando.tzinfo is None:
            cuando = cuando.replace(tzinfo=timezone.utc)
        if desde and cuando < desde:
            continue
        if usuario and entrada.get("usuario") != usuario:
            continue
        entrada["_cuando"] = cuando
        entradas.append(entrada)
    return sorted(entradas, key=lambda e: e["_cuando"])


def deduplicar(entradas: list[dict]) -> list[dict]:
    vistos = set()
    resultado = []
    for entrada in entradas:
        if entrada.get("evento") == "herramienta.resultado":
            clave = (entrada.get("sesion"), entrada.get("llamada"), entrada.get("estado"))
            if clave in vistos:
                continue
            vistos.add(clave)
        resultado.append(entrada)
    return resultado


def resumir(entradas: list[dict]) -> None:
    """Imprime el panorama general: quién, cuánto y qué se bloqueó."""
    if not entradas:
        print("Sin actividad registrada en el período.")
        return

    entradas = deduplicar(entradas)
    sesiones = {e["sesion"] for e in entradas if e.get("sesion")}
    sesiones_por_usuario = collections.defaultdict(set)
    for entrada in entradas:
        if entrada.get("sesion"):
            sesiones_por_usuario[entrada.get("usuario", "?")].add(entrada["sesion"])
    por_usuario = collections.Counter({u: len(s) for u, s in sesiones_por_usuario.items()})
    herramientas = collections.Counter(
        e.get("herramienta") for e in entradas if e.get("evento") == "herramienta.resultado" and e.get("estado") == "completed"
    )
    permisos = [e for e in entradas if e.get("evento") == "permiso.consultado"]
    intentos = sum(e.get("evento") == "herramienta.intento" for e in entradas)
    fallos = sum(e.get("evento") == "herramienta.resultado" and e.get("estado") == "error" for e in entradas)

    primera, ultima = entradas[0]["_cuando"], entradas[-1]["_cuando"]
    print(f"Período: {primera:%Y-%m-%d %H:%M} → {ultima:%Y-%m-%d %H:%M}")
    print(f"Sesiones: {len(sesiones)} | Intentos: {intentos} | Resultados con error: {fallos}\n")

    print("Por persona:")
    for usuario, cuantas in por_usuario.most_common():
        acciones = sum(
            1 for e in entradas if e.get("usuario") == usuario and e.get("evento") == "herramienta.resultado" and e.get("estado") == "completed"
        )
        print(f"  {usuario:20s} {cuantas:>3} sesiones, {acciones:>4} acciones")

    if herramientas:
        print("\nHerramientas usadas:")
        for nombre, veces in herramientas.most_common():
            print(f"  {nombre:20s} {veces:>4}")

    if permisos:
        print(f"\nPermisos consultados: {len(permisos)}")
        for permiso, veces in collections.Counter(p.get("permiso") for p in permisos).most_common(5):
            print(f"  {str(permiso):20s} {veces:>4}")


def listar(entradas: list[dict], clave: str, titulo: str) -> None:
    """Lista un campo concreto de las entradas de herramienta, con su contexto.

    :param clave: Campo a mostrar (``comando`` o ``archivo``).
    :param titulo: Encabezado.
    """
    filas = [e for e in deduplicar(entradas) if e.get("evento") == "herramienta.resultado" and e.get("estado") == "completed" and clave in e]
    if not filas:
        print(f"Sin {titulo.lower()} en el período.")
        return
    print(f"{titulo} ({len(filas)}):\n")
    for entrada in filas:
        print(f"  {entrada['_cuando']:%m-%d %H:%M}  {entrada.get('usuario','?'):12s}  {entrada[clave]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dias", type=int, default=7, help="Ventana hacia atrás (0 = todo)")
    parser.add_argument("--usuario", help="Filtrar por persona")
    parser.add_argument("--comandos", action="store_true", help="Listar comandos ejecutados")
    parser.add_argument("--archivos", action="store_true", help="Listar archivos modificados")
    parser.add_argument("--archivo", type=pathlib.Path, default=DESTINO, help="Registro a leer")
    args = parser.parse_args()
    if args.dias < 0:
        parser.error("--dias debe ser no negativo")

    entradas = leer(args.archivo, args.dias, args.usuario)
    if not args.archivo.exists():
        print(f"No hay registro en {args.archivo}")
        print("Se crea solo al usar el agente con el plugin de auditoría instalado.")
        return 0

    if args.comandos:
        listar(entradas, "comando", "Comandos ejecutados")
    elif args.archivos:
        listar(entradas, "archivo", "Archivos modificados")
    else:
        resumir(entradas)

    print(f"\nRegistro: {args.archivo}")
    print("Es atribución, no prueba: lo escribe el mismo usuario cuya actividad registra.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
