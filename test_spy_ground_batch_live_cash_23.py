import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/OPEN-DOOR.md', 'ground/EXACT_BODY_REDACT.md', 'ground/FINDER_ZERO.md', 'ground/CURSOR_HALT.md', 'ground/CURSOR_QUOTA_HOLD.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
