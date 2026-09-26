"""Pruebas de la validación del formato ejecutable antes de invocarlo."""
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cuy
import instalar
from ejecutables import validar_windows


class EjecutablesTests(unittest.TestCase):
    """Un binario de otra plataforma debe rechazarse antes de intentar ejecutarlo."""

    def test_rechaza_binario_otro_sistema_y_pe_truncado(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / 'opencode.exe'
            for datos in (b'\x7fELF' + bytes(100), b'\xcf\xfa\xed\xfe' + bytes(100), b'MZ', b'MZ' + bytes(62)):
                ruta.write_bytes(datos)
                with self.assertRaisesRegex(ValueError, 'reparar-motor'):
                    validar_windows(ruta)

    def test_acepta_pe_x64_y_arm64(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / 'opencode.exe'
            for arquitectura in (0x8664, 0xAA64):
                datos = bytearray(70)
                datos[:2] = b'MZ'
                struct.pack_into('<I', datos, 60, 64)
                datos[64:68] = b'PE\0\0'
                struct.pack_into('<H', datos, 68, arquitectura)
                ruta.write_bytes(datos)
                self.assertEqual(validar_windows(ruta), ruta)

    def test_windows_no_selecciona_compilado_mac(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(cuy, 'RAIZ', Path(tmp)), patch.object(cuy, 'ES_WINDOWS', True):
            ruta = Path(tmp) / 'vendor/opencode/packages/opencode/dist/opencode-darwin-arm64/bin/opencode'
            ruta.parent.mkdir(parents=True)
            ruta.write_bytes(b'mac')
            self.assertIsNone(cuy.buscar_binario())

    def test_reparacion_no_requiere_databricks(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(instalar, 'RAIZ', Path(tmp)), patch('sys.argv', ['instalar.py', '--reparar-motor']), patch.object(instalar, 'verificar_requisitos', return_value='npm'), patch.object(instalar, 'descargar_binario', return_value=Path(tmp) / 'motor.exe'), patch.object(instalar, 'resolver_credencial') as token, patch.object(instalar, 'generar') as generar:
            self.assertEqual(instalar.main(), 0)
            token.assert_not_called()
            generar.assert_not_called()
            self.assertTrue((Path(tmp) / 'bin/seleccion.json').exists())

    def test_rechaza_seleccion_npm_sin_marca(self):
        import json
        with tempfile.TemporaryDirectory() as tmp, patch.object(cuy, 'RAIZ', Path(tmp)):
            raiz = Path(tmp)
            (raiz / 'bin').mkdir()
            (raiz / 'bin/seleccion.json').write_text(json.dumps({
                'path': str(raiz / 'node_modules/opencode-ai/bin/opencode.exe')}))
            with self.assertRaisesRegex(ValueError, 'marca cuycli'):
                cuy.buscar_binario()

    def test_instalacion_predeterminada_descarga_sin_compilar(self):
        from contextlib import ExitStack
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            stack.enter_context(patch.object(instalar, 'RAIZ', Path(tmp)))
            stack.enter_context(patch('sys.argv', ['instalar.py']))
            for nombre, valor in {
                'verificar_requisitos': None, 'resolver_host': 'https://workspace.example',
                'resolver_credencial': 'ficticio', 'generar': {'model': 'cuy/modelo'},
                'descargar_binario': Path(tmp) / 'cuy', 'instalar_plugin': None,
                'verificar': True,
            }.items():
                doble = stack.enter_context(patch.object(instalar, nombre, return_value=valor))
                if nombre == 'descargar_binario':
                    descargar = doble
            compilar = stack.enter_context(patch.object(instalar, 'compilar_desde_fuente'))
            self.assertEqual(instalar.main(), 0)
            descargar.assert_called_once_with(instalar.MANIFIESTO)
            compilar.assert_not_called()
