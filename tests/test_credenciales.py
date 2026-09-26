"""Regresiones del flujo de autenticación de Databricks (sin red ni secretos)."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import configuracion as cfg
import generar_config as gc
import instalar


class CredencialesTests(unittest.TestCase):
    """El token se valida y se guarda sin aparecer en pantalla ni en los errores."""

    def test_dotenv_comillas_export_bom_sin_expansion(self):
        with tempfile.TemporaryDirectory() as directorio:
            ruta = Path(directorio) / '.env'
            ruta.write_text('\ufeffexport DATABRICKS_TOKEN = "token-falso"\n'
                            "OTRO='$(comando)'\nHOST=valor # comentario\n", encoding='utf-8')
            self.assertEqual(cfg.leer_env(ruta), {
                'DATABRICKS_TOKEN': 'token-falso', 'OTRO': '$(comando)', 'HOST': 'valor'})

    def test_entorno_tiene_prioridad(self):
        with tempfile.TemporaryDirectory() as directorio, patch.dict(os.environ, {'DATABRICKS_TOKEN': 'entorno'}, clear=True):
            ruta = Path(directorio) / '.env'
            ruta.write_text('DATABRICKS_TOKEN="archivo"\n')
            cfg.cargar_archivo_env(ruta)
            self.assertEqual(os.environ['DATABRICKS_TOKEN'], 'entorno')

    def test_renovar_conserva_opciones_y_reemplaza_export(self):
        with tempfile.TemporaryDirectory() as directorio, patch.dict(os.environ, {}, clear=True):
            ruta = Path(directorio) / '.env'
            ruta.write_text('# ajustes\nCUY_LIMITE_USD=5\nexport DATABRICKS_TOKEN="viejo"\n')
            with patch.object(instalar, 'ENV', ruta), patch.object(instalar.getpass, 'getpass', return_value='nuevo'):
                self.assertEqual(instalar.resolver_credencial(True), 'nuevo')
            self.assertEqual(cfg.leer_env(ruta), {'CUY_LIMITE_USD': '5', 'DATABRICKS_TOKEN': 'nuevo'})
            self.assertIn('# ajustes', ruta.read_text())

    def test_renovar_no_deja_variable_obsoleta_ocultando_archivo(self):
        with patch.dict(os.environ, {'DATABRICKS_TOKEN': 'viejo'}), patch.object(instalar.getpass, 'getpass') as pedir:
            with self.assertRaisesRegex(SystemExit, 'entorno'):
                instalar.resolver_credencial(True)
            pedir.assert_not_called()

    def test_host_dotenv(self):
        with tempfile.TemporaryDirectory() as directorio, patch.dict(os.environ, {}, clear=True):
            ruta = Path(directorio) / '.env'
            ruta.write_text('DATABRICKS_HOST="https://example.databricks.com/"\n')
            with patch.object(instalar, 'ENV', ruta):
                self.assertEqual(instalar.resolver_host(None), 'https://example.databricks.com')

    def test_401_no_repite_cuerpo_que_podria_contener_credencial(self):
        with patch.object(gc, '_pedir', return_value=(401, {'message': 'secreto-reflejado'})) as pedir:
            with self.assertRaises(SystemExit) as error:
                gc.listar_endpoints('https://example.databricks.com', 'token-falso')
            self.assertIn('401', str(error.exception))
            self.assertNotIn('secreto-reflejado', str(error.exception))
            pedir.assert_called_once_with('https://example.databricks.com/api/2.0/serving-endpoints', 'token-falso')

    def test_token_invalido_no_se_revela(self):
        for token in ['Bearer secreto', 'secreto\ninvalido', '"secreto"']:
            with self.assertRaises(ValueError) as error:
                cfg.validar_token(token)
            self.assertNotIn('secreto', str(error.exception))
