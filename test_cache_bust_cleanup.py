#!/usr/bin/env python3
"""Canary: Date.now()/no-store cache-bust leftover is closed on claimed paths.

Mechanical cause 2 of the buttons-barely cluster only. Does not touch
lane-pages-94mb-lane-scoped-bake or load-older-silent-click-board-js-585.
Live ntfy overlays may keep no-store; site/HEAD fetches must revalidate.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent

CLAIMED = (
    "index.html",
    "head.js",
    "board.js",
    "session.js",
    "carrier.js",
    "boards.html",
    "hub_pages.py",
)

# Unique-URL bust: every visit mints a new query so HTTP cache cannot hit.
NOW_QUERY_BUST = re.compile(
    r"""[?&](?:v|b|ts)=["']\s*\+\s*Date\.now\(\)"""
    r"""|["']\?[vbts]=["']\s*\+\s*Date\.now\(\)"""
)


class CacheBustCleanupCanary(unittest.TestCase):
    def test_claimed_paths_exist(self):
        for rel in CLAIMED:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_no_datetime_query_bust_on_claimed_paths(self):
        for rel in CLAIMED:
            text = (ROOT / rel).read_text(encoding="utf-8")
            hit = NOW_QUERY_BUST.search(text)
            self.assertIsNone(hit, "%s still has Date.now() query bust: %s" % (rel, hit.group(0) if hit else ""))

    def test_index_meta_allows_store_and_revalidate(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        hub = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        match = re.search(r'^ASSET_V\s*=\s*"([A-Za-z0-9]+)"', hub, re.M)
        self.assertIsNotNone(match)
        asset_v = match.group(1)
        self.assertNotIn('content="no-store', html)
        self.assertIn('content="no-cache, must-revalidate"', html)
        self.assertIn("head.js?v=" + asset_v, html)
        self.assertIn("board.js?v=" + asset_v, html)
        self.assertIn("carrier.js?v=" + asset_v, html)
        self.assertRegex(asset_v, r"^202608\d{2}[a-z]$")

    def test_boards_and_generator_revalidate(self):
        for rel in ("boards.html", "hub_pages.py"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn('content="no-store', text)
            self.assertIn("no-cache, must-revalidate", text)
            self.assertIn('cache:"no-cache"', text.replace(" ", ""))
            self.assertNotIn('cache:"no-store"', text.replace(" ", ""))

    def test_head_js_replaces_bust_with_revalidate(self):
        src = (ROOT / "head.js").read_text(encoding="utf-8")
        self.assertIn("function fetchCacheMode", src)
        self.assertIn('return "no-cache"', src)
        self.assertIn('return "no-store"', src)
        self.assertNotIn('v=" + Date.now()', src)
        self.assertIn("bust !== true", src)

    def test_board_js_fetchsite_revalidates_ntfy_stays_live(self):
        src = (ROOT / "board.js").read_text(encoding="utf-8")
        self.assertIn('cache: "no-cache"', src)
        self.assertIn('cache: "no-store"', src)
        self.assertNotIn('?v=" + Date.now()', src)

    def test_session_and_carrier_site_fetches_revalidate(self):
        session = (ROOT / "session.js").read_text(encoding="utf-8")
        self.assertIn('cache: "no-cache"', session)
        self.assertNotIn('cache: "no-store"', session)
        self.assertIn('fetch(BASE + "session.json", { cache: "no-cache"', session)

        carrier = (ROOT / "carrier.js").read_text(encoding="utf-8")
        self.assertNotIn('?v=" + Date.now()', carrier)
        self.assertIn('cache: "no-cache"', carrier)
        self.assertIn('cache: "no-store"', carrier)
        self.assertIn('hosts[i] + "/" + NTFY_TOPIC', carrier)
        self.assertIn('method: "POST"', carrier)
        post_idx = carrier.find('hosts[i] + "/" + NTFY_TOPIC')
        self.assertIn('cache: "no-store"', carrier[post_idx : post_idx + 250])


if __name__ == "__main__":
    unittest.main()
