import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/RINGDELTA.md', 'ground/SALON.md', 'ground/SIZE_ONLY.md', 'ground/SLACK_ACCESS.md', 'ground/SLACK_BUILD_FLOOR.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
