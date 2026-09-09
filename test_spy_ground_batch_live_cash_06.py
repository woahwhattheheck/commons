import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/BUSINESS_PACK_KEEP_SELL.md', 'ground/BUSINESS_PACK_OPERATOR.md', 'ground/BUSINESS_PACK_PAPERWORK.md', 'ground/BUSINESS_PACK_RATING.md', 'ground/BUSINESS_PACK_RUNNING_COST.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
