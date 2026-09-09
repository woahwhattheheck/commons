import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/AGENT_RETIREMENT.md', 'ground/ANNEX.md', 'ground/BRANCH_REVIEW.md', 'ground/CIRCUIT_PFC.md', 'ground/CLOCK_FANOUT_AUTOFAB.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
