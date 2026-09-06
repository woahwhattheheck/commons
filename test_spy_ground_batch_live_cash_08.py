import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/AGENT_TOOLKIT.md', 'ground/AGENT_TOOLKIT_AUDIT.md', 'ground/CONNECTOR_REVAL.md', 'ground/CUSTOMER_LINK_BOUNDARY.md', 'ground/COMPRESS_DOORS.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
