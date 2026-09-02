#!/usr/bin/env python3
"""Pin independent ACK of Harborline pack-market unique-pack. Do not steal /market."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACK = ROOT / "p/cursor-harborline-pack-market-render-readback-ack-20260902-01.md"
UNIQUE = ROOT / "p/cursor-harborline-pack-market-render-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-harborline-pack-market-render-20260902-01.md"
HELPER = ROOT / "host/harborline_pack_market_render.py"

KEEP = {
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "host/harborline_pack_market_render.py": "cc9a3320",
    "test_harborline_pack_market_render.py": "cf40d758",
    "p/cursor-harborline-pack-market-render-readback-20260902-01.md": "6efbac54",
    "test_harborline_pack_market_render_readback.py": "a95c2d3c",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "host/harborline_qualify_live_probe.py": "2c1797b2",
    "ground/OWNER_NOW.md": "59b1fd37",
    "p/cursor-owner-now-revenue-20260902-01.md": "fe5ba035",
    "p/cursor-owner-now-revenue-readback-20260902-01.md": "3449da29",
    "p/cursor-big-things-incoming-shots-20260902-01.md": "60b24eff",
    "p/cursor-big-things-incoming-shots-readback-20260902-01.md": "3cabb764",
    "p/cursor-incoming-models-hub-payload-20260902-01.md": "63aa4736",
    "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "autogtm.html": "9d8b3e85",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestHarborlinePackMarketRenderReadbackAck(unittest.TestCase):
    def test_keep_leftover_helper_and_unique_pack(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_json_still_render(self) -> None:
        packet = json.loads(
            subprocess.check_output(
                [sys.executable, str(HELPER), "--json"], cwd=ROOT, text=True
            )
        )
        self.assertEqual(packet["verdict"], "RENDER", packet)
        self.assertEqual(packet["store"], "standalone")
        self.assertFalse(packet["commons_is_store"])
        self.assertFalse(packet["marketplace_html_on_commons"])
        self.assertEqual(packet["sent"], 0)
        self.assertEqual(packet["cash"], 0)
        self.assertEqual(packet["checkout"], "FINDER-FAILED")

    def test_send_go_dump_still_refused(self) -> None:
        for flag in ("--send", "--go", "--dump-commons"):
            proc = subprocess.run(
                [sys.executable, str(HELPER), flag],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 2, msg=flag + proc.stdout + proc.stderr)
            packet = json.loads(proc.stdout)
            self.assertEqual(packet["sent"], 0, flag)
            self.assertEqual(packet["refused"], flag)

    def test_ack_cites_unique_pack_without_reminting(self) -> None:
        text = ACK.read_text(encoding="utf-8")
        unique = UNIQUE.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn(
            "cursor-harborline-pack-market-render-readback-ack-20260902-01", text
        )
        self.assertIn(
            "cursor-harborline-pack-market-render-readback-20260902-01", text
        )
        self.assertIn("3a418c574", text)
        self.assertIn("0141bf7c8", text)
        self.assertIn("54c348dc", text)
        self.assertIn("6efbac54", text)
        self.assertIn("Did not remint leftover helper", text)
        self.assertIn("Did not dump", text)
        self.assertIn("Did not steal", text)
        self.assertIn("Did not invent Stripe URLs", text)
        self.assertIn("bc-b0b8882f", text)
        self.assertNotEqual(text, unique)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(
            git_blob(
                "p/cursor-harborline-pack-market-render-readback-ack-20260902-01.md"
            ),
            git_blob(
                "p/cursor-harborline-pack-market-render-readback-20260902-01.md"
            ),
        )
        self.assertNotIn("https://buy.stripe.com/", text)
        self.assertNotIn("qualify.html", text)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
