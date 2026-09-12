import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/CLAUDE_PEER_CHECK.md', 'ground/CLAUDE_ROLE.md', 'ground/CLAUDE_ZERO.md', 'ground/CLAUDE_ZERO_DAMAGE.md', 'ground/CLAUDE_ZERO_DAMAGE_CONTROL.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
