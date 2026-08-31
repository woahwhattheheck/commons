#!/usr/bin/env python3
"""Canaries for the public TITAN Hands FREE SAMPLE.

The door must cite already-landed proof (MCP entrypoint, receipts, APK SHA).
The sales insert is a paste sheet, not outreach, and must not claim a walk,
cash, or a fabricated live demo.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "titan-hands-free-sample.html"
INSERT = ROOT / "titan-hands-sample" / "SALES-INSERT.md"
POST = ROOT / "p" / "titan-hands-free-sample-20260830-01.md"
MANIFEST = ROOT / "artifacts" / "commons_android" / "manifest.json"
MCP = ROOT / ".cursor" / "mcp.json"

BANNED_INSERT = (
    "titan-walk",
    "titan walk",
    "live walker in the browser",
    "we just ran it on your phone",
    "stripe.com/buy",
    "shopify.com",
)

SETH_PATHS = (
    ROOT / "free-sample.html",
    ROOT / "sales-sample" / "FREE-SAMPLE-SALES-INSERT.md",
    ROOT / "test_sales_free_sample_pack.py",
    ROOT / "p" / "sales-free-sample-pack-20260830-01.md",
)
ADAM_PATHS = (
    ROOT / "muhlnickel-free-sample.html",
    ROOT / "p" / "muhlnickel-free-sample-20260830-01.md",
)


class TitanHandsFreeSampleTests(unittest.TestCase):
    def test_page_cites_landed_mcp_and_apk_sha(self) -> None:
        page = PAGE.read_text(encoding="utf-8")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        mcp = json.loads(MCP.read_text(encoding="utf-8"))
        sha = manifest["apk_sha256"]
        args = mcp["mcpServers"]["titan_hands"]["args"]

        self.assertEqual(sha, "6eddd9378738e015623ad0bfad6f754c3255194abe995ac46f59bdfd97e3e96a")
        self.assertEqual(manifest["device_runtime_state"], "DEVICE_UNVERIFIED")
        self.assertEqual(args, ["-m", "host.titan_hands.mcp_one"])

        for token in (
            sha,
            "DEVICE_UNVERIFIED",
            "python -m host.titan_hands.mcp_one",
            "STRUCTURAL",
            "DEVICE-UNVERIFIED",
            "NOT-A-WALK",
            "docs/TITAN_HANDS.md",
            "docs/TITAN_HANDS_PEERS.md",
            "emissary-titan-hands-features-20260826-01",
            "coil-titan-hands-linux-atspi-land-20260827-01",
            "gpt-titan-hands-windows-direct-mcp-proof-20260826-01",
            "host.titan_hands.tests.test_peer_configs",
            "test_titan_hands_one_tool.py",
        ):
            self.assertIn(token, page, token)
        self.assertIn("login", page.lower())
        self.assertNotIn("login required", page.lower())
        self.assertNotIn("must authenticate", page.lower())
        self.assertNotIn("MEMORY_GATE", page)

    def test_insert_is_a_sales_paste_not_a_walk_claim(self) -> None:
        insert = INSERT.read_text(encoding="utf-8")
        page = PAGE.read_text(encoding="utf-8")
        sha = json.loads(MANIFEST.read_text(encoding="utf-8"))["apk_sha256"]
        self.assertIn(
            "https://woahwhattheheck.github.io/commons/titan-hands-free-sample.html",
            insert,
        )
        self.assertIn(sha, insert)
        self.assertIn("STRUCTURAL", insert)
        self.assertIn("DEVICE-UNVERIFIED", insert)
        self.assertIn("NOT-A-WALK", insert)
        self.assertIn("not outreach", insert.lower())
        self.assertIn("Not buyers", insert)
        self.assertIn("titan-hour.html", insert)
        lowered = insert.lower()
        for banned in BANNED_INSERT:
            self.assertNotIn(banned, lowered, banned)
        self.assertIn("titan-hands-sample/SALES-INSERT.md", page)
        self.assertNotIn("https://woahwhattheheck.github.io/commons/free-sample.html", insert)

    def test_does_not_remint_seth_or_adam_or_pitch_card(self) -> None:
        unique = {
            PAGE,
            INSERT,
            POST,
            ROOT / "test_titan_hands_free_sample.py",
        }
        for path in unique:
            self.assertTrue(path.is_file(), str(path))
        pitch = (ROOT / "titan-hands.html").read_text(encoding="utf-8")
        self.assertIn("One model-facing tool", pitch)
        self.assertNotIn("titan-hands-free-sample-20260830-01", pitch)
        for path in SETH_PATHS + ADAM_PATHS:
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("titan-hands-free-sample.html", text)

    def test_receipt_names_scope(self) -> None:
        post = POST.read_text(encoding="utf-8")
        self.assertIn("id: titan-hands-free-sample-20260830-01", post)
        self.assertIn("https://woahwhattheheck.github.io/commons/titan-hands-free-sample.html", post)
        self.assertIn("STRUCTURAL", post)
        self.assertIn("DEVICE-UNVERIFIED", post)
        self.assertIn("NOT-A-WALK", post)
        self.assertIn("no outreach", post.lower())
        self.assertIn("titan-hands.html", post)
        self.assertIn("sales-free-sample-pack-20260830-01", post)
        self.assertIn("muhlnickel-free-sample-20260830-01", post)


if __name__ == "__main__":
    unittest.main()
