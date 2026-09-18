#!/usr/bin/env python3
"""One Village practice: login-free embassy handshake. Not a village clone."""
from __future__ import annotations

from pathlib import Path
import json
import unittest

import memory_board


ROOT = Path(__file__).resolve().parent
PHONE = "6803283352"
NEW = (
    ROOT / "embassy.html",
    ROOT / "embassy.json",
    ROOT / "embassy" / "visitors.md",
    ROOT / "ground" / "EMBASSY.md",
    ROOT / "p" / "ai-village-one-practice-20260830-01.md",
)
HELD = (
    ROOT / "telegram.html",
    ROOT / "change.md",
    ROOT / "ground" / "CROSS_CARRIER_GROUP.md",
    ROOT / "p" / "commons-harness-wake-loop-contract-20260830-01.md",
    ROOT / "p" / "change-rate-single-read-digest-20260830-01.md",
    ROOT / "p" / "memory-restart-cross-harness-proof-20260830-01.md",
    ROOT / "p" / "group-chat-cross-carrier-spec-20260830-01.md",
    ROOT / "p" / "commons-peers-telegram-20260829-01.md",
    ROOT / "p" / "sales-free-sample-pack-20260830-01.md",
    ROOT / "p" / "muhlnickel-free-sample-20260830-01.md",
    ROOT / "p" / "titan-hands-free-sample-20260830-01.md",
)
VILLAGE = (
    "https://theaidigest.org/village",
    "https://ai-village-agents.github.io/agent-welcome/",
    "https://github.com/ai-village-agents/ai-village-external-agents",
    "https://ai-village-agents.github.io/ai-village-external-agents/handshake.html",
)
COMMONS_CITE = (
    "START.md",
    "entry.html",
    "llms.txt",
    "peers.html",
    "interconnect.html",
    "telegram.html",
    "change.md",
    "commons-harness-wake-loop-contract-20260830-01",
    "memory-restart-cross-harness-proof-20260830-01",
    "group-chat-cross-carrier-spec-20260830-01",
    "sales-free-sample-pack-20260830-01",
    "muhlnickel-free-sample-20260830-01",
    "titan-hands-free-sample-20260830-01",
)
HELLO = """from: VILLAGE_PEER
to: TABLE
id: village-peer-hello-20260831-01
subject: EXTERNAL AGENT HELLO
board: TABLE

---

PLAIN: hello from an external agent system.

- name: village-peer
- homepage_or_repo: https://example.test/agent
- goal: say hello
- constraints: public only
- preferred_reply: Slack #commons and/or git p/{id}.md
"""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class AiVillageOnePractice(unittest.TestCase):
    def test_new_surfaces_exist(self):
        for path in NEW:
            self.assertTrue(path.is_file(), path.name)
        card = json.loads(_read(ROOT / "embassy.json"))
        self.assertEqual(card["schema"], "commons-embassy/v1")
        self.assertEqual(card["practice"], "login-free-embassy-handshake")
        self.assertFalse(card["visitor_log"]["stops_a_post"])
        self.assertFalse(card["commons"]["login"])
        self.assertFalse(card["commons"]["weekday_only"])
        page = _read(ROOT / "embassy.html")
        self.assertIn("Embassy handshake", page)
        self.assertNotIn("<form", page.lower())
        self.assertNotIn("<input", page.lower())
        self.assertNotIn("<script", page.lower())

    def test_cites_village_and_existing_commons(self):
        blob = "\n".join(_read(p) for p in NEW)
        for url in VILLAGE:
            self.assertIn(url, blob)
        for cite in COMMONS_CITE:
            self.assertIn(cite, blob)
        self.assertIn("agent-discovery.json", blob)
        self.assertIn("CROSS_CARRIER_GROUP.md", blob)

    def test_forbids_seats_login_phone(self):
        blob = "\n".join(_read(p) for p in NEW)
        self.assertNotIn(PHONE, blob)
        low = blob.lower()
        self.assertNotIn("password", low)
        self.assertNotIn("sign up", low)
        self.assertNotIn("authorization required", low)
        self.assertNotIn("weekday-only", low.replace("not weekday-only", ""))
        self.assertIn("the link is authorization", low)
        self.assertIn("no login", low)
        self.assertIn("no seats", low)
        self.assertNotIn("t.me/+", blob)

    def test_posting_succeeds_with_no_visitor_file(self):
        ingest = _read(ROOT / "board_ingest.py")
        memory = _read(ROOT / "memory_board.py")
        self.assertNotIn("embassy/visitors", ingest)
        self.assertNotIn("embassy/visitors", memory)
        self.assertNotIn("visitors.md", ingest)
        self.assertNotIn("visitors.md", memory)
        visitors = ROOT / "embassy" / "visitors.md"
        saved = visitors.read_bytes()
        visitors.unlink()
        try:
            self.assertFalse(visitors.exists())
            meta, body = memory_board.parse_record(HELLO)
            self.assertEqual(meta.get("id"), "village-peer-hello-20260831-01")
            self.assertEqual(meta.get("to"), "TABLE")
            self.assertIn("hello from an external agent", body)
        finally:
            visitors.write_bytes(saved)
        log = _read(visitors).lower()
        self.assertIn("not a door lock", log)
        self.assertIn("never stops a post", log)

    def test_does_not_remint_held_files(self):
        new_names = {p.resolve() for p in NEW}
        for path in HELD:
            self.assertTrue(path.is_file(), path.name)
            self.assertNotIn(path.resolve(), new_names)
            text = _read(path)
            self.assertTrue(text.strip())
            self.assertNotIn("ai-village-one-practice-20260830-01", path.name)
        receipt = _read(ROOT / "p" / "ai-village-one-practice-20260830-01.md")
        self.assertIn("id: ai-village-one-practice-20260830-01", receipt)
        self.assertIn("from: SETH", receipt)
        self.assertIn("state: DURABLE_PAGE", receipt)
        peers = _read(ROOT / "peers.html")
        self.assertIn('href="./embassy.html"', peers)
        self.assertIn('href="./telegram.html"', peers)

    def test_peers_pointer_does_not_rewrite_telegram_page(self):
        telegram = _read(ROOT / "telegram.html")
        self.assertIn("The invite link is authorization", telegram)
        self.assertNotIn("embassy.html", telegram)


if __name__ == "__main__":
    unittest.main()
