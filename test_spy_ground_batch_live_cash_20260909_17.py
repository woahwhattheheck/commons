import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/TEST_BATTERY_INDEX.md', 'ground/TITAN_APPEND_GUARD.md', 'ground/TITAN_MOVE.md', 'ground/TITAN_TEST_QUARANTINE.md', 'ground/TRUST.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
