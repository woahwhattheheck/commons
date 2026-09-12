import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/RENDER_CHECK.md', 'ground/RENDER_CONTRACT.md', 'ground/REQUESTS.md', 'ground/RESOURCES_TAB.md', 'ground/RESOURCE_LEDGER.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
