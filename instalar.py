"""Deja cuy-cli listo para usar en este equipo, con un solo comando.

Hace en orden lo que antes había que hacer a mano y en el orden correcto: verifica
requisitos, guarda la credencial sin que aparezca en pantalla ni en el historial,
descubre el workspace, genera la configuración, instala cuycli y **comprueba que
responde** antes de decir que terminó.

Uso::

    python3 instalar.py
    python3 instalar.py --host https://mi-workspace.cloud.databricks.com
    python3 instalar.py --sin-verificar      # omite la llamada de prueba

Sin dependencias: corre con Python pelado.
"""

import argparse
import getpass
import hashlib
import tempfile
import json
import os
import pathlib
import shutil
import subprocess
import sys

# El destino de este proyecto incluye Windows: los mensajes y comandos que se le
# muestran al usuario tienen que usar la sintaxis de su sistema, no la de macOS.
ES_WINDOWS = os.name == "nt"
PY = "python" if ES_WINDOWS else "python3"

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import generar_config as gc
from ejecutables import validar_windows
from configuracion import escribir_json, validar_host, leer_env, validar_token

RAIZ = pathlib.Path(__file__).resolve().parent
ENV = RAIZ / ".env"
CONFIG = RAIZ / "opencode.json"


def _paso(numero: int, texto: str) -> None:
    print(f"\n[{numero}/5] {texto}")


def _error(texto: str) -> None:
    sys.exit(f"\n  ✗ {texto}")


def verificar_requisitos(necesita_npm: bool = False) -> str | None:
    """Comprueba que estén las herramientas necesarias antes de empezar.

    Fallar acá con un mensaje claro es mucho mejor que fallar tres pasos después con
    un error de npm que no dice qué falta.

    :returns: Ruta del ejecutable de npm.
    :raises SystemExit: Si falta Node o npm.
    """
    npm = shutil.which("npm")
    if not necesita_npm:
        # Compilando no hace falta Node: el binario se arma con bun.
        print(f"  ✓ Python {sys.version_info.major}.{sys.version_info.minor}")
        return npm
    if not npm:
        _error(
            "Falta Node.js (que trae npm), necesario para cuycli.\n"
            "    macOS:   brew install node\n"
            "    Windows: winget install OpenJS.NodeJS\n"
            "    Linux:   https://nodejs.org/en/download/package-manager"
        )
    version = subprocess.run([npm, "--version"], capture_output=True, text=True, shell=ES_WINDOWS).stdout.strip()
    print(f"  ✓ Node y npm ({version})")
    print(f"  ✓ Python {sys.version_info.major}.{sys.version_info.minor}")
    return npm


def resolver_host(indicado: str | None) -> str:
    """Determina la URL del workspace, reutilizando lo que ya esté configurado.

    :param indicado: Valor pasado por línea de comandos, si lo hubo.
    :returns: URL sin barra final.
    """
    if indicado:
        return validar_host(indicado)
    if os.environ.get("DATABRICKS_HOST"):
        return validar_host(os.environ["DATABRICKS_HOST"])
    if leer_env(ENV).get("DATABRICKS_HOST"):
        return validar_host(leer_env(ENV)["DATABRICKS_HOST"])
    if CONFIG.exists():
        try:
            # Sirve cualquier proveedor: en un workspace solo-Claude el compatible no
            # existe, y el nativo cuelga de otra ruta.
            proveedores = json.loads(CONFIG.read_text())["provider"].values()
            url = next(p["options"]["baseURL"] for p in proveedores)
            previo = url.removesuffix(gc.RUTA_ANTHROPIC).removesuffix("/serving-endpoints")
            respuesta = input(f"  Workspace [{previo}]: ").strip()
            return validar_host(respuesta or previo)
        except (KeyError, StopIteration, json.JSONDecodeError):
            pass
    print("  La URL del workspace es la del navegador, por ejemplo:")
    print("    https://dbc-xxxxxxxx-xxxx.cloud.databricks.com")
    while True:
        respuesta = input("  Workspace: ").strip().rstrip("/")
        try:
            return validar_host(respuesta)
        except ValueError as exc:
            print(f"    {exc}")


