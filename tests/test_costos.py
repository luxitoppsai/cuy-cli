"""Pruebas de la auditoría de tarifas y de la comparación con la facturación real."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import costos
from tarifas import tarifa_usd

class CostosTests(unittest.TestCase):
    """Tarifas: precedencia de las del contrato y detección de las desactualizadas."""

    def test_personalizada_exacta_prevalece(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp)/'tarifas.json'
            ruta.write_text(json.dumps({'databricks-claude-sonnet-4-6': {'input':3.3,'output':16.5,'cache_read':0.33,'cache_write':4.125}}))
            with patch.dict(os.environ, {'CUY_TARIFAS':str(ruta)}):
                self.assertEqual(tarifa_usd('databricks-claude-sonnet-4-6')['input'], 3.3)
                self.assertIsNone(tarifa_usd('otro-claude-sonnet-4-6'))

    def test_tarifa_negativa_no_pasa(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp)/'tarifas.json'
            ruta.write_text('{"modelo":{"input":-1,"output":1}}')
            with patch.dict(os.environ, {'CUY_TARIFAS':str(ruta)}):
                with self.assertRaises(ValueError):
                    tarifa_usd('modelo')

    def test_audita_tarifa_antigua_y_modelo_no_documentado(self):
        with patch.dict(os.environ, {}, clear=True):
            filas = costos.auditar({'provider': {'cuy': {'models': {
                'databricks-claude-opus-4-1': {'cost': {'input':5,'output':25}},
                'databricks-claude-sonnet-99': {'cost': {'input':3,'output':15}},
            }}}})
            self.assertEqual([f['estado'] for f in filas], ['difiere','sin_referencia'])
            self.assertGreater(filas[0]['referencia']['output'], 74)

    def test_actualiza_sin_inferencia_y_no_reescribe_tarifa_sin_referencia(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(costos, 'RAIZ', Path(tmp)), patch.dict(os.environ, {}, clear=True):
            ruta=Path(tmp)/'opencode.json'
            ruta.write_text(json.dumps({'provider': {'cuy': {'models': {
                'databricks-claude-opus-4-1': {'cost': {'input':5,'output':25}},
                'personal': {'cost': {'input':1,'output':2}},
            }}}}))
            self.assertEqual(costos.main(['--actualizar','--json']), 0)
            models=json.loads(ruta.read_text())['provider']['cuy']['models']
            self.assertGreater(models['databricks-claude-opus-4-1']['cost']['output'],74)
            self.assertEqual(models['personal']['cost'],{'input':1,'output':2})

    def test_conciliacion_exige_mes_registrado(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(costos, 'RAIZ', Path(tmp)), patch.dict(os.environ, {'CUY_GASTO': str(Path(tmp)/'sin-gasto.json')}, clear=True):
            (Path(tmp)/'opencode.json').write_text('{"provider":{}}')
            self.assertEqual(costos.main(['--real-usd','5','--mes','2026-09']),1)

    def test_no_elige_modelo_sin_tarifa_si_hay_alternativa(self):
        import generar_config as gc
        nombres = ['databricks-claude-sonnet-4-5', 'databricks-claude-sonnet-99']
        with patch.dict(os.environ, {}, clear=True):
            config = gc.construir_config('https://workspace.example', [{'name': n} for n in nombres],
                {n: {'forma': 'string', 'limite': 8000} for n in nombres})
            self.assertEqual(config['model'], 'cuy/databricks-claude-sonnet-4-5')
            self.assertIn(nombres[1], config['provider']['cuy']['models'])
