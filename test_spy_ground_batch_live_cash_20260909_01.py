import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/REVIEW_LANE.md', 'ground/SITTING_PR.md', 'ground/SITTING_REMINT.md', 'ground/SETTLED_FACTS.md', 'ground/SESSION_MEMORY.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
