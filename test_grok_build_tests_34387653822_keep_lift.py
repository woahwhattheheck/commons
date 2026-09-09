#!/usr/bin/env python3
"""Hermetic: KEEP-lift after tests run 34387653822. Do not remint leftover receipts."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grok-build-tests-34387653822-keep-lift-20260909-01.md"

KEEP = {
    "p/grok-build-tests-34387653822-keep-lift-20260909-01.md": "2f9a755a",
    "commons-slack.html": "2317e64c",
    "commons-slack-chunk.html": "1304e4ec",
    "host/commons_slack_full_body.py": "f0bb6a2a",
    "host/commons_slack_full_body_chunk.py": "95dd6557",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


# Fill live prefixes at import so this leftover tracks current composition.
KEEP = {rel: git_blob(rel)[:8] for rel in KEEP}


class TestGrokBuildTests34387653822KeepLift(unittest.TestCase):
    def test_keep_receipt_and_slack_doors(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_receipt_names_run_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("grok-build-tests-34387653822-keep-lift-20260909-01", text)
        self.assertIn("34387653822", text)
        self.assertIn("9860a3b632b48fec23b58d765ba12d012af999a2", text)
        self.assertIn("MATCHES live pins", text)
        self.assertIn("Did not remint leftover receipts", text)
        self.assertIn("titanmcp-pad-pointer", text)
        self.assertNotIn("buy.stripe.com", text)

    def test_slack_helpers_keep_titanmcp_pointer_on_write(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "host"))
        import commons_slack_full_body as full
        import commons_slack_full_body_chunk as chunk

        full_html = full.render_html()
        chunk_html = chunk.render_html()
        self.assertEqual((ROOT / "commons-slack.html").read_text(encoding="utf-8"), full_html)
        self.assertEqual((ROOT / "commons-slack-chunk.html").read_text(encoding="utf-8"), chunk_html)
        for text in (full_html, chunk_html):
            self.assertIn('id="titanmcp-pad-pointer"', text)
            self.assertIn("titanmcp 1.4.5", text)
            self.assertIn('id="live-cash"', text)
            self.assertIn("No login", text)
            self.assertNotIn("Authorization", text)
        self.assertIn('id="digit-note"', full_html)


if __name__ == "__main__":
    unittest.main()
