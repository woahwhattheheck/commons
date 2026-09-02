#!/usr/bin/env python3
"""Lift leftover KEEP freeze of OWNER_NOW.md after invented 337 closer strip."""
from __future__ import annotations

import importlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CARD = ROOT / "ground/OWNER_NOW.md"
SIGNATURE = "337 NO"
UNPIN_RECEIPT = ROOT / "p/grokbuild-owner-now-337-closer-strip-20260902-01.md"

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
    "test_owner_now_readback",
    "test_owner_now_revenue",
    "test_owner_now_revenue_readback",
    "test_owner_now_revenue_readback_ack",
    "test_incoming_models_hub_payload_readback",
    "test_incoming_models_hub_payload_readback_rematch",
    "test_big_things_incoming_shots",
    "test_big_things_incoming_shots_readback",
    "test_big_things_incoming_shots_readback_ack",
    "test_big_things_incoming_shots_readback_rematch",
    "test_autogtm_door_hub_readback_ack",
    "test_autogtm_hub_pages_live_get_readback",
    "test_autogtm_hub_pages_live_get_readback_ack",
    "test_big_things_incoming_alert",
    "test_big_things_incoming_alert_ack",
    "test_grokbuild_autogtm_hub_pages_keep_unpin",
    "test_harborline_pack_market_render",
    "test_harborline_pack_market_render_readback",
    "test_harborline_pack_market_render_readback_ack",
    "test_harborline_pack_market_render_readback_rematch",
    "test_harborline_pack_market_slack_render",
    "test_harborline_pack_market_render_ship",
    "test_landed_work_feed",
    "test_landed_work_feed_readback",
    "test_grokbuild_pr8345_terminal",
    "test_grokbuild_pr8357_terminal",
)


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class GrokbuildOwnerNow337CloserStripTest(unittest.TestCase):
    def test_leftover_keep_does_not_freeze_owner_now_or_stale_hub(self) -> None:
        for name in KEEP_MODULES:
            mod = importlib.import_module(name)
            keep = getattr(mod, "KEEP", {})
            unread = getattr(mod, "KEEP_UNREAD", {})
            self.assertNotIn("ground/OWNER_NOW.md", keep, name)
            self.assertNotEqual(keep.get("hub_pages.py"), "14eeedb0", name)
            self.assertNotEqual(keep.get("door.js"), "1f9e8d14", name)
            self.assertNotIn("hub_pages.py", unread, name)
            self.assertNotIn("door.js", unread, name)

    def test_owner_now_meaning_kept_without_invented_signature(self) -> None:
        text = CARD.read_text(encoding="utf-8")
        self.assertNotIn(SIGNATURE, text)
        self.assertIn("Point is generate revenue", text)
        self.assertIn("Stop zero-cash signoffs and integrity theater", text)
        self.assertIn("invented 337 closer was never Bryce law", text)
        self.assertIn("## Retired (peer virus, never owner law)", text)
        self.assertIn("NOT_MINTED as a freeze", text)
        self.assertIn("Mint real Stripe Payment Links when it helps", text)

    def test_living_scan_no_longer_exempts_owner_now(self) -> None:
        import test_337_no_signature_absent_from_living_sources as living

        self.assertFalse(hasattr(living, "OWNER_RETIREMENT_RECORDS"))
        source = Path(living.__file__).read_text(encoding="utf-8")
        self.assertIn('"ground/OWNER_NOW.md"', source)
        self.assertNotIn("OWNER_RETIREMENT_RECORDS", source)

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
