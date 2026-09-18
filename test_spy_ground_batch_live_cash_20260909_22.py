import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/DEBTS_TO_BRYCE_20260820.md', 'ground/corpus-2026-08-07.md', 'ground/corpus-2026-h2.md', 'ground/corpus-file-map.md', 'ground/corpus-knowledge-base.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
