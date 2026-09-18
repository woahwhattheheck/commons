import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/WORKING_BUILDS.md', 'ground/WORK_AUTOMATION.md', 'ground/copy-paste-manufacturing.md', 'ground/corpus-2026-08-02-substance.md', 'ground/corpus-2026-08-07-instruments.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
