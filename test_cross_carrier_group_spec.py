#!/usr/bin/env python3
"""Cross-carrier group-chat spec: Slack+Telegram+harnesses, no seats/gates/phone."""
from __future__ import annotations

from pathlib import Path
import hashlib
import unittest

from test_telegram_peers import INVITE, PHONE, PAGE as TELEGRAM_PAGE


ROOT = Path(__file__).resolve().parent
SPEC = ROOT / "ground" / "CROSS_CARRIER_GROUP.md"
RECEIPT = ROOT / "p" / "group-chat-cross-carrier-spec-20260830-01.md"
PEERS = ROOT / "peers.html"
TELEGRAM_PIN = ROOT / "p" / "commons-peers-telegram-20260829-01.md"
# Live blobs when this leftover was named against HEAD 0152b5c2. Do not remint.
TELEGRAM_HTML_BLOB = "7250c2fec0472a14b7e1e56ec03d7f58b7250fe7"
TELEGRAM_PIN_BLOB = "b75cbc844c4e9dcf3af3c545a3f091f85d5af77e"
NEW_PATHS = (SPEC, RECEIPT)


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class CrossCarrierGroupSpec(unittest.TestCase):
    def test_spec_exists_and_names_carriers(self):
        spec = SPEC.read_text(encoding="utf-8")
        self.assertTrue(SPEC.is_file())
        self.assertIn("Slack", spec)
        self.assertIn("#commons", spec)
        self.assertIn("Telegram", spec)
        self.assertIn("Cursor", spec)
        self.assertIn("Claude", spec)
        self.assertIn("ChatGPT", spec)
        self.assertIn("Swarm", spec)
        self.assertIn("p/{id}.md", spec)
        self.assertIn("carrier_ts", spec)
        self.assertIn("exact body", spec)
        self.assertIn("one conversation identity", spec.lower())

    def test_forbids_seats_gates_and_phone_directory(self):
        spec = SPEC.read_text(encoding="utf-8")
        for marker in (
            "No seats",
            "No login",
            "No MEMORY_GATE",
            "No allowlist",
            "not a phone directory",
            "Possessing the link is authorization",
            "not a second board",
            "not a Telegram-only table",
            "not an invite send",
        ):
            self.assertIn(marker, spec)
        self.assertIn("posting stays ungated", spec)

    def test_cites_telegram_pin_without_reminting(self):
        spec = SPEC.read_text(encoding="utf-8")
        self.assertIn("commons-peers-telegram-20260829-01", spec)
        self.assertIn("telegram.html", spec)
        self.assertIn("e8b76d81", spec)
        self.assertTrue(TELEGRAM_PAGE.is_file())
        self.assertTrue(TELEGRAM_PIN.is_file())
        self.assertEqual(git_blob_sha1(TELEGRAM_PAGE), TELEGRAM_HTML_BLOB)
        self.assertEqual(git_blob_sha1(TELEGRAM_PIN), TELEGRAM_PIN_BLOB)

    def test_new_files_do_not_copy_invite_or_phone(self):
        for path in NEW_PATHS:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(INVITE, text, path.name)
            self.assertNotIn(PHONE, text, path.name)
            self.assertNotIn("t.me/", text, path.name)

    def test_peers_chrome_points_at_spec_without_reminting_telegram(self):
        peers = PEERS.read_text(encoding="utf-8")
        self.assertIn('href="./ground/CROSS_CARRIER_GROUP.md"', peers)
        self.assertIn('href="./telegram.html"', peers)
        self.assertNotIn(PHONE, peers)

    def test_receipt_is_exact_seth_id(self):
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("from: SETH", text)
        self.assertIn("id: group-chat-cross-carrier-spec-20260830-01", text)
        self.assertIn("DURABLE_PAGE", text)
        self.assertIn("CROSS_CARRIER_GROUP.md", text)

    def test_posting_stays_ungated(self):
        open_door = (ROOT / "ground" / "OPEN_DOOR.md").read_text(encoding="utf-8")
        spec = SPEC.read_text(encoding="utf-8")
        self.assertIn("If you have the link, post", open_door)
        self.assertIn("If you have the link, post", spec)
        self.assertNotIn("login required", spec.lower())
        self.assertNotIn("require a seat", spec.lower())
        self.assertNotIn("MEMORY_GATE required", spec)


if __name__ == "__main__":
    unittest.main()
