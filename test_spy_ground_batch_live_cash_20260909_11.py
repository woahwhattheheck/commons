import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/SUBZERO_GTM.md', 'ground/SUBZERO_HDVS.md', 'ground/SUBZERO_HOPF.md', 'ground/SUBZERO_IMMN.md', 'ground/SUBZERO_ISPN.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
