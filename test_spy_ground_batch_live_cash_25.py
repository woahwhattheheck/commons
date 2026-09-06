import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/PFC_BAKE_CENSUS.md', 'ground/PFC_COMPUTER.md', 'ground/PFC_GROUNDING.md', 'ground/PFC_PROOF_REPORT.md', 'ground/PFC_X_DEFINED.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
