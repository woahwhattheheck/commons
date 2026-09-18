import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PICK = ROOT / "ground" / "owner_walls" / "header-184-host-write-ban-20260830-01.json"
POST = ROOT / "p" / "cursor-grok-header-184-yes-20260830-01.md"
UNFINISHED = ROOT / "muhl" / "docs" / "UNFINISHED.md"


class Header184WriteBanTests(unittest.TestCase):
    def test_pick_is_yes_host_write_ban(self):
        card = json.loads(PICK.read_text(encoding="utf-8"))
        self.assertEqual(card["id"], "cursor-grok-header-184-yes-20260830-01")
        self.assertEqual(card["wall"], "header @184 yes/no")
        self.assertEqual(card["unfinished_item"], 12)
        self.assertEqual(card["pick"], "YES")
        self.assertEqual(card["meaning"], "host write-ban on the header total")
        self.assertFalse(card["fire_337"])
        self.assertFalse(card["invented_dest"])
        self.assertEqual(card["live_inject"], "NEED_OWNER")
        self.assertIn("YES", POST.read_text(encoding="utf-8"))

    def test_does_not_mutate_unfinished_harvest(self):
        text = UNFINISHED.read_text(encoding="utf-8")
        self.assertIn("### 12. @184 host write-ban yes or no", text)
        self.assertIn("Header total. Not thrown.", text)


if __name__ == "__main__":
    unittest.main()
