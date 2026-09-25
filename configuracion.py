"""Validación y escritura compartidas por el instalador y el lanzador."""

import json
import math
import os
import re
from pathlib import Path
import tempfile
from urllib.parse import urlsplit


def validar_host(valor: str) -> str:
    valor = valor.strip().rstrip("/")
    url = urlsplit(valor)
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.path or url.query or url.fragment):
        raise ValueError("El workspace debe ser una URL HTTPS sin credenciales, ruta ni parámetros.")
    # También valida el rango y formato del puerto.
    _ = url.port
    return valor


def numero_entorno(nombre: str, defecto: float) -> float:
    try:
        valor = float(os.environ.get(nombre, defecto))
    except ValueError as exc:
        raise ValueError(f"{nombre} debe ser un número finito no negativo.") from exc
    if not math.isfinite(valor) or valor < 0:
        raise ValueError(f"{nombre} debe ser un número finito no negativo.")
    return valor


def leer_gasto(ruta: Path) -> dict:
    """Lee el formato contable compartido con el plugin, sin ocultar corrupción."""
    if not ruta.exists():
        return {}
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        raise ValueError("Contabilidad inválida; no se asumirá gasto cero.")
    for mes, valor in datos.items():
        if mes == "_eventos":
            if not isinstance(valor, dict) or any(not isinstance(ids, list)
                    or any(not isinstance(i, str) for i in ids) for ids in valor.values()):
                raise ValueError("Índice de eventos contables inválido.")
            continue
        if (not re.fullmatch(r"\d{4}-\d{2}", mes) or type(valor) not in (int, float)
                or not math.isfinite(valor) or valor < 0):
            raise ValueError("Contabilidad inválida; no se asumirá gasto cero.")
    return datos


def escribir_json(ruta: Path, datos: dict) -> None:
    """Reemplaza el archivo completo; un fallo no destruye la versión anterior."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=ruta.parent,
                                         delete=False) as salida:
            temporal = Path(salida.name)
            json.dump(datos, salida, indent=2, ensure_ascii=False, allow_nan=False)
            salida.write("\n")
            salida.flush()
            os.fsync(salida.fileno())
        os.replace(temporal, ruta)
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)


def leer_env(ruta: Path) -> dict[str, str]:
    """Lee asignaciones dotenv sin ejecutar ni expandir su contenido."""
    if not ruta.exists():
        return {}
    valores = {}
    for linea in ruta.read_text(encoding="utf-8-sig").splitlines():
        linea = linea.strip()
        if linea.startswith("export "):
            linea = linea[7:].lstrip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        clave, valor = clave.strip(), valor.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", clave):
            continue
        if len(valor) >= 2 and valor[0] in ("\"", "'") and valor[-1] == valor[0]:
            valor = valor[1:-1]
        else:
            valor = re.split(r"\s+#", valor, maxsplit=1)[0].rstrip()
        valores[clave] = valor
    return valores


def cargar_archivo_env(ruta: Path) -> None:
    for clave, valor in leer_env(ruta).items():
        os.environ.setdefault(clave, valor)


def validar_token(valor: str) -> str:
    """Admite PAT y OAuth; nunca incluye la credencial en los errores."""
    valor = valor.strip()
    if not valor or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in valor):
        raise ValueError("DATABRICKS_TOKEN debe contener solo el token, sin prefijo Bearer ni espacios.")
    if valor[0] in ("\"", "'") or valor[-1] in ("\"", "'"):
        raise ValueError("DATABRICKS_TOKEN contiene comillas literales; corregí la variable del entorno.")
    return valor
