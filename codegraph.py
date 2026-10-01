"""Índice local de fuentes y adaptador MCP de lectura para CodeGraph.

La copia evita que el indexador nativo lea archivos ignorados o siga enlaces.
Las consultas one-shot evitan su watcher, que no aplica las mismas exclusiones.
No recibe credenciales y no necesita embeddings ni inferencia.
"""

from contextlib import contextmanager
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import urllib.parse

RAIZ = Path(__file__).resolve().parent
VERSION = "0.20.1"
MAX_ARCHIVO = 1024 * 1024
MAX_ARCHIVOS = 5000
MAX_TOTAL = 64 * 1024 * 1024
TIMEOUT = 120
ESTADO = ".cuy/codegraph"
IGNORADOS_GIT = ("/.cuy/codegraph/", "/.codegraph-state/")
# Coinciden con las carpetas convencionales que excluye CodeGraph 0.20.1.
EXCLUIDOS = frozenset("node_modules target dist build out coverage htmlcov results logs tmp "
                     "__pycache__ vendor venv Pods DerivedData xcuserdata cmake-build-debug "
                     "cmake-build-release benches examples fixtures cases bin".split())
HERRAMIENTAS = frozenset("codegraph_symbol_search codegraph_get_symbol_info "
                        "codegraph_get_detailed_symbol codegraph_get_ai_context "
                        "codegraph_get_edit_context codegraph_get_callers codegraph_get_callees "
                        "codegraph_get_call_graph codegraph_get_dependency_graph "
                        "codegraph_analyze_impact codegraph_get_module_summary "
                        "codegraph_find_related_tests".split())


def carpeta_conversacion(argumentos: list[str]) -> Path | None:
    """Selecciona conversaciones locales; no indexa consultas CLI ni sesiones remotas.

    :param argumentos: Argumentos del motor, sin el ejecutable.
    :returns: Directorio de conversación o ``None`` para otros subcomandos.
    """
    if any(a in ("--help", "-h", "--version", "-v") for a in argumentos):
        return None
    if argumentos[:1] == ["run"]:
        if any(a == "--attach" or a.startswith("--attach=") for a in argumentos):
            return None
        for indice, valor in enumerate(argumentos):
            if valor.startswith("--dir="):
                return Path(valor.split("=", 1)[1])
            if valor == "--dir":
                return Path(argumentos[indice + 1]) if indice + 1 < len(argumentos) else None
        return Path.cwd()
    # El motor conserva la interpretación de sus propios flags y errores.
    comandos = {"acp", "mcp", "attach", "generate", "debug", "console", "providers", "agent",
                "upgrade", "uninstall", "serve", "web", "models", "stats", "export", "import",
                "github", "pr", "session", "plugin", "db"}
    if argumentos and argumentos[0] in comandos:
        return None
    valores = {"--model", "-m", "--agent", "--session", "-s", "--prompt", "--port",
               "--hostname", "--log-level", "--replay-limit"}
    indice = 0
    while indice < len(argumentos):
        valor = argumentos[indice]
        if valor in valores:
            indice += 2
            continue
        if valor == "--":
            return Path(argumentos[indice + 1]) if indice + 1 < len(argumentos) else Path.cwd()
        if not valor.startswith("-"):
            return Path(valor)
        indice += 1
    return Path.cwd()


def raiz_proyecto(carpeta: Path) -> Path:
    """Resuelve la raíz Git del worktree, o la carpeta si no pertenece a Git.

    :param carpeta: Directorio solicitado para la conversación.
    :returns: Directorio absoluto existente.
    """
    carpeta = carpeta.resolve(strict=True)
    if not carpeta.is_dir():
        raise ValueError("El proyecto debe ser una carpeta.")
    try:
        resultado = subprocess.run(["git", "-C", str(carpeta), "rev-parse", "--show-toplevel"],
                                   capture_output=True, timeout=10, check=False)
    except FileNotFoundError:
        return carpeta
    if resultado.returncode:
        return carpeta
    return Path(os.fsdecode(resultado.stdout).strip()).resolve(strict=True)


def _seguro(ruta: Path, raiz: Path) -> None:
    """Impide escribir o seguir enlaces en el estado que administra Cuy."""
    relativo = ruta.relative_to(raiz)
    actual = raiz
    for parte in relativo.parts:
        actual = actual / parte
        if actual.is_symlink():
            raise ValueError("El estado de CodeGraph contiene enlaces; mové .cuy/codegraph y reintentá.")


