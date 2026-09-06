import unittest
from pathlib import Path
T=(Path(__file__).resolve().parent/'redundancy.html').read_text()
class X(unittest.TestCase):
    def test(self):
        self.assertIn('id="live-cash"', T)
        self.assertIn('agent-rescue.html', T)
if __name__=='__main__':
    unittest.main()
