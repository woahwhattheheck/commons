import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/HARNESS.md', 'ground/HARNESS_ALREADY_LOGGED_IN.md', 'ground/HOARD.md', 'ground/HOLD_QUOTE.md', 'ground/HOST_ZERO.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
