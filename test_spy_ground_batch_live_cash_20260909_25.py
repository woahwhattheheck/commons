import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/out-of-spec-host-lean.md', 'ground/pfc-is-reach.md', 'ground/redundancy-dual-doors.md', 'ground/studies-biblio.md', 'ground/studies-models-as-files.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
