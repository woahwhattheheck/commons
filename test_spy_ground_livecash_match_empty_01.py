import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class X(unittest.TestCase):
    def test_receipt(self):
        t=(ROOT/'p/spy-ground-livecash-match-empty-20260909-01.md').read_text()
        self.assertIn('Zero list: (none)', t)
        self.assertIn('Hands off #8802', t)
    def test_ground_saturated(self):
        missing=[]
        for p in sorted((ROOT/'ground').glob('*.md')):
            if '## Live cash' not in p.read_text():
                missing.append(p.name)
        self.assertEqual(missing, [], missing)
if __name__=='__main__':
    unittest.main()