def resolver_credencial(renovar: bool = False) -> str:
    """Obtiene PAT u OAuth sin mostrarlo; conserva las otras opciones de .env."""
    if os.environ.get("DATABRICKS_TOKEN") and not renovar:
        print("  ✓ Token tomado del entorno (tiene prioridad sobre .env)")
        return validar_token(os.environ["DATABRICKS_TOKEN"])
    guardado = leer_env(ENV).get("DATABRICKS_TOKEN")
    if guardado and not renovar:
        print("  ✓ Token reutilizado de .env")
        return validar_token(guardado)
    if renovar and os.environ.get("DATABRICKS_TOKEN"):
        _error("DATABRICKS_TOKEN está definido en el entorno. Actualizá o eliminá esa variable "
               "antes de renovar; de lo contrario seguirá ocultando el token de .env.")
    print("  Ingresá un PAT o access token OAuth del workspace de Databricks.")
    token = validar_token(getpass.getpass("  Token (oculto): "))
    lineas = ENV.read_text(encoding="utf-8-sig").splitlines() if ENV.exists() else []
    lineas = [linea for linea in lineas
              if "DATABRICKS_TOKEN" not in leer_env_linea(linea)]
    temporal = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=ENV.parent,
                                         delete=False) as archivo:
            temporal = pathlib.Path(archivo.name)
            archivo.write("\n".join(lineas + [f"DATABRICKS_TOKEN={token}"]) + "\n")
            archivo.flush()
            os.fsync(archivo.fileno())
        os.replace(temporal, ENV)
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)
    print("  ✓ Token guardado en .env")
    return token


def leer_env_linea(linea: str) -> set[str]:
    """Identifica claves para reemplazar también asignaciones con export."""
    linea = linea.strip()
    if linea.startswith("export "):
        linea = linea[7:].lstrip()
    return {linea.split("=", 1)[0].strip()} if "=" in linea else set()


def generar(host: str, token: str, rapido: bool) -> dict:
    """Descubre el workspace y escribe la configuración.

    :returns: La configuración generada.
    :raises SystemExit: Si ningún endpoint resulta usable.
    """
    config = gc.descubrir_config(host, token, rapido)
    if not any(p["models"] for p in config["provider"].values()):
        _error("Ningún endpoint tiene compatibilidad verificada. Revisá conexión y contratos.")
    escribir_json(CONFIG, config)
    print("  ✓ Configuración de cuycli generada")
    return config


FORK = "https://github.com/luxitoppsai/opencode.git"
RAMA = "cuy"
FUENTE = RAIZ / "vendor" / "opencode"


def buscar_bun() -> str | None:
    """Ubica bun, mirando también donde su instalador lo deja.

    En Windows el instalador de bun agrega la ruta al PATH del sistema, pero **la
    terminal ya abierta no la ve hasta reiniciarse**: buscar solo en el PATH hace que
    parezca no instalado cuando sí lo está.

    :returns: Ruta del ejecutable, o ``None`` si no aparece en ningún lado.
    """
    if (encontrado := shutil.which("bun")):
        return encontrado
    candidatos = [
        pathlib.Path.home() / ".bun" / "bin" / ("bun.exe" if ES_WINDOWS else "bun"),
        pathlib.Path("/usr/local/bin/bun"),
        pathlib.Path("/opt/homebrew/bin/bun"),
    ]
    if ES_WINDOWS:
        local = os.environ.get("LOCALAPPDATA")
        if local:
            candidatos.insert(1, pathlib.Path(local) / "bun" / "bun.exe")
    return next((str(c) for c in candidatos if c.exists()), None)


RELEASE = "https://github.com/luxitoppsai/cuy-cli/releases/download"
MANIFIESTO = RAIZ / "release.json"

# Nombre del binario publicado para cada plataforma, y dónde se guarda al bajarlo.
PLATAFORMAS = {
    ("Windows", "AMD64"): "cuy-windows-x64.exe",
    ("Windows", "ARM64"): "cuy-windows-arm64.exe",
    ("Darwin", "arm64"): "cuy-darwin-arm64",
    ("Darwin", "x86_64"): "cuy-darwin-x64",
    ("Linux", "x86_64"): "cuy-linux-x64",
    ("Linux", "aarch64"): "cuy-linux-arm64",
}


