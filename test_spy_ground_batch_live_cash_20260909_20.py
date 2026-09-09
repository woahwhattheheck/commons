import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/01_NONPROVISIONAL_CONVERSION_PLAN.md', 'ground/02_FOLLOWON_PROVISIONAL_NEW_MATTER_DRAFT.md', 'ground/03_EVIDENCE_ANNEX.md', 'ground/CLAUDE_COMPUTE.md', 'ground/CLAUDE_INTERMEDIATE.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
