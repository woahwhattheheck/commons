import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/SUBZERO_WALK.md', 'ground/SUPERGROK_HEAVY.md', 'ground/SWARM_DC.md', 'ground/TAKING_TRACE.md', 'ground/TERMINAL_CATALOG.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
