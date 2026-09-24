"""Prueba si el workspace sirve Claude por la API nativa de Anthropic.

**Por qué.** Por la vía OpenAI-compatible, Sonnet 4.5 devuelve el razonamiento como
lista de bloques dentro de ``delta.content``, y el cliente lo rechaza:

    Invalid input: expected string, received array

La especificación de OpenAI define ``content`` como string. El endpoint lo emite igual
—no se lo pedimos—, así que no hay parámetro del lado del cliente que lo evite: el
formato es incompatible, no está mal configurado.

Databricks expone además un **passthrough de la API Messages de Anthropic**, que es la
superficie nativa de Claude. Si responde, se acabó la clase entera de este problema, y
además es lo que el RFC defiende desde el principio: el modelo rinde mejor contra el
contrato para el que fue entrenado.

Este script no arregla nada: **contesta tres preguntas** antes de tocar el generador de
configuración, porque desde afuera del workspace no se pueden responder.

Uso::

    python spike/probar_anthropic.py

Lee ``DATABRICKS_HOST`` y ``DATABRICKS_TOKEN`` del entorno o de ``.env``.
"""

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent

# Databricks documenta el passthrough acá; el modelo se nombra como en el endpoint.
RUTA = "/serving-endpoints/anthropic/v1/messages"
VERSION_ANTHROPIC = "2023-06-01"


def cargar_env() -> None:
    """Carga `.env` sin pisar lo que ya venga del entorno."""
    env = RAIZ / ".env"
    if not env.exists():
        return
    for linea in env.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            clave, valor = linea.split("=", 1)
            os.environ.setdefault(clave.strip(), valor.strip())


def pedir(url: str, cabeceras: dict, cuerpo: dict, timeout: int = 120):
    """Hace un POST JSON y devuelve ``(codigo, cuerpo)`` sin lanzar por HTTP."""
    datos = json.dumps(cuerpo).encode()
    pedido = urllib.request.Request(url, data=datos, method="POST")
    for clave, valor in {**cabeceras, "Content-Type": "application/json"}.items():
        pedido.add_header(clave, valor)
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        crudo = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(crudo)
        except json.JSONDecodeError:
            return e.code, {"raw": crudo}
    except Exception as e:
        return 0, {"raw": str(e)}


def probar_auth(host: str, token: str, modelo: str):
    """Pregunta 1: ¿qué forma de autenticación acepta el passthrough?

    El SDK de Anthropic manda ``x-api-key``; Databricks autentica con
    ``Authorization: Bearer``. Cuál de las dos funciona decide si alcanza con apuntar
    el SDK a otra URL o hay que además inyectarle cabeceras.

    :returns: El nombre de la cabecera que funcionó, o ``None``.
    """
    url = host + RUTA
    cuerpo = {"model": modelo, "max_tokens": 16,
              "messages": [{"role": "user", "content": "di: ok"}]}
    formas = {
        "Authorization: Bearer": {"Authorization": f"Bearer {token}",
                                  "anthropic-version": VERSION_ANTHROPIC},
        "x-api-key": {"x-api-key": token, "anthropic-version": VERSION_ANTHROPIC},
    }
    for nombre, cabeceras in formas.items():
        codigo, respuesta = pedir(url, cabeceras, cuerpo)
        if codigo == 200:
            texto = "".join(b.get("text", "") for b in respuesta.get("content", []))
            print(f"  ✓ {nombre}: HTTP 200 — respondió {texto.strip()[:40]!r}")
            return nombre, cabeceras
        detalle = respuesta.get("error", respuesta).get("message") if isinstance(
            respuesta.get("error", respuesta), dict) else respuesta
        print(f"  · {nombre}: HTTP {codigo} — {str(detalle)[:160]}")
    return None, None


