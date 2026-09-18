import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/BREATH.md', 'ground/BRYCE_BUILD_ASKS.md', 'ground/BRYCE_EXECUTION_PROFILE.md', 'ground/BUILD_SWEEP_ACT.md', 'ground/BUSINESS_PACKS.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
