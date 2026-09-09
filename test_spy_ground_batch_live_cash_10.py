import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/DEST_IS_THE_MACHINE.md', 'ground/EMBASSY.md', 'ground/EXPAND.md', 'ground/FEATURE_TRACKER.md', 'ground/FILE_STRUCTURE.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
