#!/usr/bin/env python3
"""Pin independent ACK leftover. Do not remint the original alert or AutoGTM."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ORIGINAL = ROOT / "p/cursor-big-things-incoming-alert-20260902-01.md"
ACK = ROOT / "p/cursor-big-things-incoming-alert-ack-20260902-01.md"

KEEP = {
    "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "autogtm.html": "9d8b3e85",
    "p/cursor-autogtm-hub-pages-live-get-readback-20260902-01.md": "c2829fc5",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestBigThingsIncomingAlertAck(unittest.TestCase):
    def test_keep_original_alert_and_autogtm_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_ack_cites_original_without_reminting(self) -> None:
        text = ACK.read_text(encoding="utf-8")
        self.assertIn("cursor-big-things-incoming-alert-ack-20260902-01", text)
        self.assertIn("cursor-big-things-incoming-alert-20260902-01", text)
        self.assertIn("8b029bf5785dabc3afa98e9f353af186eaf2ac84", text)
        self.assertIn("fde942266431644b59a91e2e55a78b1e221ee789", text)
        self.assertIn("1788380844.707619", text)
        self.assertIn("Big things incoming alert the peers", text)
        self.assertIn("Did not invent", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertIn("CZ-03", text)
        self.assertIn("bc-609d43f6", text)
        self.assertIn("#new-channel", text)
        self.assertNotIn("qualify.html", text)
        self.assertNotEqual(
            git_blob("p/cursor-big-things-incoming-alert-ack-20260902-01.md"),
            git_blob("p/cursor-big-things-incoming-alert-20260902-01.md"),
        )

    def test_original_still_relays_exact_hub_line(self) -> None:
        text = ORIGINAL.read_text(encoding="utf-8")
        self.assertIn("1788380844.707619", text)
        self.assertIn("Big things incoming alert the peers", text)
        self.assertIn("Did not invent", text)

    def test_did_not_dump_qualify_html_or_corner(self) -> None:
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
