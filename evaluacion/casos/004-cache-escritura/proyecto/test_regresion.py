import unittest
import os
from unittest.mock import patch
import modulo as m

class Regresion(unittest.TestCase):
    def test_contrato(self):
        p=m.tarifa_usd('databricks-claude-sonnet-4-5',.14)
        self.assertAlmostEqual(p['cache_write'],7.5,places=3)
        self.assertAlmostEqual(p['input'],6,places=3)

if __name__ == "__main__":
    unittest.main()
