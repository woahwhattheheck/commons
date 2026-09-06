import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/GROK_APP_ROUTE.md', 'ground/GROK_AUTOMATION_HARVEST.md', 'ground/GROK_HYGIENE.md', 'ground/GROK_LAND_UPFRONT.md', 'ground/HUB_TICK.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
