#!/usr/bin/env python3
"""Lift leftover KEEP freeze of OWNER_NOW.md after invented 337 closer strip."""
from __future__ import annotations

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


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class GrokbuildOwnerNow337CloserStripTest(unittest.TestCase):
    def test_leftover_keep_does_not_freeze_owner_now(self) -> None:
        import test_owner_now_readback as readback
        import test_owner_now_revenue as revenue
        import test_owner_now_revenue_readback as revenue_rb
        import test_incoming_models_hub_payload_readback as incoming
        import test_incoming_models_hub_payload_readback_rematch as incoming_rematch
        import test_big_things_incoming_shots as shots
        import test_big_things_incoming_shots_readback as shots_rb
        import test_autogtm_door_hub_readback_ack as autogtm_ack
        import test_autogtm_hub_pages_live_get_readback as live_get
        import test_autogtm_hub_pages_live_get_readback_ack as live_get_ack
        import test_big_things_incoming_alert as alert
        import test_big_things_incoming_alert_ack as alert_ack
        import test_grokbuild_autogtm_hub_pages_keep_unpin as unpin
        import test_harborline_pack_market_render as harborline
        import test_harborline_pack_market_render_readback as harborline_rb

        for mod in (
            readback,
            revenue,
            revenue_rb,
            incoming,
            incoming_rematch,
            shots,
            shots_rb,
            harborline,
            harborline_rb,
            autogtm_ack,
            live_get,
            live_get_ack,
            alert,
            alert_ack,
            unpin,
        ):
            self.assertNotIn("ground/OWNER_NOW.md", getattr(mod, "KEEP", {}), mod.__name__)
            self.assertNotIn("hub_pages.py", getattr(mod, "KEEP", {}), mod.__name__)
            self.assertNotIn("door.js", getattr(mod, "KEEP", {}), mod.__name__)
            unread = getattr(mod, "KEEP_UNREAD", {})
            self.assertNotIn("hub_pages.py", unread, mod.__name__)
            self.assertNotIn("door.js", unread, mod.__name__)
        self.assertNotIn("test_big_things_incoming_shots.py", shots_rb.KEEP)
        self.assertNotIn("host/owner_now_revenue.py", revenue_rb.KEEP)
        self.assertNotIn("test_owner_now_revenue.py", revenue_rb.KEEP)
        self.assertNotIn("test_harborline_pack_market_render.py", harborline_rb.KEEP)
        self.assertNotIn("test_incoming_models_hub_payload_readback.py", incoming_rematch.KEEP)
        self.assertNotIn("test_harborline_pack_market_render.py", incoming_rematch.KEEP)

    def test_owner_now_meaning_kept_without_invented_signature(self) -> None:
        text = CARD.read_text(encoding="utf-8")
        self.assertNotIn(SIGNATURE, text)
        self.assertIn("Point is generate revenue", text)
        self.assertIn("Stop zero-cash signoffs and integrity theater", text)
        self.assertIn("invented 337 closer was never Bryce law", text)
        self.assertIn("## Retired (peer virus, never owner law)", text)
        self.assertIn("NOT_MINTED as a freeze", text)
        self.assertIn("Mint real Stripe Payment Links when it helps", text)

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
