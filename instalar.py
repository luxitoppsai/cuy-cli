"""Deja cuy-cli listo para usar en este equipo, con un solo comando.

Hace en orden lo que antes había que hacer a mano y en el orden correcto: verifica
requisitos, guarda la credencial sin que aparezca en pantalla ni en el historial,
descubre el workspace, genera la configuración, instala OpenCode y **comprueba que
responde** antes de decir que terminó.

Uso::

    python3 instalar.py
    python3 instalar.py --host https://mi-workspace.cloud.databricks.com
    python3 instalar.py --sin-verificar      # omite la llamada de prueba

Sin dependencias: corre con Python pelado.
"""

import argparse
import getpass
import json
import os
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import generar_config as gc

RAIZ = pathlib.Path(__file__).resolve().parent
ENV = RAIZ / ".env"
CONFIG = RAIZ / "opencode.json"


def _paso(numero: int, texto: str) -> None:
    print(f"\n[{numero}/5] {texto}")


def _error(texto: str) -> None:
    sys.exit(f"\n  ✗ {texto}")


def verificar_requisitos() -> str:
    """Comprueba que estén las herramientas necesarias antes de empezar.

    Fallar acá con un mensaje claro es mucho mejor que fallar tres pasos después con
    un error de npm que no dice qué falta.

    :returns: Ruta del ejecutable de npm.
    :raises SystemExit: Si falta Node o npm.
    """
    npm = shutil.which("npm")
    if not npm:
        _error(
            "Falta Node.js (que trae npm), necesario para OpenCode.\n"
            "    macOS:   brew install node\n"
            "    Windows: winget install OpenJS.NodeJS\n"
            "    Linux:   https://nodejs.org/en/download/package-manager"
        )
    version = subprocess.run([npm, "--version"], capture_output=True, text=True).stdout.strip()
    print(f"  ✓ Node y npm ({version})")
    print(f"  ✓ Python {sys.version_info.major}.{sys.version_info.minor}")
    return npm


def resolver_host(indicado: str | None) -> str:
    """Determina la URL del workspace, reutilizando lo que ya esté configurado.

    :param indicado: Valor pasado por línea de comandos, si lo hubo.
    :returns: URL sin barra final.
    """
    if indicado:
        return indicado.rstrip("/")
    if os.environ.get("DATABRICKS_HOST"):
        return os.environ["DATABRICKS_HOST"].rstrip("/")
    if CONFIG.exists():
        try:
            url = json.loads(CONFIG.read_text())["provider"]["databricks"]["options"]["baseURL"]
            previo = url.removesuffix("/serving-endpoints")
            respuesta = input(f"  Workspace [{previo}]: ").strip()
            return (respuesta or previo).rstrip("/")
        except (KeyError, json.JSONDecodeError):
            pass
    print("  La URL del workspace es la del navegador, por ejemplo:")
    print("    https://dbc-xxxxxxxx-xxxx.cloud.databricks.com")
    while True:
        respuesta = input("  Workspace: ").strip().rstrip("/")
        if respuesta.startswith("http"):
            return respuesta
        print("    Tiene que empezar con https://")


def resolver_credencial() -> str:
    """Obtiene el token, reutilizando el guardado o pidiéndolo sin mostrarlo.

    El token se escribe solo en ``.env`` con permisos restringidos; nunca se imprime
    ni queda en el historial del shell.

    :returns: El token.
    """
    if os.environ.get("DATABRICKS_TOKEN"):
        print("  ✓ Token tomado del entorno")
        return os.environ["DATABRICKS_TOKEN"]

    if ENV.exists():
        for linea in ENV.read_text().splitlines():
            if linea.startswith("DATABRICKS_TOKEN="):
                valor = linea.split("=", 1)[1].strip()
                if valor:
                    print("  ✓ Token reutilizado de .env")
                    return valor

    print("  Generá uno en: Settings → Developer → Access tokens")
    print("  (no se muestra al escribirlo, y se guarda solo en .env)")
    token = getpass.getpass("  Token: ").strip()
    if not token:
        _error("No se ingresó ningún token.")

    ENV.write_text(f"DATABRICKS_TOKEN={token}\n")
    try:
        ENV.chmod(0o600)  # en Windows no aplica, pero no falla
    except OSError:
        pass
    print(f"  ✓ Guardado en {ENV.name} (ignorado por git)")
    return token


