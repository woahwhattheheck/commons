#!/usr/bin/env python3
"""Hermetic: tools.json cash.doors hrefs match commerce.html tip shelf."""

from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"
COMMERCE = ROOT / "commerce.html"

PRODUCT_RE = re.compile(
    r"\./(?:agent-rescue|dealer-service-lead-rescue|referral-intake-completeness|repair-booking-preflight|plant-downtime-handoff)\.html\Z"
)


class _TipShelfParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_tip_shelf = False
        self.section_depth = 0
        self.cash_hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == "section":
            if self.in_tip_shelf:
                self.section_depth += 1
            elif attr.get("id") == "tip-shelf":
                self.in_tip_shelf = True
                self.section_depth = 1
        if self.in_tip_shelf and tag == "a":
            href = attr.get("href")
            if href and PRODUCT_RE.fullmatch(href):
                self.cash_hrefs.append(href)

    def handle_endtag(self, tag: str) -> None:
        if self.in_tip_shelf and tag == "section":
            self.section_depth -= 1
            if self.section_depth == 0:
                self.in_tip_shelf = False


def tip_shelf_cash_hrefs(html: str) -> list[str]:
    parser = _TipShelfParser()
    parser.feed(html)
    parser.close()
    return parser.cash_hrefs


class CoilCommerceCashDoorsSyncTest(unittest.TestCase):
    def test_cash_doors_on_commerce_tip_shelf(self) -> None:
        data = json.loads(TOOLS.read_text(encoding="utf-8"))
        cash = data["cash"]
        doors = [d["href"] for d in cash["doors"]]
        self.assertEqual(cash.get("commerce"), "./commerce.html")
        shelf_hrefs = tip_shelf_cash_hrefs(COMMERCE.read_text(encoding="utf-8"))
        self.assertEqual(sorted(doors), sorted(shelf_hrefs))

    def test_off_shelf_cash_link_is_not_evidence(self) -> None:
        html = (
            '<p id="live-cash"><a href="./agent-rescue.html">outside shelf</a></p>'
            '<section id="tip-shelf"><a href="./dealer-service-lead-rescue.html">inside shelf</a></section>'
        )
        self.assertEqual(tip_shelf_cash_hrefs(html), ["./dealer-service-lead-rescue.html"])

    def test_duplicate_shelf_cash_link_is_preserved_for_parity_failure(self) -> None:
        html = (
            '<section id="tip-shelf">'
            '<a href="./agent-rescue.html">one</a>'
            '<a href="./agent-rescue.html">duplicate</a>'
            '</section>'
        )
        self.assertEqual(
            tip_shelf_cash_hrefs(html),
            ["./agent-rescue.html", "./agent-rescue.html"],
        )


if __name__ == "__main__":
    unittest.main()
