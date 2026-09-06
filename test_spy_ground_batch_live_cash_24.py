import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/PAGES_DEPLOY_RECEIPT.md', 'ground/PAGES_KEEP_PATHS.md', 'ground/PC_SHARE.md', 'ground/PEER_PACKET_20260819.md', 'ground/PEER_WAKE_BUS.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
