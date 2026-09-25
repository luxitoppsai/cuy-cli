"""Presentación compartida por tareas reales y demostración, sin dependencias."""
import argparse
from datetime import datetime
import html
import json
import os
from pathlib import Path
import shutil
import sys
import textwrap
import unicodedata

from configuracion import leer_gasto, numero_entorno

ESTADOS = {
    "entregada": ("ENTREGADA · por revisar", "36"),
    "verificada": ("VERIFICADA · pruebas aprobadas", "32"),
    "sin_verificar": ("SIN VERIFICAR", "33"),
    "error": ("NO COMPLETADA", "31"),
    "interrumpida": ("INTERRUMPIDA", "33"),
    "preparada": ("PREPARADA", "36"),
    "en_curso": ("EN CURSO", "36"),
}


def seguro(valor) -> str:
    """No interpretar escapes de terminal provenientes de rutas o respuestas del modelo."""
    return "".join(c for c in str(valor) if c in "\n\t" or unicodedata.category(c) not in ("Cc", "Cf", "Cs"))


def panel(lineas: list[str], ancho=78) -> str:
    ancho = max(36, min(ancho, 100))
    dentro = ancho - 4
    salida = ["┌" + "─" * (ancho - 2) + "┐"]
    for linea in lineas:
        partes = seguro(linea).expandtabs(2).splitlines() or [""]
        for parte in partes:
            for trozo in textwrap.wrap(parte, dentro, replace_whitespace=False, drop_whitespace=True) or [""]:
                salida.append("│ " + trozo.ljust(dentro) + " │")
    salida.append("└" + "─" * (ancho - 2) + "┘")
    return "\n".join(salida)


def render_resultado(informe: dict, ancho=78) -> str:
    estado, _ = ESTADOS.get(informe.get("estado"), ("ESTADO DESCONOCIDO", "33"))
    lineas = [f"cuy / {informe.get('flujo', 'tarea')}", "", estado]
    if informe.get("proyecto"):
        lineas += ["", "Proyecto    " + Path(informe["proyecto"]).name]
    if informe.get("id"):
        lineas += ["Tarea       " + informe["id"]]
    costo = informe.get("costo_usd")
    lineas += ["Consumo     " + (f"${costo:.5f} estimados" if isinstance(costo, (int, float)) else "No disponible")]
    if "duracion_s" in informe:
        lineas += [f"Tiempo      {informe['duracion_s']} s"]
    entrega = informe.get("entrega") or {}
    if entrega.get("resumen"):
        lineas += ["", "RESULTADO", entrega["resumen"]]
    referencias = entrega.get("referencias", [])
    if referencias:
        lineas += ["", "REFERENCIAS"]
        for item in referencias:
            lineas += [f"  {item['archivo']}:{item['linea']}  {item['explicacion']}"]
    hallazgos = entrega.get("hallazgos", [])
    if informe.get("flujo") == "revisar":
        lineas += ["", f"HALLAZGOS ({len(hallazgos)})"]
        if not hallazgos and entrega:
            lineas += ["  Sin hallazgos reportados; no equivale a ausencia de bugs."]
        for item in hallazgos:
            lineas += [f"  [{item['severidad'].upper()}] {item['archivo']}:{item['linea']}",
                       f"  Evidencia: {item['evidencia']}", f"  Impacto: {item['impacto']}"]
    if informe.get("flujo") == "corregir":
        lineas += ["", f"CAMBIOS ({len(informe.get('archivos', []))})"]
        lineas += ["  " + p for p in informe.get("archivos", [])]
        lineas += ["", "PRUEBAS"]
        for prueba in informe.get("pruebas", []):
            marca = "OK" if prueba["codigo"] == 0 and not prueba["timeout"] else "FALLO"
            lineas += [f"  [{marca}] " + " ".join(prueba["comando"])]
            if "antes" in prueba:
                lineas += [f"       Antes: salida {prueba['antes']} · Después: salida {prueba['codigo']}"]
        if not informe.get("pruebas"):
            lineas += ["  No ejecutadas. Agregá --prueba para verificar el cambio."]
        if informe.get("trabajo"):
            lineas += ["", "WORKTREE · cambios pendientes de inspección", informe["trabajo"],
                       "Inspeccionar: git -C <worktree> diff", "Los cambios no se aplican al proyecto original."]
        if informe.get("diff"):
            lineas += ["", "DIFF EXPORTADO · incluye archivos nuevos", informe["diff"]]
    if informe.get("motivo"):
        lineas += ["", informe["motivo"]]
    if informe.get("informe"):
        lineas += ["", "INFORME LOCAL", informe["informe"]]
    return panel(lineas, ancho)


def mostrar_resultado(informe: dict) -> None:
    texto = render_resultado(informe, shutil.get_terminal_size((78, 24)).columns)
    if sys.stdout.isatty() and "NO_COLOR" not in os.environ:
        estado, color = ESTADOS.get(informe.get("estado"), ("ESTADO DESCONOCIDO", "33"))
        texto = texto.replace(estado, f"\033[{color}m{estado}\033[0m")
    print(texto)