def generar(host: str, token: str, rapido: bool) -> dict:
    """Descubre el workspace y escribe la configuración.

    :returns: La configuración generada.
    :raises SystemExit: Si ningún endpoint resulta usable.
    """
    os.environ["DATABRICKS_TOKEN"] = token
    endpoints = gc.listar_endpoints(host, token)
    if not endpoints:
        _error("El workspace no tiene endpoints de chat servidos.")
    print(f"  {len(endpoints)} endpoints de chat encontrados")

    detalles = {}
    for endpoint in endpoints:
        nombre = endpoint["name"]
        forma = gc.detectar_forma(host, token, nombre)
        limite = gc.SALIDA_POR_DEFECTO if rapido else gc.sondear_limite(host, token, nombre)
        detalles[nombre] = {"forma": forma, "limite": limite}
        if forma == "bloques":
            print(f"    - {nombre}: descartado (no respeta el contrato OpenAI)")
        else:
            print(f"    ✓ {nombre} (salida ≤ {limite})")

    config = gc.construir_config(host, endpoints, detalles)
    if not config["provider"]["databricks"]["models"]:
        _error("Ningún endpoint es usable: todos devuelven bloques en vez de texto.")
    CONFIG.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    print(f"  ✓ {CONFIG.name} generado")
    return config


def instalar_plugin() -> None:
    """Deja el plugin de presupuesto donde OpenCode lo busca.

    Se copia en vez de enlazarse para que siga funcionando si el repo se mueve.

    :returns: Nada.
    """
    origen = RAIZ / "plugin" / "presupuesto.js"
    destino_dir = RAIZ / ".opencode" / "plugin"
    destino_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origen, destino_dir / "presupuesto.js")
    limite = os.environ.get("CUY_LIMITE_TOKENS", "300000")
    print(f"  ✓ Tope de presupuesto activo ({int(limite):,} tokens por sesión)".replace(",", "."))


def instalar_opencode(npm: str) -> pathlib.Path:
    """Instala OpenCode local al proyecto, sin tocar el sistema.

    :returns: Ruta del ejecutable.
    :raises SystemExit: Si la instalación falla.
    """
    binario = RAIZ / "node_modules" / ".bin" / "opencode"
    if binario.exists():
        print("  ✓ OpenCode ya estaba instalado")
        return binario

    print("  Instalando (puede tardar un par de minutos)...")
    resultado = subprocess.run(
        [npm, "install", "--no-fund", "--no-audit"], cwd=RAIZ, capture_output=True, text=True
    )
    if resultado.returncode != 0 or not binario.exists():
        _error(f"Falló la instalación:\n{resultado.stderr[-500:]}")
    print("  ✓ OpenCode instalado (local al proyecto)")
    return binario


def verificar(host: str, token: str, config: dict) -> bool:
    """Hace una llamada real al modelo principal para confirmar que todo responde.

    Es el paso que distingue "quedó configurado" de "funciona".

    :returns: ``True`` si el modelo respondió.
    """
    modelo = config.get("model", "").split("/", 1)[-1]
    if not modelo:
        return False
    codigo, respuesta = gc._pedir(
        f"{host}/serving-endpoints/{modelo}/invocations",
        token,
        {"messages": [{"role": "user", "content": "di: ok"}], "max_tokens": 50},
        timeout=90,
    )
    if codigo != 200:
        detalle = respuesta.get("message") or respuesta.get("raw") or respuesta
        print(f"  ✗ {modelo} no respondió (HTTP {codigo}): {str(detalle)[:200]}")
        return False
    print(f"  ✓ {modelo} respondió correctamente")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", help="URL del workspace de Databricks")
    parser.add_argument("--rapido", action="store_true", help="No sondear los límites de tokens")
    parser.add_argument("--sin-verificar", action="store_true", help="No hacer la llamada de prueba")
    args = parser.parse_args()

    print("Instalación de cuy-cli")

    _paso(1, "Verificando requisitos")
    npm = verificar_requisitos()

    _paso(2, "Conexión al workspace")
    host = resolver_host(args.host)
    token = resolver_credencial()

    _paso(3, "Descubriendo modelos disponibles")
    config = generar(host, token, args.rapido)

    _paso(4, "Instalando OpenCode")
    binario = instalar_opencode(npm)
    instalar_plugin()

    _paso(5, "Verificando que responde")
    if args.sin_verificar:
        print("  (omitido)")
    elif not verificar(host, token, config):
        print("\n  La configuración quedó escrita, pero el modelo no respondió.")
        print("  Revisá el token y que el workspace esté accesible desde esta red.")
        return 1

    relativo = binario.relative_to(RAIZ)
    print("\n" + "─" * 60)
    print("Listo. Para empezar:\n")
    print(f"  ./{relativo}\n")
    print(f"  Modelo principal : {config.get('model', '').split('/', 1)[-1]}")
    print(f"  Modelo auxiliar  : {config.get('small_model', '').split('/', 1)[-1]}")
    print("\nSi los modelos elegidos no son los que preferís, editá opencode.json.")
    print("Al cambiar de workspace, volvé a correr este script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