def _json(ruta: Path, valor: dict | list) -> None:
    """Reemplaza un archivo generado atómicamente, incluso en Windows."""
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=ruta.parent,
                                     delete=False) as archivo:
        temporal = Path(archivo.name)
        json.dump(valor, archivo, ensure_ascii=False)
    try:
        os.replace(temporal, ruta)
    finally:
        temporal.unlink(missing_ok=True)


def ignorar_estado(raiz: Path) -> None:
    """Añade las rutas generadas a Git sin duplicar reglas ni alterar las anteriores.

    :param raiz: Raíz del repositorio o carpeta de trabajo.
    """
    ruta = raiz / ".gitignore"
    _seguro(ruta, raiz)
    previo = ruta.read_bytes() if ruta.exists() else b""
    lineas = previo.decode("utf-8").splitlines()
    faltantes = [regla for regla in IGNORADOS_GIT if regla not in lineas]
    if faltantes:
        salto = b"\r\n" if b"\r\n" in previo else b"\n"
        with ruta.open("ab") as archivo:
            if previo and not previo.endswith(b"\n"):
                archivo.write(salto)
            archivo.write(salto + b"# Indice local de Cuy (generado)" + salto)
            archivo.write(salto.join(regla.encode() for regla in faltantes) + salto)


def _admitido(relativo: Path) -> bool:
    """Exclusiones convencionales; Git determina las exclusiones del usuario."""
    if any(parte.startswith(".") or parte in EXCLUIDOS for parte in relativo.parts):
        return False
    nombre = relativo.name.lower()
    return not any(fnmatch.fnmatchcase(nombre, patron) for patron in
                   ("*.token", "*.pem", "*.key", "*.p12", "*.pfx", "credentials.json", "secrets.json"))


def fuentes(raiz: Path) -> dict[str, bytes]:
    """Lee archivos de texto admitidos, incluidos cambios sin commit.

    :param raiz: Raíz del proyecto.
    :returns: Rutas relativas POSIX y bytes; nunca incluye enlaces ni archivos ocultos.
    :raises ValueError: Si se supera el límite, en vez de generar cobertura parcial.
    """
    try:
        listado = subprocess.run(["git", "-C", str(raiz), "ls-files", "-z", "--cached",
                                  "--others", "--exclude-standard"], capture_output=True,
                                 timeout=10, check=False)
    except FileNotFoundError:
        listado = None
    if listado is not None and listado.returncode == 0:
        candidatos = [Path(os.fsdecode(p)) for p in listado.stdout.split(b"\0") if p]
    else:
        candidatos = []
        for carpeta, directorios, archivos in os.walk(raiz, followlinks=False):
            directorios[:] = [d for d in directorios if _admitido(Path(d))
                              and not (Path(carpeta) / d).is_symlink()]
            candidatos.extend((Path(carpeta) / a).relative_to(raiz) for a in archivos)
    resultado = {}
    total = 0
    for relativo in sorted(set(candidatos)):
        if relativo.is_absolute() or ".." in relativo.parts or not _admitido(relativo):
            continue
        ruta = raiz / relativo
        if any((raiz / Path(*relativo.parts[:n])).is_symlink()
               for n in range(1, len(relativo.parts) + 1)):
            continue
        if not ruta.is_file() or ruta.stat().st_size > MAX_ARCHIVO:
            continue
        try:
            contenido = ruta.read_bytes()
        except FileNotFoundError:  # archivo eliminado durante el barrido
            continue
        if len(contenido) > MAX_ARCHIVO or b"\0" in contenido:
            continue
        total += len(contenido)
        if total > MAX_TOTAL:
            raise ValueError("Más de 64 MiB de texto; excluí archivos generados en .gitignore "
                             "y reintentá. Cuy puede usarse sin índice.")
        resultado[relativo.as_posix()] = contenido
        if len(resultado) > MAX_ARCHIVOS:
            raise ValueError("Más de 5000 archivos de texto; Cuy continúa sin índice. "
                             "Excluí archivos generados en .gitignore y reintentá.")
    return resultado


