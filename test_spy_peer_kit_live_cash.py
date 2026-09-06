import unittest
from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "ground" / "PEER_KIT.md").read_text()
class T(unittest.TestCase):
    def test(self):
        self.assertIn("## Live cash", TEXT)
        self.assertIn("agent-rescue.html", TEXT)
        self.assertNotIn("Do not fire 337", TEXT)
if __name__ == "__main__":
    unittest.main()
