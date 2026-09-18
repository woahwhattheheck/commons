import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class HubPagesEncodingTest(unittest.TestCase):
    def test_active_hub_templates_have_no_replacement_or_substitute_controls(self) -> None:
        source = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        self.assertNotIn("\ufffd", source)
        self.assertNotIn("\x1a", source)

    def test_home_vent_pointer_has_no_stray_historical_token(self) -> None:
        home = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("Scratch pad, not punishment.</p>", home)
        self.assertNotIn("Scratch pad, not punishment. owdvmf.</p>", home)


if __name__ == "__main__":
    unittest.main()
