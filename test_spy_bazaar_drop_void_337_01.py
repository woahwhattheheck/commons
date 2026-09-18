import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class X(unittest.TestCase):
    def test_no_337(self):
        t=(ROOT/'bazaar.html').read_text()
        self.assertNotIn('337 NO', t)
if __name__=='__main__':
    unittest.main()
