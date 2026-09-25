import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cuy
import instalar
from ejecutables import validar_windows


class EjecutablesTests(unittest.TestCase):
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
        with tempfile.TemporaryDirectory() as tmp, patch.object(instalar, 'RAIZ', Path(tmp)), patch('sys.argv', ['instalar.py', '--reparar-motor']), patch.object(instalar, 'verificar_requisitos', return_value='npm'), patch.object(instalar, 'instalar_opencode', return_value=Path(tmp) / 'motor.exe'), patch.object(instalar, 'resolver_credencial') as token, patch.object(instalar, 'generar') as generar:
            self.assertEqual(instalar.main(), 0)
            token.assert_not_called()
            generar.assert_not_called()
            self.assertTrue((Path(tmp) / 'bin/seleccion.json').exists())
