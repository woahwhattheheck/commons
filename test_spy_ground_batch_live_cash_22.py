import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/MUHC_CORPUS.md', 'ground/MUHL_FILM_ORGAN.md', 'ground/MUHL_SELF_TRAIN_ADDRESS_CONTRACT.md', 'ground/MNO_DATASHEETS_20260819.md', 'ground/P4_CLOSED.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
