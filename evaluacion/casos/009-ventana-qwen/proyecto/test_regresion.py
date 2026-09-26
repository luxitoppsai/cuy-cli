import unittest
import os
from unittest.mock import patch
import modulo as m

class Regresion(unittest.TestCase):
    def test_contrato(self):
        self.assertEqual(m._describir_modelo('databricks-qwen3',8000)['limit']['context'],32000)
        self.assertEqual(m._describir_modelo('desconocido',4000)['limit']['context'],128000)

if __name__ == "__main__":
    unittest.main()
