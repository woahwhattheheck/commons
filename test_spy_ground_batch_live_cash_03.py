import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/CHECKOUT_CAPABILITY.md', 'ground/APK.md', 'ground/BATTERY_RED.md', 'ground/BRANCH_TRUTH_DELTA.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text()
            self.assertIn('## Live cash', t, rel)
            self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
