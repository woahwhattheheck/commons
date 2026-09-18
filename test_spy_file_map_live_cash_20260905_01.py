import unittest
from pathlib import Path
T=(Path(__file__).resolve().parent/'ground/FILE_MAP.md').read_text()
class X(unittest.TestCase):
    def test(self):
        self.assertIn('## Live cash', T)
        self.assertIn('dealer-service-lead-rescue.html', T)
if __name__=='__main__':
    unittest.main()
