import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/SUBZERO_CENSUS.md', 'ground/SUBZERO_CHFS.md', 'ground/SUBZERO_CHGS.md', 'ground/SUBZERO_CHHS.md', 'ground/SUBZERO_CHIH.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
