"""wire-agents-tools-build-md-keep-larger-fixed-20260916-01 — KEEP proof for AGENTS/TOOLS/BUILD MD."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "wire-agents-tools-build-md-keep-larger-fixed-20260916-01"
INK = "ink-readme-lanes-larger-fixed-20260916-01"
NEEDLES = (
    "Larger fixed engagements",
    "./diagnostic.html",
    "./commercial.html",
    "$12,000",
    "$30,000",
    "./agent-rescue.html",
    "$199",
)
PRODUCTS = (
    "agent-rescue.html",
    "diagnostic.html",
    "commercial.html",
)
# leftover-census.md stays pin-locked — do not remint.
# TOOLS.md / BUILD.md are absent on tip; do not invent those files.


def _cash(text: str) -> str:
    idx = text.find("## Live cash")
    return text[idx:] if idx >= 0 else text


class TestWireAgentsToolsBuildMdKeepLargerFixed2026091601(unittest.TestCase):
    def test_agents_md_already_keep_larger(self):
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("## Live cash", text)
        self.assertIn("Autopsy", text)
        for needle in NEEDLES:
            self.assertIn(needle, text)
        self.assertNotIn("buy.stripe.com", _cash(text))

    def test_tools_md_and_build_md_absent_or_keep(self):
        for name in ("TOOLS.md", "BUILD.md"):
            path = ROOT / name
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            live = ("Live cash" in text) or ("Autopsy" in text) or ("$199" in text)
            if not live:
                continue
            self.assertIn("Larger fixed engagements", text, name)
            self.assertIn("diagnostic.html", text, name)
            self.assertIn("commercial.html", text, name)
            self.assertIn("$12,000", text, name)
            self.assertIn("$30,000", text, name)
            self.assertNotIn("buy.stripe.com", _cash(text), name)

    def test_readme_already_keep_leave_ink(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("## Live cash", text)
        self.assertIn("Autopsy", text)
        for needle in NEEDLES:
            self.assertIn(needle, text)
        self.assertNotIn("buy.stripe.com", _cash(text))
        ink = (ROOT / "p" / f"{INK}.md").read_text(encoding="utf-8")
        self.assertIn(INK, ink)
        self.assertIn("README.md", ink)

    def test_product_pages_exist(self):
        for name in PRODUCTS:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_receipt(self):
        text = (ROOT / "p" / f"{CLAIM}.md").read_text(encoding="utf-8")
        self.assertIn(CLAIM, text)
        self.assertIn("Tip KEEP", text)
        self.assertIn("#8802", text)
        self.assertIn("AGENTS.md", text)
        self.assertIn("TOOLS.md", text)
        self.assertIn("BUILD.md", text)
        self.assertIn("README.md", text)
        self.assertIn(INK, text)


if __name__ == "__main__":
    unittest.main()
