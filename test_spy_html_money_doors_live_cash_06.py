import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['weather.html', 'toolbench.html', 'subzero.html', 'scope-to-delivery.html', 'feature-tracker.html']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('id="live-cash"', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
