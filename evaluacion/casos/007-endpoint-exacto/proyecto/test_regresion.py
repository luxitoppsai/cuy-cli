import unittest
import os
from unittest.mock import patch
import modulo as m

class Regresion(unittest.TestCase):
    def test_contrato(self):
        self.assertIsNone(m.tarifa_usd('mi-claude-sonnet-4-5-copia'))
        self.assertIsNotNone(m.tarifa_usd('databricks-claude-sonnet-4-5'))

if __name__ == "__main__":
    unittest.main()
