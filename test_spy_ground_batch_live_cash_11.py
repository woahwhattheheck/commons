import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/COMMONS_ARCHITECTURE_300FT.md', 'ground/COMMONS_PROVIDER_MAP.md', 'ground/COMMONS_ADMISSIBILITY_AND_EXECUTION.md', 'ground/CLOUD_CURRENT.md', 'ground/CLOUD_STORAGE_ONLY.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