def _entorno(estado: Path) -> dict[str, str]:
    """Entorno mínimo para el proceso nativo; su HOME apunta solo a su caché."""
    conservar = {"PATH", "SystemRoot", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR",
                 "LANG", "LC_ALL", "PATHEXT"}
    entorno = {k: v for k, v in os.environ.items() if k in conservar}
    home = estado / "home"
    _seguro(home, estado)
    _seguro(home / ".codegraph", estado)
    home.mkdir(parents=True, exist_ok=True)
    entorno.update(HOME=str(home), USERPROFILE=str(home), DO_NOT_TRACK="1")
    return entorno


def _plataforma() -> str:
    """Nombre de asset publicado; no supone binarios para plataformas inexistentes."""
    sistemas = {"Darwin": "darwin", "Linux": "linux", "Windows": "win32"}
    arquitecturas = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "amd64": "x64"}
    sistema = sistemas.get(platform.system())
    arquitectura = arquitecturas.get(platform.machine().lower())
    if not sistema or not arquitectura or (sistema == "win32" and arquitectura != "x64"):
        raise ValueError("CodeGraph no publica binario para este equipo; Cuy puede usarse sin índice.")
    return f"codegraph-server-{sistema}-{arquitectura}" + (".exe" if sistema == "win32" else "")


def asegurar_binario() -> Path:
    """Instala una release fija comprobando SHA-256 antes de reemplazar archivos.

    :returns: Ejecutable nativo de CodeGraph, separado del motor de Cuy.
    :raises ValueError: Si el contrato o checksum no coincide.
    """
    manifiesto = json.loads((RAIZ / "codegraph-release.json").read_text(encoding="utf-8"))
    if manifiesto["version"] != VERSION:
        raise ValueError("Versión de CodeGraph incompatible; actualizá el repositorio completo.")
    asset = _plataforma()
    carpeta = RAIZ / "bin" / "codegraph" / VERSION
    _seguro(carpeta, RAIZ)
    carpeta.mkdir(parents=True, exist_ok=True)
    assets = [asset, "onnxruntime.dll"] if asset.endswith(".exe") else [asset]
    for nombre in assets:
        destino = carpeta / nombre
        _seguro(destino, RAIZ)
        esperado = manifiesto["sha256"][nombre]
        if destino.is_file() and hashlib.sha256(destino.read_bytes()).hexdigest() == esperado:
            continue
        print(f"Cuy: descargando CodeGraph {VERSION} ({nombre})…", file=sys.stderr)
        url = f"https://github.com/codegraph-ai/CodeGraph/releases/download/v{VERSION}/{nombre}"
        temporal = None
        try:
            with tempfile.NamedTemporaryFile(dir=carpeta, delete=False) as archivo:
                temporal = Path(archivo.name)
                with urllib.request.urlopen(url, timeout=60) as respuesta:
                    if not respuesta.geturl().startswith("https://"):
                        raise ValueError("Descarga de CodeGraph redirigida fuera de HTTPS.")
                    shutil.copyfileobj(respuesta, archivo)
            if hashlib.sha256(temporal.read_bytes()).hexdigest() != esperado:
                raise ValueError("Checksum de CodeGraph incorrecto; reintentá con una red confiable.")
            temporal.chmod(0o755)
            os.replace(temporal, destino)
        finally:
            if temporal is not None:
                temporal.unlink(missing_ok=True)
    return carpeta / asset


