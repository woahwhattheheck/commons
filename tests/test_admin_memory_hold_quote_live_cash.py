from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class T(unittest.TestCase):
    def test(self):
        text=(ROOT/'memory/HOLD_QUOTE.md').read_text(encoding='utf-8')
        self.assertIn('## Live cash', text)
        self.assertIn('../agent-rescue.html', text)
if __name__=='__main__': unittest.main()
