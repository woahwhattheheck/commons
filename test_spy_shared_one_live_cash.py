import unittest
from pathlib import Path
T=(Path(__file__).resolve().parent/'ground'/'SHARED_ONE.md').read_text()
class X(unittest.TestCase):
    def test(self):
        self.assertIn('## Live cash', T)
        self.assertIn('agent-rescue.html', T)
if __name__=='__main__':
    unittest.main()
