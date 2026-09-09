import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/SUBZERO_PRED.md', 'ground/SUBZERO_PROOF.md', 'ground/SUBZERO_QUOTE.md', 'ground/SUBZERO_RECEIPT.md', 'ground/SUBZERO_RGCG.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
