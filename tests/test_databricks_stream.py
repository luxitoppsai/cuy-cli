"""Regresión del formato de reasoning observado en Databricks Model Serving."""
import unittest
from unittest.mock import patch
import generar_config as gc


class DatabricksStreamTests(unittest.TestCase):
    def test_bloques_reasoning_se_prueban_en_ruta_real_del_agente(self):
        fragmento = {
            'model': 'us.anthropic.claude-sonnet-5',
            'choices': [{'delta': {'role': 'assistant', 'content': [
                {'type': 'reasoning', 'summary': [
                    {'type': 'summary_text', 'text': '', 'signature': ''}]}]},
                'index': 0, 'finish_reason': None}],
            'usage': {'prompt_tokens': 11612, 'completion_tokens': None, 'total_tokens': None},
            'object': 'chat.completion.chunk',
        }
        with patch.object(gc, '_pedir_stream', return_value=(200, [fragmento])) as stream:
            self.assertEqual(gc.detectar_forma('https://workspace.example', 'ficticio', 'endpoint-claude'), 'bloques')
        args = stream.call_args.args
        self.assertEqual(args[0], 'https://workspace.example/serving-endpoints/chat/completions')
        self.assertEqual(args[2]['model'], 'endpoint-claude')
        config = gc.construir_config('https://workspace.example', [{'name': 'endpoint-claude'}],
                                    {'endpoint-claude': {'forma': 'bloques', 'limite': 8000}})
        self.assertFalse(config['provider'])

class VerificacionInstaladorTests(unittest.TestCase):
    def verificar(self, fragmentos):
        import instalar
        config = gc.construir_config('https://workspace.example', [{'name': 'modelo'}],
                                    {'modelo': {'forma': 'string', 'limite': 8000}})
        with patch.object(gc, '_pedir_stream', return_value=(200, fragmentos)):
            return instalar.verificar('https://workspace.example', 'ficticio', config)

    def test_http_200_con_bloques_no_es_instalacion_verificada(self):
        self.assertFalse(self.verificar([{'choices': [{'delta': {'content': [
            {'type': 'reasoning', 'summary': []}]}, 'finish_reason': 'stop'}]}]))

    def test_texto_sin_cierre_no_es_instalacion_verificada(self):
        self.assertFalse(self.verificar([{'choices': [{'delta': {'content': 'Hola'}}]}]))

    def test_stream_completo_es_valido(self):
        self.assertTrue(self.verificar([
            {'choices': [{'delta': {'content': 'Hola'}}]},
            {'choices': [{'delta': {}, 'finish_reason': 'stop'}]},
        ]))
