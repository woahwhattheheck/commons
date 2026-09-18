import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/MEASURE_ABUSE.md', 'ground/MIRROR_MESH_0.md', 'ground/MODEL_LANGUAGE.md', 'ground/MOVING_MAIN_MIRROR.md', 'ground/MUHC.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
