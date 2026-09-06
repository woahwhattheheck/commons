import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/BUSINESS_PACK_PAPERWORK_FILLED.md', 'ground/BUSINESS_PACK_PAPERWORK_INCLUDED.md', 'ground/BUSINESS_PACK_PAPERWORK_SLOT.md', 'ground/CARRIER_PICKUP.md', 'ground/CCC_VAULT_HARVEST.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
