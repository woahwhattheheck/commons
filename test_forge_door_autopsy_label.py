"""Drive door to agent-rescue.html must label live Autopsy $29, not agent survival."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
DOOR = ROOT / "door.js"
INDEX = ROOT / "index.html"


class ForgeDoorAutopsyLabelTests(unittest.TestCase):
    def test_door_js_catalog_label(self):
        text = DOOR.read_text(encoding="utf-8")
        self.assertIn('["agent-rescue.html", "Agent Failure Autopsy · $29"]', text)
        self.assertNotIn('["agent-rescue.html", "agent survival"]', text)
        self.assertIn("relabelStaticAutopsyDoor", text)

    def test_index_static_hub_still_has_rescue_href(self):
        # Static HTML may lag until a later bytes patch; door.js relabels when JS runs.
        text = INDEX.read_text(encoding="utf-8")
        self.assertIn("agent-rescue.html", text)
        self.assertIn('id="door-hub"', text)


if __name__ == "__main__":
    unittest.main()
