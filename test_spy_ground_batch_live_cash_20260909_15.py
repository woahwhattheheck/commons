import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/SUBZERO_TITAN_PACKET.md', 'ground/SUBZERO_TITF.md', 'ground/SUBZERO_TITM.md', 'ground/SUBZERO_TITX.md', 'ground/SUBZERO_TSET.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