def descargar_binario(manifiesto: pathlib.Path) -> pathlib.Path:
    """Baja el binario ya compilado que corresponde a esta máquina.

    El manifiesto incluido en el repo fija versión y SHA-256 por plataforma.
    El ejecutable anterior se conserva si la descarga o la verificación falla.

    :returns: Ruta del binario descargado.
    :raises SystemExit: Si no hay binario para esta plataforma o falla la descarga.
    """
    import platform as plataforma_mod
    import urllib.request

    clave = (plataforma_mod.system(), plataforma_mod.machine())
    nombre = PLATAFORMAS.get(clave)
    if not nombre:
        _error(
            f"No hay binario publicado para {clave[0]} {clave[1]}.\n"
            "    Pedí una release para esta plataforma; no se compilará en este equipo."
        )

    destino_dir = RAIZ / "bin"
    destino_dir.mkdir(exist_ok=True)
    destino = destino_dir / ("cuy.exe" if ES_WINDOWS else "cuy")
    if not manifiesto.is_file():
        _error("Falta release.json. Actualizá el repositorio para obtener el manifiesto de binarios publicados.")
    datos = json.loads(manifiesto.read_text(encoding="utf-8"))
    version = datos.get("version", "")
    import re
    if not re.fullmatch(r"v?[0-9]+(?:[.][0-9]+)*(?:-[a-zA-Z0-9.-]+)?", version):
        _error("El manifiesto debe fijar una versión; no se admite latest.")
    esperado = datos.get("sha256", {}).get(nombre, "")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", esperado):
        _error(f"Falta SHA-256 válido para {nombre} en el manifiesto revisado.")
    url = f"{RELEASE}/{version}/{nombre}"
    temporal = None

    print(f"  Descargando {nombre}...")
    try:
        with tempfile.NamedTemporaryFile(dir=destino_dir, delete=False) as salida:
            temporal = pathlib.Path(salida.name)
            digest = hashlib.sha256()
            with urllib.request.urlopen(url, timeout=600) as respuesta:
                while bloque := respuesta.read(1024 * 1024):
                    digest.update(bloque)
                    salida.write(bloque)
            salida.flush()
            os.fsync(salida.fileno())
        if digest.hexdigest() != esperado.lower():
            raise ValueError("El SHA-256 no coincide; se conserva el ejecutable anterior.")
        if ES_WINDOWS:
            validar_windows(temporal)
        else:
            temporal.chmod(0o755)
        os.replace(temporal, destino)
    except Exception as e:
        _error(
            f"No se pudo descargar el binario:\n    {url}\n    {e}\n"
            "\n    Revisá el acceso a GitHub y actualizá el repositorio. No se compilará automáticamente."
        )

    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)
    print(f"  ✓ Binario descargado ({destino.stat().st_size // 1024 // 1024} MB)")
    return destino


def exportar_certificados_del_sistema() -> pathlib.Path | None:
    """Vuelca los certificados raíz de Windows a un archivo PEM.

    En una red que intercepta TLS, el certificado de la empresa ya está en el almacén
    de Windows —por eso funcionan el navegador y npm—, pero bun no lo lee. Exportarlo
    y apuntarlo con ``NODE_EXTRA_CA_CERTS`` resuelve el problema **sin desactivar la
    verificación**, que sería peor: dejaría pasar cualquier intermediario, no solo el
    de la empresa, justo mientras se descarga código que después se compila y ejecuta.

    :returns: Ruta del PEM generado, o ``None`` si el sistema no expone el almacén.
    """
    import ssl

    if not hasattr(ssl, "enum_certificates"):
        return None  # solo existe en Windows

    pem = []
    for almacen in ("ROOT", "CA"):
        try:
            for der, codificacion, _ in ssl.enum_certificates(almacen):
                if codificacion == "x509_asn":
                    pem.append(ssl.DER_cert_to_PEM_cert(der))
        except Exception:
            continue

    if not pem:
        return None
    destino = RAIZ / "certificados-sistema.pem"
    destino.write_text("".join(pem), encoding="utf-8")
    print(f"  ✓ {len(pem)} certificados del sistema exportados")
    return destino


