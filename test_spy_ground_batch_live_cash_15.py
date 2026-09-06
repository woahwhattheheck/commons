import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/COMMONS_SLACK_FULL_BODY.md', 'ground/CONTAINMENT.md', 'ground/CONTEXT_INTEGRITY.md', 'ground/DELTA.md', 'ground/DIO_CRLF.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
