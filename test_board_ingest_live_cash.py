#!/usr/bin/env python3
"""Ingest writers compose live-cash after doors() so remints keep product doors."""
from __future__ import annotations

import inspect
import unittest
from pathlib import Path

import board_ingest


def live_cash_section(text: str, name: str) -> str:
    """Return the live-cash door section. Posts on the same page stay speakable."""
    marker = 'id="live-cash"'
    start = text.find(marker)
    if start < 0:
        raise AssertionError("%s missing live-cash door" % name)
    open_tag = text.rfind("<section", 0, start)
    if open_tag < 0:
        open_tag = start
    end = text.find("</section>", start)
    if end < 0:
        raise AssertionError("%s live-cash door unclosed" % name)
    return text[open_tag:end + len("</section>")]


class BoardIngestLiveCashTests(unittest.TestCase):
    def test_helper_has_product_doors(self) -> None:
        root = board_ingest.live_cash_html()
        nested = board_ingest.live_cash_html(True)
        self.assertIn('id="live-cash"', root)
        self.assertIn('href="./agent-rescue.html"', root)
        self.assertIn("$29 Autopsy", root)
        self.assertNotIn("buy.stripe.com", root)
        self.assertIn('href="../agent-rescue.html"', nested)
        self.assertNotIn('href="./agent-rescue.html"', nested)
        src = inspect.getsource(board_ingest.rebuild_names)
        self.assertIn("live_cash_html()", src)
        src = inspect.getsource(board_ingest.rebuild_by)
        self.assertIn("live_cash_html(True)", src)
        src = inspect.getsource(board_ingest.rebuild_board)
        self.assertIn("live_cash_html()", src)
        src = inspect.getsource(board_ingest.rebuild_live)
        self.assertIn("live_cash_html()", src)
        src = inspect.getsource(board_ingest.rebuild_court)
        self.assertIn("live_cash_html()", src)
        src = inspect.getsource(board_ingest.rebuild_to)
        self.assertIn("live_cash_html(True)", src)
        src = inspect.getsource(board_ingest.doors)
        self.assertIn("keep_pad_html(parent)", src)
        keep = board_ingest.keep_pad_html()
        nested_keep = board_ingest.keep_pad_html(True)
        self.assertIn("https://webmcp-pad.vercel.app/", keep)
        self.assertIn("1.4.5", keep)
        self.assertIn('href="./titanmcp.html"', keep)
        self.assertIn('href="../titanmcp.html"', nested_keep)

    def test_committed_surfaces_keep_live_cash(self) -> None:
        root = Path(board_ingest.ROOT)
        cases = [
            (root / "by/LATCH.html", "../"),
            (root / "by/PAD.html", "../"),
            (root / "names.html", "./"),
            (root / "live.html", "./"),
            (root / "board.html", "./"),
            (root / "court.html", "./"),
            (root / "to/index.html", "../"),
            (root / "memory/index.html", "../"),
        ]
        for path, prefix in cases:
            text = path.read_text(encoding="utf-8")
            self.assertIn('id="live-cash"', text, path.name)
            section = live_cash_section(text, path.name)
            self.assertIn(prefix + "agent-rescue.html", section, path.name)
            self.assertIn("$29 Autopsy", section, path.name)
            self.assertNotIn("buy.stripe.com", section)

    def test_live_cash_door_ignores_speakable_stripe_posts(self) -> None:
        helper = board_ingest.live_cash_html()
        page = (
            helper
            + '<article data-id="example-census"><pre>'
            + "Existing rails only: https://buy.stripe.com/example-not-a-door"
            + "</pre></article>"
        )
        section = live_cash_section(page, "synthetic-board")
        self.assertNotIn("buy.stripe.com", section)
        self.assertIn("buy.stripe.com", page)


if __name__ == "__main__":
    unittest.main()
