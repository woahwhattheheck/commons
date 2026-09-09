import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/corpus-record-audit.md', 'ground/corpus-speed-derivation.md', 'ground/frontier-file-is-machine.md', 'ground/instruments-in-mno.md', 'ground/interconnect-any-player.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
