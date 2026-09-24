"""Genera el `opencode.json` de un workspace de Databricks, descubriéndolo solo.

Existe porque configurar esto a mano es frágil: los endpoints cambian entre workspaces,
el tope de tokens es **distinto en cada modelo** y no está documentado en ningún lado, y
algunos endpoints no respetan el contrato OpenAI aunque Databricks los llame
"compatibles". Todo eso se descubre preguntándole al workspace.

Uso::

    python3 generar_config.py                    # usa DATABRICKS_HOST/.env
    python3 generar_config.py --host https://... --salida opencode.json
    python3 generar_config.py --rapido           # sin sondear límites (más veloz)

Sin dependencias: corre con Python pelado en un equipo recién formateado.
"""

import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent

# Un agente necesita razonar y editar; los modelos de embeddings no sirven acá.
TAREA_CHAT = "llm/v1/chat"

# Tope por defecto cuando no se sondea. Conservador a propósito: pasarse da un
# `Bad Request` que no dice cuál es el límite real.
SALIDA_POR_DEFECTO = 8000

# Candidatos a sondear, de mayor a menor. El endpoint rechaza los que no soporta.
ESCALONES = [64000, 32000, 24000, 16000, 8192, 4096, 2048]


def _pedir(url: str, token: str, cuerpo: dict | None = None, timeout: int = 120) -> tuple[int, dict]:
    """Hace una request y devuelve código y cuerpo parseado.

    :param url: URL completa.
    :param token: Token de Databricks.
    :param cuerpo: Si se da, la request es POST con este JSON.
    :param timeout: Segundos de espera.
    :returns: ``(código HTTP, cuerpo)``. El cuerpo es ``{}`` si no era JSON.
    """
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(
        url,
        data=datos,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST" if datos else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        crudo = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(crudo)
        except json.JSONDecodeError:
            return e.code, {"raw": crudo}
    except Exception as e:  # red, DNS, timeout
        return 0, {"raw": str(e)}


def listar_endpoints(host: str, token: str) -> list[dict]:
    """Lista los endpoints de chat servidos y listos.

    :param host: URL del workspace, sin barra final.
    :param token: Token de Databricks.
    :returns: Endpoints de chat, ya filtrados.
    :raises SystemExit: Si el workspace no responde o rechaza el token.
    """
    codigo, cuerpo = _pedir(f"{host}/api/2.0/serving-endpoints", token)
    if codigo != 200:
        detalle = cuerpo.get("message") or cuerpo.get("raw") or cuerpo
        sys.exit(f"No se pudo listar endpoints (HTTP {codigo}): {str(detalle)[:300]}")
    return [
        e for e in cuerpo.get("endpoints", [])
        if e.get("task") == TAREA_CHAT and (e.get("state") or {}).get("ready") == "READY"
    ]


def sondear_limite(host: str, token: str, nombre: str) -> int:
    """Averigua el tope de tokens de salida de un endpoint.

    El error de Databricks suele traer el límite real en el texto
    ("cannot exceed 8192"), así que primero se intenta leerlo de ahí; si no aparece,
    se baja por los escalones hasta que una request sea aceptada.

    :param host: URL del workspace.
    :param token: Token de Databricks.
    :param nombre: Nombre del endpoint.
    :returns: Tope de tokens de salida utilizable.
    """
    url = f"{host}/serving-endpoints/{nombre}/invocations"
    for escalon in ESCALONES:
        cuerpo = {"messages": [{"role": "user", "content": "hi"}], "max_tokens": escalon}
        codigo, respuesta = _pedir(url, token, cuerpo, timeout=90)
        if codigo == 200:
            return escalon
        texto = json.dumps(respuesta)
        # "max_tokens (24000) cannot exceed 8192" — el número util es el segundo.
        encontrados = [int(n) for n in re.findall(r"exceed (\d+)|greater than \D*(\d+)", texto) for n in n if n]
        if encontrados:
            return min(encontrados)
        numeros = re.findall(r"max_output_tokens (\d+)|cannot exceed (\d+)", texto)
        for par in numeros:
            for n in par:
                if n:
                    return int(n)
    return SALIDA_POR_DEFECTO


def detectar_forma(host: str, token: str, nombre: str) -> str:
    """Detecta si el endpoint respeta el contrato OpenAI para `content`.

    La especificación define `content` como string. Algunos endpoints de Databricks
    devuelven una lista de bloques tipados (razonamiento + texto), que los clientes
    OpenAI-compatible no saben leer.

    :returns: ``"string"``, ``"bloques"`` o ``"desconocido"``.
    """
    url = f"{host}/serving-endpoints/{nombre}/invocations"
    codigo, respuesta = _pedir(
        url, token, {"messages": [{"role": "user", "content": "di: ok"}], "max_tokens": 2000}, timeout=90
    )
    if codigo != 200:
        return "desconocido"
    try:
        contenido = respuesta["choices"][0]["message"].get("content")
    except (KeyError, IndexError):
        return "desconocido"
    return "bloques" if isinstance(contenido, list) else "string"


def _nombre_legible(endpoint: str) -> str:
    return endpoint.removeprefix("databricks-").replace("-", " ").title()


# Nivel relativo de las familias Claude, cuando el nombre no trae cantidad de parámetros.
NIVELES_CLAUDE = {"haiku": 10, "sonnet": 100, "opus": 1000}


def _tamano_estimado(endpoint: str) -> float:
    """Estima el "tamaño" de un modelo a partir de su nombre, para ordenarlos.

    Sirve para elegir cuál usar como principal y cuál como auxiliar sin pedirle al
    usuario que lo sepa. Se apoya en dos señales que casi siempre están en el nombre:
    la cantidad de parámetros (``70b``, ``120b``) o el nivel de la familia Claude
    (haiku < sonnet < opus).

    :param endpoint: Nombre del endpoint.
    :returns: Número comparable; mayor es más capaz. Un valor intermedio si el nombre
        no dice nada: desconocido no es lo mismo que chico, y tratarlo como chico haría
        que un modelo grande termine elegido para las tareas baratas.
    """
    nombre = endpoint.lower()
    for familia, nivel in NIVELES_CLAUDE.items():
        if familia in nombre:
            return float(nivel)
    # "qwen35-122b-a10b": interesa el total (122b), no los activos (a10b).
    parametros = [float(n) for n in re.findall(r"(?<![a-z])(\d+(?:\.\d+)?)b(?![a-z])", nombre)]
    return max(parametros) if parametros else 50.0


# Política de permisos por defecto, pensada para uso de equipo.
#
# El criterio es que el agente no pida permiso para lo que es seguro —si pregunta todo,
# la gente aprueba sin leer y el control deja de servir (§2.4 del RFC, "fatiga de
# aprobaciones")— pero que lo irreversible no dependa de que alguien lea el prompt.
#
# En OpenCode gana la última regla que coincide, así que va de lo general a lo específico.
PERMISOS_BASE = {
    # Leer, buscar y navegar el proyecto no necesita aprobación.
    "*": "allow",
    # Salir del proyecto y traer cosas de internet sí: son la vía de escape típica.
    "external_directory": "ask",
    "webfetch": "ask",
    "websearch": "ask",
    # Llamadas idénticas repetidas: el síntoma de un agente en loop, que además gasta.
    "doom_loop": "ask",
    "bash": {
        # Por defecto se pregunta: la lista de abajo habilita lo cotidiano.
        "*": "ask",
        # Lectura e inspección: sin riesgo.
        "ls *": "allow", "cat *": "allow", "head *": "allow", "tail *": "allow",
        "grep *": "allow", "rg *": "allow", "find *": "allow", "wc *": "allow",
        "pwd": "allow", "which *": "allow", "echo *": "allow",
        # Git de solo lectura.
        "git status*": "allow", "git diff*": "allow", "git log*": "allow",
        "git show*": "allow", "git branch": "allow",
        # Correr pruebas y linters es el ciclo normal de trabajo.
        "pytest*": "allow", "python3 -m pytest*": "allow", "python3 -m unittest*": "allow",
        "npm test*": "allow", "npm run *": "allow", "make *": "allow",
        # Irreversible o fuera del proyecto: se bloquea, no se pregunta.
        "rm -rf *": "deny", "rm -r *": "deny",
        "sudo *": "deny",
        "git push --force*": "deny", "git push -f*": "deny",
        "git reset --hard*": "deny", "git clean *": "deny",
        "* > /dev/sd*": "deny", "mkfs*": "deny", "dd *": "deny",
        # Ejecutar lo que se descarga de internet sin leerlo.
        "curl * | sh": "deny", "curl * | bash": "deny",
        "wget * | sh": "deny", "wget * | bash": "deny",
    },
}


def construir_permisos() -> dict:
    """Devuelve la política de permisos por defecto.

    Es un punto de partida razonable, no una respuesta definitiva: cada equipo tiene
    comandos propios que conviene habilitar. Se edita en ``opencode.json``.

    :returns: Bloque ``permission`` para la configuración.
    """
    return dict(PERMISOS_BASE)


# Nombre propio del proveedor. **No puede ser "databricks"**: ese id ya existe en el
# catálogo de models.dev y OpenCode fusiona los dos, así que `/models` termina listando
# modelos del catálogo que este workspace no sirve.
PROVEEDOR = "cuy"


# Preferencias de modelo por rol, en orden. Se buscan por subcadena en el nombre del
# endpoint; lo que no coincide cae al criterio de tamaño.
#
# Sonnet va de principal y no Opus, aunque Opus sea más capaz: es el equilibrio que
# rinde para el trabajo diario. Opus queda disponible para elegirlo a mano cuando la
# tarea lo justifique, que es distinto de que se use en todo sin pensarlo.
PREFERIDOS_PRINCIPAL = ["sonnet", "opus"]
PREFERIDOS_AUXILIAR = ["haiku"]


def elegir(candidatos: list[str], preferidos: list[str], respaldo) -> str | None:
    """Elige un modelo por preferencia declarada, con respaldo por tamaño.

    :param candidatos: Endpoints usables.
    :param preferidos: Subcadenas a buscar, en orden de preferencia.
    :param respaldo: Función que elige cuando ninguna preferencia coincide.
    :returns: El endpoint elegido, o ``None`` si no hay candidatos.
    """
    if not candidatos:
        return None
    for preferido in preferidos:
        coincidencias = [c for c in candidatos if preferido in c.lower()]
        if coincidencias:
            # Entre varias versiones de la misma familia, la de nombre mayor suele ser
            # la más nueva (sonnet-4-5 sobre sonnet-4).
            return sorted(coincidencias)[-1]
    return respaldo(candidatos)


def construir_agentes(por_tamano: list[str]) -> dict:
    """Asigna un modelo a cada agente según su rol (D3 del RFC).

    OpenCode liga un modelo a cada agente de forma nativa, así que el ruteo por rol es
    configuración y no hace falta tocar el harness. El criterio: planificar y explorar
    son tareas de lectura y razonamiento donde un modelo barato alcanza; ejecutar
    —leer, editar, correr comandos— es donde conviene el modelo capaz.

    :param por_tamano: Endpoints usables, de menor a mayor capacidad estimada.
    :returns: Bloque ``agent`` para la config, o ``{}`` si no hay con qué decidir.
    """
    if len(por_tamano) < 2:
        return {}
    capaz = elegir(por_tamano, PREFERIDOS_PRINCIPAL, lambda c: c[-1])
    barato = elegir(por_tamano, PREFERIDOS_AUXILIAR, lambda c: c[0])
    if capaz == barato:
        barato = por_tamano[0]
    return {
        # Ejecuta y edita: es donde más pesa la capacidad del modelo.
        "build": {"model": f"{PROVEEDOR}/{capaz}"},
        # Planifica sin permiso de editar ni ejecutar (lo trae OpenCode por defecto).
        "plan": {"model": f"{PROVEEDOR}/{barato}"},
        # Subagentes de solo lectura: explorar y buscar no justifican el modelo caro.
        "explore": {"model": f"{PROVEEDOR}/{barato}"},
        "scout": {"model": f"{PROVEEDOR}/{barato}"},
    }


def construir_config(host: str, endpoints: list[dict], detalles: dict) -> dict:
    """Arma el `opencode.json` a partir de lo descubierto.

    Solo entran los endpoints que devuelven `content` como string: los que devuelven
    bloques cuelgan al cliente OpenAI-compatible sin dar error.

    :param host: URL del workspace.
    :param endpoints: Endpoints de chat listos.
    :param detalles: ``{nombre: {"limite": int, "forma": str}}``.
    :returns: Config lista para escribir.
    """
    usables = {
        e["name"]: detalles[e["name"]]
        for e in endpoints
        if detalles.get(e["name"], {}).get("forma") != "bloques"
    }
    modelos = {
        nombre: {
            "name": _nombre_legible(nombre),
            "limit": {"context": 128000, "output": info["limite"]},
        }
        for nombre, info in usables.items()
    }

    # Se ordena por tamaño estimado, no por tope de tokens: el tope no se correlaciona
    # con la capacidad (dos modelos muy distintos pueden compartir el mismo 8192).
    por_tamano = sorted(usables, key=_tamano_estimado)
    principal = elegir(por_tamano, PREFERIDOS_PRINCIPAL, lambda c: c[-1])
    auxiliar = elegir(por_tamano, PREFERIDOS_AUXILIAR, lambda c: c[0])
    if principal == auxiliar and len(por_tamano) > 1:
        auxiliar = por_tamano[0]

    config = {
        "$schema": "https://opencode.ai/config.json",
        # El nombre que aparece en las conversaciones. El logo y el nombre del programa
        # están compilados en el binario y no se pueden cambiar sin recompilar.
        "username": "cuy-cli",
        # Solo el proveedor propio: sin esto, `/models` lista también los proveedores
        # que el agente carga por su cuenta (OpenCode Zen y demás), que no se pueden
        # usar acá y solo ensucian la elección.
        "enabled_providers": [PROVEEDOR],
        "permission": construir_permisos(),
        "provider": {
            PROVEEDOR: {
                "npm": "@ai-sdk/openai-compatible",
                "name": "Databricks",
                "options": {
                    "baseURL": f"{host}/serving-endpoints",
                    "apiKey": "{env:DATABRICKS_TOKEN}",
                },
                "models": modelos,
            }
        },
    }
    if principal:
        config["model"] = f"{PROVEEDOR}/{principal}"
    agentes = construir_agentes(por_tamano)
    if agentes:
        config["agent"] = agentes
    # Sin esto OpenCode elige un modelo del catálogo que no existe en el workspace
    # y devuelve 404 en cada sesión, visible solo en su log.
    if auxiliar:
        config["small_model"] = f"{PROVEEDOR}/{auxiliar}"
    return config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", help="URL del workspace (o DATABRICKS_HOST)")
    parser.add_argument("--salida", default="opencode.json", help="Archivo a escribir")
    parser.add_argument("--rapido", action="store_true", help="No sondear límites")
    args = parser.parse_args()

    env = RAIZ / ".env"
    if env.exists():
        for linea in env.read_text().splitlines():
            if "=" in linea and not linea.strip().startswith("#"):
                clave, valor = linea.split("=", 1)
                os.environ.setdefault(clave.strip(), valor.strip())

    token = os.environ.get("DATABRICKS_TOKEN")
    if not token:
        sys.exit("Falta DATABRICKS_TOKEN (ponelo en .env o en el entorno).")
    host = (args.host or os.environ.get("DATABRICKS_HOST", "")).rstrip("/")
    if not host:
        sys.exit("Falta el host: pasá --host o definí DATABRICKS_HOST.")

    print(f"Workspace: {host}\n")
    endpoints = listar_endpoints(host, token)
    print(f"{len(endpoints)} endpoints de chat listos.\n")

    detalles = {}
    for e in endpoints:
        nombre = e["name"]
        forma = detectar_forma(host, token, nombre)
        limite = SALIDA_POR_DEFECTO if args.rapido else sondear_limite(host, token, nombre)
        detalles[nombre] = {"forma": forma, "limite": limite}
        marca = "descartado (devuelve bloques)" if forma == "bloques" else f"salida<={limite}"
        print(f"  {nombre:45s} {forma:12s} {marca}")

    config = construir_config(host, endpoints, detalles)
    usables = len(config["provider"][PROVEEDOR]["models"])
    if not usables:
        sys.exit("\nNingún endpoint es usable: todos devuelven bloques en vez de string.")

    pathlib.Path(args.salida).write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    print(f"\nEscrito {args.salida} con {usables} modelo(s).")
    print(f"  principal : {config.get('model')}")
    print(f"  auxiliar  : {config.get('small_model')}")
    print("\nLa elección de principal/auxiliar se estima del nombre: revisala y ajustala")
    print("a mano si conocés mejor los modelos de tu workspace.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
