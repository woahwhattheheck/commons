#!/usr/bin/env python3
"""Lift leftover KEEP freeze of reminted hub_pages.py / door.js after 337 closer strip landed."""
from __future__ import annotations

import importlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UNPIN_RECEIPT = ROOT / "p/grokbuild-owner-now-337-closer-strip-20260902-01.md"
CARD = ROOT / "ground/OWNER_NOW.md"
SIGNATURE = "337 NO"

KEEP_UNREAD = {
    "p/cursor-owner-now-readback-20260902-01.md": "1b3cd631",
    "p/cursor-owner-now-revenue-20260902-01.md": "fe5ba035",
    "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "p/cursor-big-things-incoming-shots-20260902-01.md": "60b24eff",
    "p/cursor-incoming-models-hub-payload-20260902-01.md": "63aa4736",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "autogtm.html": "9d8b3e85",
}

KEEP_MODULES = (
    "test_autogtm_door_hub_readback_ack",
    "test_autogtm_hub_pages_live_get_readback",
    "test_autogtm_hub_pages_live_get_readback_ack",
    "test_big_things_incoming_alert",
    "test_big_things_incoming_alert_ack",
    "test_big_things_incoming_shots",
    "test_big_things_incoming_shots_readback",
    "test_grokbuild_autogtm_hub_pages_keep_unpin",
    "test_harborline_pack_market_render",
    "test_harborline_pack_market_render_readback",
    "test_owner_now_revenue",
    "test_owner_now_revenue_readback",
)


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class GrokbuildOwnerNow337CloserStripTest(unittest.TestCase):
    def test_leftover_keep_does_not_freeze_stale_hub_or_door(self) -> None:
        for name in KEEP_MODULES:
            mod = importlib.import_module(name)
            keep = getattr(mod, "KEEP", {})
            unread = getattr(mod, "KEEP_UNREAD", {})
            self.assertNotEqual(keep.get("hub_pages.py"), "14eeedb0", name)
            self.assertNotEqual(keep.get("door.js"), "1f9e8d14", name)
            self.assertNotEqual(unread.get("hub_pages.py"), "14eeedb0", name)
            self.assertNotEqual(unread.get("door.js"), "1f9e8d14", name)

    def test_living_owner_now_stays_clear_of_invented_signature(self) -> None:
        text = CARD.read_text(encoding="utf-8")
        self.assertNotIn(SIGNATURE, text)
        self.assertIn("Point is generate revenue", text)
        self.assertIn("invented closer was never Bryce law", text)
        self.assertIn("## Retired (peer virus, never owner law)", text)

    def test_did_not_remint_unread_unique_packs(self) -> None:
        for rel, prefix in KEEP_UNREAD.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        unpin = UNPIN_RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: grokbuild-owner-now-337-closer-strip-20260902-01", unpin)
        self.assertIn("6b8ee988", unpin)
        self.assertIn("Did not remint", unpin)
        self.assertIn("#7915", unpin)
        self.assertIn("NOT_MINTED", unpin)
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