def compilar_desde_fuente() -> pathlib.Path:
    """Clona el fork propio y compila el binario con la marca de cuy-cli.

    El logo y el nombre del programa están dentro del binario: no hay configuración
    que los cambie. La única forma de tenerlos propios es compilar, y eso implica
    mantener el binario — por eso es opcional y no el camino por defecto.

    Se salta la interfaz web embebida (`--skip-embed-web-ui`): su compilación depende
    de paquetes nativos que fallan cuando la arquitectura de bun y la de node no
    coinciden, y el lanzador la desactiva igual por el blindaje de red.

    :returns: Ruta del binario compilado.
    :raises SystemExit: Si falta bun o la compilación falla.
    """
    bun = buscar_bun()
    if not bun:
        _error(
            "Falta bun, necesario para compilar el binario propio.\n"
            "    macOS/Linux: curl -fsSL https://bun.sh/install | bash\n"
            "    Windows:     powershell -c \"irm bun.sh/install.ps1 | iex\"\n"
            "\n"
            "    También podés instalar una release propia con --binario-manifiesto."
        )

    # El fuente viaja dentro de este repo (subtree en vendor/): un `git clone` se lo
    # lleva todo y no hace falta bajar nada más para compilar.
    if not FUENTE.exists():
        _error(
            f"No está el fuente en {FUENTE.relative_to(RAIZ)}.\n"
            "    Debería venir con el repo. Traelo con:\n"
            f"    git subtree add --prefix=vendor/opencode {FORK} {RAMA} --squash"
        )
    print(f"  Fuente: {FUENTE.relative_to(RAIZ)}")

    print("  Instalando dependencias (son ~2 GB, tarda varios minutos)...")
    dep = subprocess.run([bun, "install", "--frozen-lockfile"], cwd=FUENTE, capture_output=True, text=True)
    if dep.returncode != 0:
        # `bun install` devuelve error si falla el script de instalación de *cualquier*
        # dependencia, incluso una opcional que no usamos. El caso conocido es
        # `tree-sitter-powershell`, que compila código nativo y falla donde no están
        # las herramientas de compilación (Visual Studio Build Tools en Windows). Es
        # una gramática de resaltado: no afecta al agente. Por eso no se aborta acá,
        # sino que se sigue y se deja que falle el build si de verdad faltó algo.
        problemas = [l for l in (dep.stderr or "").splitlines() if l.startswith("error:")]
        print(f"  Aviso: {len(problemas) or 1} dependencia(s) opcional(es) no compilaron:")
        for linea in problemas[:3]:
            print(f"    {linea[:110]}")
        print("    Se continúa: suelen ser gramáticas de resaltado que el agente no usa.")

    salida = (dep.stderr or "") + (dep.stdout or "")
    if ("SELF_SIGNED_CERT_IN_CHAIN" in salida or "UNABLE_TO_GET_ISSUER_CERT" in salida) \
            and not os.environ.get("NODE_EXTRA_CA_CERTS"):
        print("  La red intercepta TLS; usando los certificados del sistema...")
        certificados = exportar_certificados_del_sistema()
        if certificados:
            entorno = {**os.environ, "NODE_EXTRA_CA_CERTS": str(certificados)}
            dep = subprocess.run([bun, "install", "--frozen-lockfile"], cwd=FUENTE, capture_output=True,
                                 text=True, env=entorno)
            salida = (dep.stderr or "") + (dep.stdout or "")
            os.environ["NODE_EXTRA_CA_CERTS"] = str(certificados)

    if "SELF_SIGNED_CERT_IN_CHAIN" in salida or "UNABLE_TO_GET_ISSUER_CERT" in salida:
        # Red corporativa que intercepta TLS: bun no reconoce el certificado propio de
        # la empresa. npm suele estar configurado con él, por eso --sin-compilar anda.
        _error(
            "Tu red intercepta TLS y bun no reconoce el certificado de la empresa\n"
            "    (SELF_SIGNED_CERT_IN_CHAIN al bajar dependencias).\n"
            "\n"
            "    Para compilar igual, apuntá bun al certificado de tu empresa:\n"
            "      Windows:  $env:NODE_EXTRA_CA_CERTS=\"C:\\ruta\\al\\certificado.pem\"\n"
            "      macOS:    export NODE_EXTRA_CA_CERTS=/ruta/al/certificado.pem\n"
            "      El certificado lo da el equipo de IT, o se exporta del navegador."
        )

    if not (FUENTE / "node_modules").exists():
        _error(f"No se instalaron las dependencias:\n{salida[-400:]}")

    print("  Compilando...")
    paquete = FUENTE / "packages" / "opencode"
    build = subprocess.run(
        [bun, "run", "script/build.ts", "--single", "--skip-embed-web-ui"],
        cwd=paquete, capture_output=True, text=True, env={**os.environ},
    )
    binarios = sorted((paquete / "dist").glob("*/bin/opencode*")) if (paquete / "dist").exists() else []
    if ES_WINDOWS:
        binarios = [p for p in binarios if p.suffix.lower() == ".exe"
                    and p.parent.parent.name.startswith("opencode-windows-")]
    if build.returncode != 0 or not binarios:
        _error(f"Falló la compilación:\n{(build.stderr or build.stdout)[-600:]}")

    if ES_WINDOWS:
        validar_windows(binarios[0])
    print(f"  ✓ Binario propio compilado ({binarios[0].stat().st_size // 1024 // 1024} MB)")
    return binarios[0]


