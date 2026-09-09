import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
FILES = ['ground/CLANS.md', 'ground/CLASS_17.md', 'ground/AGENT_GROUNDING.md', 'ground/ACTION_DOOR.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            if not (ROOT/rel).exists():
                self.skipTest('missing '+rel)
            t = (ROOT/rel).read_text()
            self.assertIn('## Live cash', t, rel)
            self.assertIn('agent-rescue.html', t, rel)
if __name__ == '__main__':
    unittest.main()
