import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/MUHL_RECEIPT_LANE.md', 'ground/MUHL_TRAIN_BRIDGE.md', 'ground/MUHL_PNG.md', 'ground/NAMED_BUILDER.md', 'ground/NO_MOCK_ONLY.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
