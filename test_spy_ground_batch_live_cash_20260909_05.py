import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ground/SLACK_SERVICE_ALL_DRIVERS.md', 'ground/SLACK_SERVICE_TAGS.md', 'ground/SLACK_SPARK_MCP_DRIVER.md', 'ground/SPECTER_FINAL.md', 'ground/SPEC_DADDY_STUDY.md']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('## Live cash', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
