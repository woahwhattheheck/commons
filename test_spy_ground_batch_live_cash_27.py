import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/PROOF_TO_PROPOSAL.md', 'ground/PRTSCN.md', 'ground/README.md', 'ground/README_LIVE.md', 'ground/REMEASURE.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
