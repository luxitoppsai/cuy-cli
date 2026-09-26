import unittest
import os
from unittest.mock import patch
import modulo as m

class Regresion(unittest.TestCase):
    def test_contrato(self):
        self.assertAlmostEqual(m.tarifa_usd('databricks-claude-opus-4-1')['input'],15,places=3)
        self.assertAlmostEqual(m.tarifa_usd('databricks-claude-opus-4-5')['input'],5,places=3)

if __name__ == "__main__":
    unittest.main()
