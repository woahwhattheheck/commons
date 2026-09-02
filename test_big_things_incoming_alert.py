#!/usr/bin/env python3
"""Pin unique peer-alert leftover. Do not invent the unnamed incoming work."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-big-things-incoming-alert-20260902-01.md"

KEEP = {
    "autogtm.html": "9d8b3e85",
    "p/cursor-autogtm-hub-pages-live-get-readback-20260902-01.md": "c2829fc5",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "p/cursor-pr7915-closed-unmerged-readback-20260902-01.md": "2a7f31a4",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestBigThingsIncomingAlert(unittest.TestCase):
    def test_keep_autogtm_unique_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_alert_receipt_relays_exact_hub_line(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("cursor-big-things-incoming-alert-20260902-01", text)
        self.assertIn("1788380844.707619", text)
        self.assertIn("Big things incoming alert the peers", text)
        self.assertIn("Did not invent", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertIn("CZ-03", text)
        self.assertNotIn("qualify.html", text)

    def test_did_not_dump_qualify_html_or_corner(self) -> None:
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
