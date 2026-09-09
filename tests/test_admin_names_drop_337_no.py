from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class T(unittest.TestCase):
    def test(self):
        text=(ROOT/'names.html').read_text(encoding='utf-8')
        self.assertNotIn('Do not fire 337', text)
        self.assertIn('Do not smash commons.mno', text)
if __name__=='__main__': unittest.main()
