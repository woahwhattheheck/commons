import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/STEALABLE_LANES.md', 'ground/STEALABLE_ROLES.md', 'ground/STRANDED_MAP.md', 'ground/SUBZERO_BUYERS.md', 'ground/SUBZERO_BYZQ.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
