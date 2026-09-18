import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/FOUNDRY_LAND_20260819.md', 'ground/GEMMA_TOKENIZER_MAP.md', 'ground/GITHUB_CALL_NOT_LOGIN.md', 'ground/H002.md', 'ground/H009.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
