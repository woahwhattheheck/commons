#!/usr/bin/env python3
"""KEEP-lift leftover incoming-models freeze after NEWBOT #14994 helper remint.

#14994 baked tip #live-cash + Larger fixed into host/incoming_models.render_html
so --write-html no longer wipes diagnostic.html/$12k · commercial.html/$30k.
Leftover KEEP dicts still froze helper 7f4ae3bf vs live 108797f0, and the
TYPE #14975 door 56aab207 vs leftover ef42b9d5. Lift living pins. Do not remint
leftover unique-pack receipts or NEWBOT id.
"""
from __future__ import annotations

import importlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER_BLOB = "108797f0"
STALE_HELPER = "7f4ae3bf"
HTML_BLOB = "56aab207"
STALE_HTML = "ef42b9d5"
READBACK_BLOB = "3d509221"
STALE_READBACK = "1fd96349"

KEEP_UNREAD = {
    "p/cursor-incoming-models-hub-payload-20260902-01.md": "63aa4736",
    "p/cursor-incoming-models-hub-payload-readback-20260902-01.md": "2d297673",
    "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "test_incoming_models.py": "d8f2ddbd",
    "ground/INCOMING_MODELS.json": "6b5e89dc",
    "autogtm.html": "2fe108f4",
}

KEEP_MODULES = (
    "test_incoming_models_hub_payload_readback",
    "test_incoming_models_hub_payload_readback_rematch",
)


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokIncomingModelsKeepLift2026091601(unittest.TestCase):
    def test_leftover_keep_no_longer_freezes_stale_helper_or_html(self) -> None:
        for name in KEEP_MODULES:
            mod = importlib.import_module(name)
            keep = getattr(mod, "KEEP", {})
            self.assertNotEqual(keep.get("host/incoming_models.py"), STALE_HELPER, name)
            self.assertNotEqual(keep.get("incoming-models.html"), STALE_HTML, name)
            self.assertEqual(keep.get("host/incoming_models.py"), HELPER_BLOB, name)
            self.assertEqual(keep.get("incoming-models.html"), HTML_BLOB, name)
        rematch = importlib.import_module(
            "test_incoming_models_hub_payload_readback_rematch"
        )
        self.assertEqual(
            rematch.KEEP.get("test_incoming_models_hub_payload_readback.py"),
            READBACK_BLOB,
        )
        self.assertNotEqual(
            rematch.KEEP.get("test_incoming_models_hub_payload_readback.py"),
            STALE_READBACK,
        )

    def test_live_blobs_and_larger_fixed_still_on_render(self) -> None:
        helper = git_blob("host/incoming_models.py")
        html = git_blob("incoming-models.html")
        readback = git_blob("test_incoming_models_hub_payload_readback.py")
        self.assertTrue(helper.startswith(HELPER_BLOB), helper)
        self.assertFalse(helper.startswith(STALE_HELPER), helper)
        self.assertTrue(html.startswith(HTML_BLOB), html)
        self.assertFalse(html.startswith(STALE_HTML), html)
        self.assertTrue(readback.startswith(READBACK_BLOB), readback)
        src = (ROOT / "host/incoming_models.py").read_text(encoding="utf-8")
        tip = (ROOT / "incoming-models.html").read_text(encoding="utf-8")
        for text in (src, tip):
            self.assertIn("Larger fixed engagements", text)
            self.assertIn("diagnostic.html", text)
            self.assertIn("commercial.html", text)
            self.assertIn('id="live-cash"', text)
            self.assertNotIn("buy.stripe.com", text)
        self.assertIn("LIVE_CASH_HTML", src)
        self.assertNotIn("337 NO", tip)

    def test_leftover_receipts_not_reminted(self) -> None:
        for rel, prefix in KEEP_UNREAD.items():
            blob = git_blob(rel)
            self.assertTrue(blob.startswith(prefix), f"{rel}: want {prefix} got {blob[:8]}")


if __name__ == "__main__":
    unittest.main()
