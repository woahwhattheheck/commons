import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/OWNER_CONTEXT.md', 'ground/OWNER_MACHINE_BUILD_SWEEP.md', 'ground/OWNER_NOW.md', 'ground/MEMORY_SHIP.md', 'ground/MEMORY_VISIBLE.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
