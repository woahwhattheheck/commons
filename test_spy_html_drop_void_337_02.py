import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['look.html', 'offer.html', 'shots.html', 'flipbook.html', 'net159.html']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            self.assertNotIn('337 NO', (ROOT/rel).read_text(), rel)
if __name__=='__main__':
    unittest.main()
