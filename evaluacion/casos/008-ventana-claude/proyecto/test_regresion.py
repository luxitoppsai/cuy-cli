import unittest
import os
from unittest.mock import patch
import modulo as m

class Regresion(unittest.TestCase):
    def test_contrato(self):
        p=m._describir_modelo('databricks-claude-sonnet-4-5',8000)
        self.assertEqual(p['limit'],{'context':200000,'output':8000})

if __name__ == "__main__":
    unittest.main()
