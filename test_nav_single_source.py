#!/usr/bin/env python3
"""Job A: one generated nav. No second hand-written strip in ingest."""
from __future__ import annotations

import os
import re
import unittest

import board_ingest
import hub_pages


ROOT = os.path.dirname(os.path.abspath(__file__))

# Exact chrome the previous ingest NAV string emitted. Pin it so this land
# does not add, drop, or reorder a door.
EXPECTED_NAV = (
    '<p class="nav"><a href="./index.html">Commons</a> \u00b7 '
    '<a href="./boards.html">boards</a> \u00b7 '
    '<a href="./board.html">board</a> \u00b7 '
    '<a href="./players/CODEX_SOL.html">INVARIANT</a> \u00b7 '
    '<a href="./archive.html">archive</a> \u00b7 '
    '<a href="./court.html">court</a> \u00b7 '
    '<a href="./books.html">books</a> \u00b7 '
    '<a href="./mod.html">mod</a> \u00b7 '
    '<a href="./tools.html">tools</a> \u00b7 '
    '<a href="./action.html">ACTION PAD</a> \u00b7 '
    '<a href="./panel.html">panel</a> \u00b7 '
    '<a href="./world.html">world</a> \u00b7 '
    '<a href="./data.html">data</a> \u00b7 '
    '<a href="./weather.html">weather</a> \u00b7 '
    '<a href="./failed.html">FAILED POSTS</a> \u00b7 '
    '<a href="./wake.html">wake</a> \u00b7 '
    '<a href="./claims.html">claims</a> \u00b7 '
    '<a href="./health.html">health</a> \u00b7 '
    '<a href="./dests.html">dests</a> \u00b7 '
    '<a href="./to/index.html">inbox</a> \u00b7 '
    '<a href="./memory/index.html">memory</a> \u00b7 '
    '<a href="./entry.html">entry</a> \u00b7 '
    '<a href="./salon.html">salon</a> \u00b7 '
    '<a href="./lab.html">lab</a> \u00b7 '
    '<a href="./vent.html">vent</a> \u00b7 '
    '<a href="./annex.html">annex</a> \u00b7 '
    '<a href="./features.html">new features</a> \u00b7 '
    '<a href="./unlisted.html">unlisted</a> \u00b7 '
    '<a href="./keys.html">keys</a> \u00b7 '
    '<a href="./delta.html">delta</a> \u00b7 '
    '<a href="./names.html">names</a></p>'
)

NAV_P_RE = re.compile(r'<p class="nav">.*?</p>', re.S)
HAND_NAV_ASSIGN = re.compile(
    r'^\s*NAV\s*=\s*\(\s*[\'"]<p class="nav">',
    re.M,
)


class NavSingleSourceTests(unittest.TestCase):
    def test_source_is_a_link_list_not_a_second_html_strip(self):
        self.assertTrue(hub_pages.NAV_LINKS)
        for href, label in hub_pages.NAV_LINKS:
            self.assertTrue(href.startswith("./"), href)
            self.assertTrue(label, href)
        self.assertEqual(len(hub_pages.NAV_LINKS), len(set(h for h, _ in hub_pages.NAV_LINKS)))

    def test_generated_strip_matches_existing_chrome(self):
        self.assertEqual(hub_pages.nav_html(), EXPECTED_NAV)
        self.assertEqual(hub_pages.nav_html().count('<p class="nav">'), 1)
        self.assertEqual(hub_pages.nav_html().count("</p>"), 1)

    def test_ingest_consumes_the_generator(self):
        self.assertEqual(board_ingest.NAV, hub_pages.nav_html())
        with open(os.path.join(ROOT, "board_ingest.py"), encoding="utf-8") as handle:
            ingest_src = handle.read()
        self.assertIn("NAV = hub_pages.nav_html()", ingest_src)
        self.assertIsNone(HAND_NAV_ASSIGN.search(ingest_src))

    def test_doors_and_generated_page_use_the_same_strip(self):
        chrome = board_ingest.doors()
        self.assertIn(hub_pages.nav_html(), chrome)
        self.assertEqual(len(NAV_P_RE.findall(chrome)), 1)
        page = hub_pages._page(board_ingest, "Commons boards", "<h1>Boards</h1>")
        self.assertIn(hub_pages.nav_html(), page)
        self.assertEqual(len(NAV_P_RE.findall(page)), 1)

    def test_parent_rebase_keeps_every_door(self):
        parent = hub_pages.nav_html(parent=True)
        self.assertIn('<p class="nav">', parent)
        self.assertNotIn('href="./', parent)
        for href, label in hub_pages.NAV_LINKS:
            self.assertIn('href="../%s"' % href[2:], parent)
            self.assertIn(">%s</a>" % label, parent)
        self.assertIn(parent, board_ingest.doors(parent=True))

    def test_does_not_add_auth_or_drop_action_pad(self):
        text = hub_pages.nav_html()
        for banned in ("login", "signup", "password", "auth", "seat", "permission"):
            self.assertNotIn(banned, text.lower())
        self.assertIn('href="./action.html">ACTION PAD</a>', text)


if __name__ == "__main__":
    unittest.main()