def probar_razonamiento(host: str, token: str, modelo: str, cabeceras: dict) -> bool:
    """Pregunta 2: ¿el razonamiento llega en un formato que el cliente entiende?

    Es el fallo que se está arreglando. Por la vía OpenAI-compatible el razonamiento
    rompe el esquema; por la nativa debería llegar como bloque ``thinking``, que es
    parte del contrato.
    """
    # Un problema que suele disparar razonamiento en vez de responder de una.
    pregunta = ("Un tren sale a las 14:35 y viaja 2h48m. Otro sale 40 minutos después "
                "y tarda 25 minutos menos. ¿Cuál llega primero y por cuánto?")
    codigo, respuesta = pedir(host + RUTA, cabeceras,
                              {"model": modelo, "max_tokens": 2000,
                               "messages": [{"role": "user", "content": pregunta}]})
    if codigo != 200:
        print(f"  ✗ HTTP {codigo}: {str(respuesta)[:200]}")
        return False
    tipos = [b.get("type") for b in respuesta.get("content", [])]
    print(f"  ✓ bloques devueltos: {tipos}")
    print(f"    stop_reason: {respuesta.get('stop_reason')}")
    return True


def probar_herramienta(host: str, token: str, modelo: str, cabeceras: dict) -> bool:
    """Pregunta 3: ¿Claude usa herramientas por esta vía, y con qué forma de argumentos?

    Es **la** pregunta abierta del proyecto. El spike mostró que los modelos de pesos
    abiertos hacen todo menos editar archivos, porque ``old_string``/``new_string`` es
    la superficie nativa de Claude y no la de ellos. Si Claude por su propia API emite
    un ``tool_use`` bien formado, el producto funciona; si no, no.
    """
    herramienta = {
        "name": "edit",
        "description": "Reemplaza un fragmento exacto de texto en un archivo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filePath": {"type": "string"},
                "oldString": {"type": "string"},
                "newString": {"type": "string"},
            },
            "required": ["filePath", "oldString", "newString"],
        },
    }
    codigo, respuesta = pedir(host + RUTA, cabeceras, {
        "model": modelo,
        "max_tokens": 2000,
        "tools": [herramienta],
        "messages": [{
            "role": "user",
            "content": ("El archivo saludo.py contiene exactamente esta línea:\n"
                        "print('hola')\n\n"
                        "Cambiá el saludo por 'buenas'. Usá la herramienta edit."),
        }],
    })
    if codigo != 200:
        print(f"  ✗ HTTP {codigo}: {str(respuesta)[:200]}")
        return False

    usos = [b for b in respuesta.get("content", []) if b.get("type") == "tool_use"]
    if not usos:
        texto = "".join(b.get("text", "") for b in respuesta.get("content", []))
        print(f"  ✗ no llamó la herramienta; contestó texto: {texto.strip()[:160]!r}")
        return False

    uso = usos[0]
    print(f"  ✓ llamó a {uso.get('name')!r} con: {json.dumps(uso.get('input'), ensure_ascii=False)[:200]}")
    entrada = uso.get("input") or {}
    completo = all(k in entrada for k in ("filePath", "oldString", "newString"))
    print(f"    argumentos completos: {'sí' if completo else 'NO — faltan campos'}")
    return completo


def main() -> int:
    cargar_env()
    host = (os.environ.get("DATABRICKS_HOST") or "").rstrip("/")
    token = os.environ.get("DATABRICKS_TOKEN") or ""
    if not host or not token:
        sys.exit("Faltan DATABRICKS_HOST o DATABRICKS_TOKEN (en el entorno o en .env).")

    # El passthrough nombra al modelo como lo nombra Anthropic, no como el endpoint.
    modelo = sys.argv[1] if len(sys.argv) > 1 else "claude-sonnet-4-5"
    print(f"Workspace : {host}")
    print(f"Modelo    : {modelo}")
    print(f"Ruta      : {RUTA}\n")

    print("1. ¿Responde el passthrough de Anthropic, y con qué autenticación?")
    nombre, cabeceras = probar_auth(host, token, modelo)
    if not cabeceras:
        print("\n  → El passthrough no respondió. Puede no estar habilitado en el")
        print("    workspace, o el modelo llamarse distinto. Probá:")
        print("      python spike/probar_anthropic.py databricks-claude-sonnet-4-5")
        return 1

    print("\n2. ¿El razonamiento llega en un formato válido?")
    probar_razonamiento(host, token, modelo, cabeceras)

    print("\n3. ¿Claude usa herramientas por esta vía?")
    ok = probar_herramienta(host, token, modelo, cabeceras)

    print("\n" + "=" * 60)
    print(f"Autenticación que funciona: {nombre}")
    print(f"Edición de archivos: {'SÍ — el producto funciona' if ok else 'NO — hay que mirarlo'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
