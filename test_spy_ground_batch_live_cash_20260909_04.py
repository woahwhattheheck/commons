import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/SLACK_CONTROL_PLANE.md', 'ground/SLACK_CUSTOM_TOOLS_CLI_CHALLENGE.md', 'ground/SLACK_CUSTOM_TOOLS_CLI_PROJECT.md', 'ground/SLACK_CUSTOM_TOOLS_INSTALL.md', 'ground/SLACK_RECEIPT.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
