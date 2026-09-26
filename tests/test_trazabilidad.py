"""Verifica que cada criterio de aceptación tenga un test que lo cubra.

Es la pieza que convierte el RFC en un contrato comprobable en vez de un documento que
envejece. Sin esto, escribir un criterio y olvidarse de cubrirlo no produce ninguna señal:
la suite queda en verde y el criterio nunca se ejerce.

Lo que **sí** comprueba:

1. Todo ``CA-NNN`` y ``RF-NNN`` del RFC aparece en su tabla de trazabilidad.
2. Todo test nombrado en la tabla existe de verdad en el archivo que la tabla indica.
3. Ningún identificador de la tabla dejó de existir en el RFC.

Lo que **no** puede comprobar es que el test pruebe lo que dice cubrir. Eso lo sostiene la
revisión, no un script.

Correr con::

    python3 -m unittest discover -s tests -p test_trazabilidad.py
"""

import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RFCS = RAIZ / "docs" / "rfc"
SPECS = RAIZ / "docs" / "specs"

# Identificador al principio de una fila de tabla Markdown: | CA-001 | … |
FILA = re.compile(r"^\|\s*((?:CA|RF)-\d{3})\s*\|(.*)$", re.MULTILINE)
# Nombre de test y archivo dentro de una fila de trazabilidad, ambos entre acentos graves.
CELDA = re.compile(r"`([^`]+)`")
# Una spec numerada: 002-redaccion-de-secretos → RFC-002
NUMERO = re.compile(r"^(\d{3})-")


def specs_con_trazabilidad() -> list[tuple[str, Path, Path]]:
    """Empareja cada carpeta de spec con el RFC del que deriva.

    Las specs sin ``trazabilidad.md`` se ignoran: una spec en curso todavía no la tiene, y
    fallar por eso convertiría el archivo en un estorbo en vez de una red.

    :returns: Tuplas ``(número, RFC, trazabilidad)`` de las specs ya trazadas.
    """
    encontradas = []
    for carpeta in sorted(SPECS.glob("*/")) if SPECS.exists() else []:
        coincide = NUMERO.match(carpeta.name)
        tabla = carpeta / "trazabilidad.md"
        if not coincide or not tabla.exists():
            continue
        rfcs = list(RFCS.glob(f"RFC-{coincide.group(1)}-*.md"))
        if rfcs:
            encontradas.append((coincide.group(1), rfcs[0], tabla))
    return encontradas


def identificadores(texto: str) -> set[str]:
    """Extrae los ``CA-NNN`` y ``RF-NNN`` que encabezan una fila de tabla.

    Se buscan solo al principio de fila para no capturar las menciones en prosa, que son
    referencias y no declaraciones.

    :param texto: Contenido del documento.
    :returns: Los identificadores declarados.
    """
    return {m.group(1) for m in FILA.finditer(texto)}


def cobertura(texto: str) -> dict[str, tuple[str | None, str | None]]:
    """Lee la tabla de trazabilidad.

    :param texto: Contenido de ``trazabilidad.md``.
    :returns: ``{identificador: (nombre del test, archivo)}``. Ambos son ``None`` cuando la
        fila declara explícitamente que no hay test automático.
    """
    filas = {}
    for m in FILA.finditer(texto):
        celdas = CELDA.findall(m.group(2))
        filas[m.group(1)] = (celdas[0], celdas[1]) if len(celdas) >= 2 else (None, None)
    return filas


class Trazabilidad(unittest.TestCase):
    """Cada criterio de una spec entregada tiene un test que lo ejerce."""

    def test_hay_al_menos_una_spec_trazada(self):
        """Si el emparejado se rompe, todo lo demás pasaría por vacío."""
        self.assertTrue(specs_con_trazabilidad(),
                        "no se encontró ninguna spec con trazabilidad; revisá docs/specs/")

    def test_todo_criterio_del_rfc_esta_en_la_tabla(self):
        for numero, rfc, tabla in specs_con_trazabilidad():
            with self.subTest(spec=numero):
                declarados = identificadores(rfc.read_text(encoding="utf-8"))
                trazados = set(cobertura(tabla.read_text(encoding="utf-8")))
                faltan = declarados - trazados
                self.assertFalse(faltan, f"RFC-{numero} declara {sorted(faltan)} sin trazar")

    def test_la_tabla_no_traza_criterios_inexistentes(self):
        """Un criterio borrado del RFC deja una fila huérfana que hay que limpiar."""
        for numero, rfc, tabla in specs_con_trazabilidad():
            with self.subTest(spec=numero):
                declarados = identificadores(rfc.read_text(encoding="utf-8"))
                trazados = set(cobertura(tabla.read_text(encoding="utf-8")))
                sobran = trazados - declarados
                self.assertFalse(sobran, f"la tabla de RFC-{numero} traza {sorted(sobran)}, "
                                         "que ya no existe en el RFC")

    def test_los_tests_nombrados_existen(self):
        """Renombrar un test sin actualizar la tabla rompe la trazabilidad en silencio."""
        for numero, _, tabla in specs_con_trazabilidad():
            for identificador, (nombre, archivo) in cobertura(tabla.read_text(encoding="utf-8")).items():
                if nombre is None:
                    continue
                with self.subTest(spec=numero, criterio=identificador):
                    ruta = RAIZ / archivo
                    self.assertTrue(ruta.exists(), f"{identificador} apunta a {archivo}, que no existe")
                    self.assertIn(nombre, ruta.read_text(encoding="utf-8"),
                                  f"{identificador} nombra un test que no está en {archivo}")

    def test_toda_falta_de_test_queda_justificada(self):
        """Dejar un criterio sin cubrir es aceptable; dejarlo sin explicar, no."""
        for numero, _, tabla in specs_con_trazabilidad():
            texto = tabla.read_text(encoding="utf-8")
            for identificador, (nombre, _) in cobertura(texto).items():
                if nombre is not None:
                    continue
                with self.subTest(spec=numero, criterio=identificador):
                    notas = texto[texto.index("## Notas"):] if "## Notas" in texto else ""
                    self.assertIn(identificador, notas,
                                  f"{identificador} no tiene test ni justificación en las notas")


if __name__ == "__main__":
    unittest.main()
