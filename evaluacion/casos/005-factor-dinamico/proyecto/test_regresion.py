import unittest
import os
from unittest.mock import patch
import modulo as m

class Regresion(unittest.TestCase):
    def test_contrato(self):
        with patch.dict(os.environ,{'CUY_USD_POR_DBU':'.14'}):
            self.assertAlmostEqual(m.tarifa_usd('databricks-claude-sonnet-4-5')['input'],6,places=3)
            self.assertAlmostEqual(m.tarifa_usd('databricks-claude-sonnet-4-5',.07)['input'],3,places=3)

if __name__ == "__main__":
    unittest.main()
