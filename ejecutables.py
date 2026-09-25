"""Validación local del formato ejecutable antes de invocarlo en Windows."""
from pathlib import Path
import struct


def validar_windows(ruta: Path) -> Path:
    with ruta.open('rb') as archivo:
        cabecera = archivo.read(64)
        valido = len(cabecera) == 64 and cabecera[:2] == b'MZ'
        if valido:
            desplazamiento = struct.unpack_from('<I', cabecera, 60)[0]
            archivo.seek(desplazamiento)
            pe = archivo.read(6)
            valido = (len(pe) == 6 and pe[:4] == b'PE\0\0'
                      and struct.unpack_from('<H', pe, 4)[0] in (0x8664, 0xAA64))
    if not valido:
        raise ValueError(
            'El archivo seleccionado no es un ejecutable válido de Windows x64/ARM64. '
            'Ejecutá: python instalar.py --reparar-motor. '
            'No copies binarios ni node_modules desde otro sistema.'
        )
    return ruta
