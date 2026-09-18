import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/IMPACT_LEDGER.md', 'ground/INTERCONNECT.md', 'ground/INCOMING_MODELS.md', 'ground/LISTING_REGISTRY.md', 'ground/MCP_WAKE_JOB.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
