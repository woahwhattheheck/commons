import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/LDA_ANDROID_CI.md', 'ground/LDA_RECEIPT.md', 'ground/JOJO_ASSIGN.md', 'ground/INVENTION_BURST_INDEX.md', 'ground/IP_FILING_INDEX.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
