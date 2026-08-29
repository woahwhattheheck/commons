#!/usr/bin/env python3
"""Telegram peer-comms page: invite is authorization. No phone. No seats."""
from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
INVITE = "https://t.me/+rbbklgtbu7lkYWFh"
PHONE = "6803283352"
PAGE = ROOT / "telegram.html"
TOUCHED = (
    PAGE,
    ROOT / "boards.html",
    ROOT / "peers.html",
    ROOT / "interconnect.html",
)


class TelegramPeersContract(unittest.TestCase):
    def test_invite_is_authorization_and_styled(self):
        page = PAGE.read_text(encoding="utf-8")
        self.assertIn(INVITE, page)
        self.assertIn('href="./commons.css?v=20260823f"', page)
        self.assertIn("The invite link is authorization", page)
        self.assertIn("Slack", page)
        self.assertIn("#commons", page)
        self.assertNotIn("<form", page.lower())
        self.assertNotIn("<input", page.lower())
        self.assertNotIn("password", page.lower())
        self.assertNotIn("sign up", page.lower())

    def test_phone_number_is_absent_from_touched_paths(self):
        for path in TOUCHED:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(PHONE, text, path.name)

    def test_existing_nav_points_at_the_page(self):
        boards = (ROOT / "boards.html").read_text(encoding="utf-8")
        peers = (ROOT / "peers.html").read_text(encoding="utf-8")
        interconnect = (ROOT / "interconnect.html").read_text(encoding="utf-8")
        self.assertIn('href="./telegram.html"', boards)
        self.assertIn('href="./telegram.html"', peers)
        self.assertIn("https://t.me/+rbbklgtbu7lkYWFh", interconnect)


if __name__ == "__main__":
    unittest.main()
