import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/TWO_ROOMS.md', 'ground/UNUSED_INVOKE.md', 'ground/VERIFY_CITE.md', 'ground/WATCHDOG_HEAD_PROOF.md', 'ground/WHAT_THE_PFC_IS.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