@contextmanager
def _bloqueo(estado: Path):
    """Serializa copia/consulta entre sesiones que usan el mismo repositorio."""
    ruta = estado / "lock"
    _seguro(ruta, estado)
    with ruta.open("a+b") as archivo:
        if archivo.tell() == 0:
            archivo.write(b"0")
            archivo.flush()
        archivo.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(archivo.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(archivo, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ValueError("Otra sesión está actualizando el índice; reintentá en unos segundos.") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                archivo.seek(0)
                msvcrt.locking(archivo.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(archivo, fcntl.LOCK_UN)


def _sincronizar(raiz: Path, estado: Path) -> tuple[dict, str]:
    """Actualiza copia; invalida toda la caché al borrar archivos o cambiar raíz."""
    archivos = fuentes(raiz)
    actual = {"version": VERSION, "raiz": str(raiz),
              "archivos": {ruta: hashlib.sha256(valor).hexdigest() for ruta, valor in archivos.items()}}
    manifest = estado / "manifest.json"
    _seguro(manifest, raiz)
    try:
        anterior = json.loads(manifest.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        anterior = {}
    if not isinstance(anterior, dict) or not isinstance(anterior.get("archivos", {}), dict):
        anterior = {}
    copia = estado / "source"
    _seguro(copia, raiz)
    copia.mkdir(parents=True, exist_ok=True)
    borrar = []
    # El manifiesto no controla rutas de borrado: solo archivos reales de nuestra copia.
    for carpeta, directorios, nombres in os.walk(copia, followlinks=False):
        directorios[:] = [d for d in directorios if not d.startswith(".")]
        for nombre in nombres:
            ruta = Path(carpeta) / nombre
            relativo = ruta.relative_to(copia).as_posix()
            if not nombre.startswith(".") and relativo not in archivos:
                _seguro(ruta, raiz)
                borrar.append(ruta)
    reconstruir = (anterior.get("version") != VERSION or anterior.get("raiz") != str(raiz)
                   or bool(borrar))
    if reconstruir:
        for cache in (estado / "home" / ".codegraph", copia / ".codegraph-state"):
            _seguro(cache, raiz)
            if cache.exists():
                shutil.rmtree(cache)
    for ruta in borrar:
        ruta.unlink()
    for relativo, contenido in archivos.items():
        destino = copia / relativo
        _seguro(destino, raiz)
        if anterior.get("archivos", {}).get(relativo) != actual["archivos"][relativo] or not destino.exists():
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(contenido)
    estado_indice = "creando" if not anterior else "reconstruyendo" if reconstruir else (
        "actualizando" if anterior != actual else "comprobando")
    return actual, estado_indice


def _nativo(binario: Path, estado: Path, argumentos: list[str], entrada: str | None = None) -> str:
    """Ejecuta sin shell ni credenciales; no imprime stderr con posibles contenidos."""
    resultado = subprocess.run([str(binario), "--workspace", str(estado / "source"),
                               "--graph-only", "--max-files", str(MAX_ARCHIVOS), *argumentos],
                              input=entrada, capture_output=True, text=True, encoding="utf-8",
                              timeout=TIMEOUT, env=_entorno(estado), cwd=estado / "source")
    if resultado.returncode:
        raise ValueError(f"CodeGraph terminó con código {resultado.returncode}; "
                         "mové .cuy/codegraph y reintentá para regenerar su índice.")
    return resultado.stdout


def _esquemas(binario: Path, estado: Path) -> list[dict]:
    """Obtiene los esquemas del binario real y filtra herramientas administrativas."""
    ruta = estado / "tools.json"
    _seguro(ruta, estado)
    if ruta.exists():
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        if datos.get("version") == VERSION:
            herramientas = datos["tools"]
            if {t["name"] for t in herramientas} == HERRAMIENTAS:
                return _aclarar_esquemas(herramientas)
    peticiones = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2024-11-05", "capabilities": {},
        "clientInfo": {"name": "cuy-cli", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}]
    salida = _nativo(binario, estado, ["--mcp"],
                     "".join(json.dumps(p) + "\n" for p in peticiones))
    respuestas = [json.loads(linea) for linea in salida.splitlines() if linea.strip()]
    respuesta = next((r for r in respuestas if r.get("id") == 2), {})
    herramientas = [t for t in respuesta.get("result", {}).get("tools", []) if t["name"] in HERRAMIENTAS]
    if {t["name"] for t in herramientas} != HERRAMIENTAS:
        raise ValueError("Contrato de herramientas CodeGraph incompatible; actualizá la instalación.")
    _json(ruta, {"version": VERSION, "tools": herramientas})
    return _aclarar_esquemas(herramientas)


def _aclarar_esquemas(herramientas: list[dict]) -> list[dict]:
    """Aclara el alcance de Cuy y la numeración observada en el binario fijado."""
    for herramienta in herramientas:
        propiedades = herramienta.get("inputSchema", {}).get("properties", {})
        if "line" in propiedades:
            propiedades["line"]["description"] = (
                "Número de línea del archivo original, desde 1. En la primera línea puede "
                "resolverse el archivo completo; consultá una línea dentro del cuerpo del símbolo.")
        if herramienta["name"] == "codegraph_get_edit_context":
            herramienta["description"] = (
                "Contexto para editar: símbolo, llamadas y pruebas relacionadas de las fuentes "
                "del proyecto. En Cuy no incluye historial Git, memoria ni otros repositorios.")
    return herramientas


def _traducir(valor, origen: Path, destino: Path):
    """Traduce rutas absolutas dentro de los argumentos y resultados JSON."""
    if isinstance(valor, str):
        return valor.replace(origen.as_uri(), destino.as_uri()).replace(
            str(origen), str(destino)).replace(origen.as_posix(), destino.as_posix())
    if isinstance(valor, list):
        return [_traducir(v, origen, destino) for v in valor]
    if isinstance(valor, dict):
        return {k: _traducir(v, origen, destino) for k, v in valor.items()}
    return valor


def _argumentos(argumentos: dict, raiz: Path, copia: Path) -> dict:
    """Normaliza URI/rutas de herramientas al conjunto local de fuentes."""
    args = dict(argumentos)
    for clave in ("uri", "path"):
        if clave not in args:
            continue
        valor = args[clave]
        if not isinstance(valor, str):
            raise ValueError("La ruta de consulta debe ser texto.")
        if clave == "uri":
            uri = urllib.parse.urlsplit(valor)
            if uri.scheme != "file" or uri.netloc not in ("", "localhost") or uri.query or uri.fragment:
                raise ValueError("Usá una URI file del proyecto para consultar el índice.")
            ruta = Path(urllib.request.url2pathname(uri.path))
        else:
            ruta = Path(valor)
            if not ruta.is_absolute():
                ruta = raiz / ruta
        try:
            relativo = ruta.resolve().relative_to(raiz)
        except ValueError as exc:
            raise ValueError("La consulta debe apuntar a un archivo del proyecto.") from exc
        destino = copia / relativo
        _seguro(destino, copia)
        if not destino.exists():
            raise ValueError("El archivo no está incluido en el índice; usá la lectura normal del proyecto.")
        args[clave] = destino.as_uri() if clave == "uri" else str(destino)
    return args


def consultar(raiz: Path, binario: Path, herramienta: str, argumentos: dict) -> dict:
    """Sincroniza y ejecuta una consulta de lectura con rutas del proyecto original.

    :param raiz: Raíz real del proyecto.
    :param binario: Binario verificado.
    :param herramienta: Nombre incluido en la lista permitida.
    :param argumentos: Argumentos JSON según el esquema nativo.
    :returns: Resultado nativo con las rutas traducidas.
    """
    if herramienta not in HERRAMIENTAS or not isinstance(argumentos, dict):
        raise ValueError("Herramienta o argumentos no permitidos.")
    estado = raiz / ESTADO
    _seguro(estado, raiz)
    estado.mkdir(parents=True, exist_ok=True)
    with _bloqueo(estado):
        manifest, _ = _sincronizar(raiz, estado)
        copia = estado / "source"
        args = _argumentos(argumentos, raiz, copia)
        resultado = json.loads(_nativo(binario, estado, ["--run-tool", herramienta,
                                                        "--tool-args", json.dumps(args)]))
        if isinstance(resultado, dict) and "error" in resultado:
            raise ValueError("CodeGraph no pudo resolver la consulta; comprobá la ruta y la línea "
                             "o usá la lectura normal del archivo.")
        # El modo graph-only nunca inicia embeddings; el mensaje nativo de búsqueda
        # dice "building" incluso aquí. Aclarar el modo evita prometer una espera inútil.
        if isinstance(resultado, dict) and "embedding_status" in resultado:
            resultado["embedding_status"] = "Modo estructural: búsqueda por nombre/texto, sin embeddings."
        _json(estado / "manifest.json", manifest)
    return _traducir(resultado, copia, raiz)


def preparar(raiz: Path, binario: Path) -> list[dict]:
    """Crea o actualiza el índice antes de abrir Cuy y obtiene los esquemas MCP.

    :param raiz: Raíz del repositorio/worktree.
    :param binario: Ejecutable verificado de CodeGraph.
    :returns: Esquemas de herramientas de lectura disponibles.
    """
    ignorar_estado(raiz)
    estado = raiz / ESTADO
    _seguro(estado, raiz)
    estado.mkdir(parents=True, exist_ok=True)
    with _bloqueo(estado):
        manifest, accion = _sincronizar(raiz, estado)
        print(f"Cuy: {accion} índice local de CodeGraph…", file=sys.stderr)
        json.loads(_nativo(binario, estado, ["--run-tool", "codegraph_symbol_search", "--tool-args",
                                            json.dumps({"query": "__cuy_indice__"})]))
        _json(estado / "manifest.json", manifest)
        return _esquemas(binario, estado)


def configurar(entorno: dict, carpeta: Path) -> dict:
    """Añade índice, MCP e instrucciones; un fallo recuperable conserva Cuy usable.

    :param entorno: Entorno del motor con configuración JSON de Cuy.
    :param carpeta: Directorio solicitado por el usuario.
    :returns: Entorno con herramientas locales o el original si falla el índice.
    """
    try:
        raiz = raiz_proyecto(carpeta)
        binario = asegurar_binario()
        preparar(raiz, binario)
        config = json.loads(entorno["OPENCODE_CONFIG_CONTENT"])
        config.setdefault("mcp", {})["cuy_codegraph"] = {
            "type": "local", "command": [sys.executable, str(RAIZ / "codegraph.py"),
                                          "serve", str(raiz), str(binario)],
            "enabled": True, "timeout": (TIMEOUT + 10) * 1000,
            "environment": {"PYTHONUTF8": "1"},
        }
        permisos = {f"cuy_codegraph_{nombre}": "allow" for nombre in sorted(HERRAMIENTAS)}
        config.setdefault("permission", {}).update(permisos)
        for nombre in ("plan", "explore"):
            config["agent"][nombre]["permission"].update(permisos)
        config["instructions"] = list(dict.fromkeys([*config.get("instructions", []),
            str(RAIZ / "instrucciones" / "CODEGRAPH.md")]))
        return {**entorno, "OPENCODE_CONFIG_CONTENT": json.dumps(config)}
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        # No volcar stderr del indexador ni rutas/contenidos de fuentes.
        detalle = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        print(f"Cuy: índice no disponible ({detalle}). Continúa con lectura y búsqueda normales. "
              "Reintentá al abrir Cuy; la primera descarga necesita acceso a GitHub.", file=sys.stderr)
        return entorno


def servir(raiz: Path, binario: Path) -> int:
    """Servidor JSON-RPC MCP stdio con lista cerrada de consultas de lectura.

    :param raiz: Raíz real, fijada por el lanzador.
    :param binario: Binario nativo verificado durante el arranque.
    :returns: Código de salida del servidor.
    """
    herramientas = _esquemas(binario, raiz / ESTADO)
    for linea in sys.stdin:
        peticion = None
        try:
            peticion = json.loads(linea)
            if not isinstance(peticion, dict):
                raise ValueError("Petición JSON-RPC inválida.")
            identificador = peticion.get("id")
            metodo = peticion.get("method")
            if identificador is None:
                continue
            if metodo == "initialize":
                resultado = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                             "serverInfo": {"name": "cuy-codegraph", "version": VERSION}}
            elif metodo == "ping":
                resultado = {}
            elif metodo == "tools/list":
                resultado = {"tools": herramientas}
            elif metodo == "tools/call":
                parametros = peticion.get("params", {})
                try:
                    valor = consultar(raiz, binario, parametros.get("name"), parametros.get("arguments", {}))
                    resultado = {"content": [{"type": "text", "text": json.dumps(valor, ensure_ascii=False)}]}
                except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                    detalle = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
                    resultado = {"isError": True, "content": [{"type": "text", "text": detalle}]}
            else:
                print(json.dumps({"jsonrpc": "2.0", "id": identificador,
                                  "error": {"code": -32601, "message": "Método no disponible"}}), flush=True)
                continue
            respuesta = {"jsonrpc": "2.0", "id": identificador, "result": resultado}
        except (ValueError, TypeError, AttributeError):
            respuesta = {"jsonrpc": "2.0", "id": peticion.get("id") if isinstance(peticion, dict) else None,
                         "error": {"code": -32600, "message": "Petición JSON-RPC inválida"}}
        print(json.dumps(respuesta, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "serve":
        raise SystemExit(servir(Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve()))
    raise SystemExit("Este módulo lo inicia Cuy; abrí cuy desde el proyecto.")