def instalar_plugin() -> None:
    """Deja los plugins donde OpenCode los busca.

    El lanzador referencia el fuente por URL absoluta; comprueba que esté completo.

    :returns: Nada.
    """
    for nombre in ("presupuesto", "auditoria", "secretos"):
        if not (RAIZ / "plugin" / f"{nombre}.js").is_file():
            _error(f"Falta el plugin {nombre}; restaurá el checkout.")
    # El lanzador carga los plugins fuente por URL absoluta; no hay copias obsoletas.
    print("  ✓ Plugins locales: presupuesto, auditoría y secretos")


def verificar(host: str, token: str, config: dict) -> bool:
    """Hace una llamada real al modelo principal para confirmar que todo responde.

    Es el paso que distingue "quedó configurado" de "funciona".

    :returns: ``True`` si el modelo respondió.
    """
    referencia = config.get("model", "")
    if "/" not in referencia:
        return False
    proveedor_id, modelo = referencia.split("/", 1)
    proveedor = config["provider"][proveedor_id]
    cuerpo = {"messages": [{"role": "user", "content": "di: ok"}], "max_tokens": 50}
    if proveedor["npm"] == "@ai-sdk/anthropic":
        opciones = proveedor["options"]
        cabeceras = {"x-api-key": token}
        if "Authorization" in opciones.get("headers", {}):
            cabeceras["Authorization"] = f"Bearer {token}"
        base = opciones["baseURL"].removesuffix(gc.RUTA_ANTHROPIC)
        codigo, respuesta = gc._pedir_anthropic(base, cabeceras, {**cuerpo, "model": modelo})
    else:
        # La TUI consume SSE: una respuesta HTTP 200 sin streaming no prueba
        # compatibilidad (Claude puede emitir bloques solamente al razonar).
        codigo, fragmentos = gc._pedir_stream(
            proveedor["options"]["baseURL"] + "/chat/completions", token,
            {"model": modelo, "messages": [{"role": "user", "content": gc.PREGUNTA_SONDA}],
             "max_tokens": min(2000, proveedor["models"][modelo]["limit"]["output"])},
        )
        texto = False
        terminado = False
        for fragmento in fragmentos:
            if not isinstance(fragmento, dict) or fragmento.get("error"):
                print(f"  ✗ {modelo}: error en el streaming")
                return False
            for eleccion in fragmento.get("choices", []):
                contenido = (eleccion.get("delta") or {}).get("content")
                if contenido is not None and not isinstance(contenido, str):
                    print(f"  ✗ {modelo}: streaming incompatible (content no es texto)")
                    return False
                texto |= bool(contenido)
                terminado |= eleccion.get("finish_reason") is not None
        if codigo != 200 or not texto or not terminado:
            print(f"  ✗ {modelo}: streaming incompleto o inválido (HTTP {codigo})")
            return False
        print(f"  ✓ {modelo}: streaming de Databricks verificado")
        return True
    if codigo != 200:
        detalle = respuesta.get("message") or respuesta.get("raw") or respuesta
        print(f"  ✗ {modelo} no respondió (HTTP {codigo}): {str(detalle)[:200]}")
        return False
    contenido = respuesta.get("content") if proveedor["npm"] == "@ai-sdk/anthropic" else respuesta.get("choices")
    if not contenido:
        print(f"  ✗ {modelo}: respuesta vacía o contrato inesperado")
        return False
    print(f"  ✓ {modelo} respondió correctamente")
    return True


