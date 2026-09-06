import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class X(unittest.TestCase):
    def test_receipt(self):
        t=(ROOT/'p/spy-html-livecash-saturation-measure-20260905-01.md').read_text()
        self.assertIn('Root HTML with Live cash present', t)
        self.assertIn('Hands off #8802', t)
        self.assertIn('(none)', t)  # saturation MATCH-empty
if __name__=='__main__':
    unittest.main()
