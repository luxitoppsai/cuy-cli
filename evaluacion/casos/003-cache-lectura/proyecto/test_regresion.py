import unittest
import os
from unittest.mock import patch
import modulo as m

class Regresion(unittest.TestCase):
    def test_contrato(self):
        p=m.tarifa_usd('databricks-claude-sonnet-4-5')
        self.assertAlmostEqual(p['cache_read'],.3,places=3)
        self.assertAlmostEqual(p['input'],3,places=3)

if __name__ == "__main__":
    unittest.main()
