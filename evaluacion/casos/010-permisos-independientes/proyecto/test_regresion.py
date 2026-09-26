import unittest
import os
from unittest.mock import patch
import modulo as m

class Regresion(unittest.TestCase):
    def test_contrato(self):
        a=m.construir_permisos()
        a['bash']['nuevo']='deny'
        self.assertNotIn('nuevo',m.construir_permisos()['bash'])

if __name__ == "__main__":
    unittest.main()