def main() -> int:
    """Punto de entrada del instalador: deja cuy-cli listo en este equipo.

    :returns: Código de salida; 0 si la instalación terminó y el motor respondió.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", help="URL del workspace de Databricks")
    parser.add_argument("--renovar-token", action="store_true", help="Reemplazar el token guardado en .env")
    parser.add_argument("--rapido", action="store_true", help="No sondear los límites de tokens")
    parser.add_argument("--sin-verificar", action="store_true", help="No hacer la llamada de prueba")
    parser.add_argument("--reparar-motor", action="store_true",
                        help="Reinstalar solo el agente para este equipo, sin consultar Databricks")
    origen = parser.add_mutually_exclusive_group()
    origen.add_argument("--compilar", action="store_true",
                        help="Compilar el binario acá en vez de descargarlo (necesita bun)")
    origen.add_argument("--sin-compilar", action="store_true",
                        help="Instalar el binario publicado (comportamiento predeterminado)")
    origen.add_argument("--binario-manifiesto", type=pathlib.Path,
                        help="Descargar release fijada por manifiesto local con version y sha256")
    args = parser.parse_args()

    if args.reparar_motor:
        verificar_requisitos(necesita_npm=False)
        binario = compilar_desde_fuente() if args.compilar else descargar_binario(args.binario_manifiesto or MANIFIESTO)
        escribir_json(RAIZ / "bin" / "seleccion.json", {"path": str(binario.resolve())})
        print("Motor reinstalado para este equipo. Ejecutá .\\cuy.cmd en Windows.")
        return 0

    print("Instalación de cuycli")

    _paso(1, "Verificando requisitos")
    verificar_requisitos(necesita_npm=False)

    _paso(2, "Conexión al workspace")
    host = resolver_host(args.host)
    token = resolver_credencial(args.renovar_token)

    _paso(3, "Descubriendo modelos disponibles")
    config = generar(host, token, args.rapido)

    _paso(4, "Instalando el agente")
    if args.compilar:
        binario = compilar_desde_fuente()
    else:
        binario = descargar_binario(args.binario_manifiesto or MANIFIESTO)
    escribir_json(RAIZ / "bin" / "seleccion.json", {"path": str(binario.resolve())})
    instalar_plugin()

    _paso(5, "Verificando que responde")
    if args.sin_verificar:
        print("  Verificación omitida: la instalación no confirma que el modelo funcione.")
    elif not verificar(host, token, config):
        print("\n  La configuración quedó escrita, pero el modelo no respondió.")
        print("  Revisá el error anterior: autenticación, red o compatibilidad de la respuesta.")
        return 1

    lanzador = "cuy.cmd" if ES_WINDOWS else "./cuy"
    print("\n" + "─" * 60)
    print("Instalación sin verificar. Para probar:\n" if args.sin_verificar else "Listo. Para empezar:\n")
    print(f"  {lanzador}\n")
    print("  Marca            : cuycli")
    print(f"  Modelo principal : {config.get('model', '').split('/', 1)[-1]}")
    print(f"  Modelo auxiliar  : {config.get('small_model', '').split('/', 1)[-1]}")
    print("\nPodés elegir otro modelo disponible con /models dentro de cuycli.")
    print("Al cambiar de workspace, volvé a correr este script.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as exc:
        raise SystemExit(f"No se pudo completar: {exc}") from None
