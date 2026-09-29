"""Entorno controlado para pruebas, sin dejar a Windows sin ``Path.home()``.

Existe porque ``patch.dict(os.environ, {...}, clear=True)`` rompía el CI en Windows:
``Path.home()`` ahí depende exclusivamente de ``USERPROFILE``/``HOMEDRIVE``/``HOMEPATH``,
sin el respaldo por usuario POSIX que tienen Linux y macOS. Y el problema aparece aunque
el test no toque ``Path.home()`` a propósito: patrones como
``os.environ.get("CUY_GASTO", Path.home() / "...")`` evalúan el valor por defecto
**siempre**, exista o no la variable, así que ``Path.home()`` se llama igual.
"""

import os
import sys
from contextlib import contextmanager
from unittest.mock import patch

# Sin estas, Windows no puede resolver el directorio del usuario actual.
_RESPALDO_WINDOWS = ("USERPROFILE", "HOMEDRIVE", "HOMEPATH")


@contextmanager
def entorno_limpio(variables=None):
    """Reemplaza ``os.environ`` por uno controlado, preservando el home en Windows.

    :param variables: Variables a dejar puestas, además del respaldo de Windows.
    """
    variables = dict(variables or {})
    if sys.platform == "win32":
        for clave in _RESPALDO_WINDOWS:
            if clave in os.environ:
                variables.setdefault(clave, os.environ[clave])
    with patch.dict(os.environ, variables, clear=True):
        yield
