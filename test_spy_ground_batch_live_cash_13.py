import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/DEVICE_CANARY.md', 'ground/DEVICE_CHURN.md', 'ground/DEVICE_PATH_CANARY.md', 'ground/DEVICE_PATH_CENSUS.md', 'ground/DEVICE_QUEUE_CAP.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