def inicio() -> int:
    import cuy
    lineas = ["cuy", "Programar con un resultado que podés comprobar.", "", "ELEGÍ UN FLUJO", "",
              "01  ENTENDER   Mapa del código y referencias. Solo lectura.",
              '    cuy tarea entender "Cómo funciona la autenticación"', "",
              "02  CORREGIR   Cambio aislado y pruebas explícitas.",
              '    cuy tarea corregir "Corregí el bug" --prueba "python -m unittest"', "",
              "03  REVISAR    Bugs con ubicación, evidencia e impacto.",
              '    cuy tarea revisar "Revisá el módulo de importación"', "", "TU ENTORNO", "Proyecto    " + Path.cwd().name]
    try:
        env = cuy.entorno_agente()
        config = json.loads(env["OPENCODE_CONFIG_CONTENT"])
        lineas += ["Modelo      " + config["model"]]
        limite = numero_entorno("CUY_LIMITE_USD", 10)
        datos = leer_gasto(Path(env.get("CUY_GASTO", Path.home() / ".local/share/cuy-cli/gasto.json")))
        mes = datetime.now().strftime("%Y-%m")
        lineas += [f"Mes         ${datos.get(mes, 0):.2f} estimados · " + (f"tope ${limite:.2f}" if limite else "sin tope local")]
        prov, nombre = config["model"].split("/", 1)
        costo = config["provider"][prov]["models"][nombre].get("cost", {})
        if limite and not all(type(costo.get(k)) in (int, float) and costo[k] > 0 for k in ("input", "output")):
            lineas += ["ATENCIÓN    Faltan tarifas. La inferencia está bloqueada con tope activo."]
    except (OSError, ValueError, KeyError) as exc:
        lineas += ["ATENCIÓN    " + str(exc)]
    lineas += ["", "cuy doctor   Diagnóstico     cuy demo   Ver resultados de ejemplo", "", "Permisos locales · presupuesto estimado · sin publicación automática"]
    print(panel(lineas, shutil.get_terminal_size((78, 24)).columns))
    return 0


def ejemplos() -> list[dict]:
    base = {"id": "20260924-120000-demo", "proyecto": "/proyectos/inventario", "costo_usd": .0124,
            "duracion_s": 24.6, "informe": "~/.local/share/cuy-cli/tareas/<id>/resultado.json", "pruebas": [], "archivos": []}
    entender = {**base, "flujo": "entender", "estado": "entregada", "motivo": "Referencias comprobadas. Las conclusiones requieren revisión humana.", "entrega": {
        "resumen": "La API valida el pedido, reserva stock y persiste la orden dentro de una transacción.",
        "referencias": [{"archivo": "src/pedidos.py", "linea": 42, "explicacion": "Entrada y validación del pedido."},
                        {"archivo": "src/stock.py", "linea": 18, "explicacion": "Reserva y control de disponibilidad."}], "hallazgos": []}}
    corregir = {**base, "flujo": "corregir", "estado": "verificada", "trabajo": "~/.local/share/cuy-cli/tareas/<id>/worktree",
                "archivos": ["src/stock.py"], "pruebas": [{"comando": ["python", "-m", "unittest", "tests.test_stock"], "codigo": 0, "timeout": False}],
                "entrega": {"resumen": "Corregido el límite de reserva: una cantidad igual al stock disponible ahora se acepta.", "referencias": [], "hallazgos": []}}
    revisar = {**base, "flujo": "revisar", "estado": "entregada", "motivo": "Ubicación comprobada; reproducibilidad pendiente de revisión humana.", "entrega": {
        "resumen": "Un hallazgo puede rechazar pedidos válidos. No se modificaron archivos.", "referencias": [], "hallazgos": [{
            "archivo": "src/stock.py", "linea": 23, "severidad": "alta", "evidencia": "Con stock=5 y cantidad=5, reservar devuelve error.",
            "impacto": "Se rechazan pedidos que podrían atenderse por completo."}]}}
    pendiente = {**corregir, "estado": "sin_verificar", "pruebas": [], "motivo": "No se indicaron pruebas; no se declara verificado el cambio."}
    return [entender, corregir, revisar, pendiente]


def html_demo(destino: Path) -> None:
    tarjetas = ejemplos()
    panels = "\n".join(f'<section id="vista-{i}" class="terminal" {"hidden" if i else ""}><pre>{html.escape(render_resultado(r, 78))}</pre></section>' for i, r in enumerate(tarjetas))
    plantilla = Path(__file__).with_name("tema") / "demo.html"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(plantilla.read_text(encoding="utf-8").replace("<!-- TERMINALES -->", panels), encoding="utf-8")


def demo(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Vista de ejemplo: no inicia el motor ni consume tokens.")
    parser.add_argument("--flujo", choices=["entender", "corregir", "revisar", "pendiente"], default="corregir")
    parser.add_argument("--html", type=Path, help="Guardar una vista interactiva local con los cuatro estados")
    args = parser.parse_args(argv)
    if args.html:
        html_demo(args.html)
        print(f"Vista local: {args.html.resolve()}")
    else:
        print("DEMOSTRACIÓN · datos simulados · sin llamadas al modelo\n")
        mostrar_resultado(ejemplos()[["entender", "corregir", "revisar", "pendiente"].index(args.flujo)])
    return 0
