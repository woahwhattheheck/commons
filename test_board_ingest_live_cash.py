#!/usr/bin/env python3
"""Ingest writers compose live-cash after doors() so remints keep product doors."""
from __future__ import annotations

import inspect
import unittest
from pathlib import Path

import board_ingest


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

    def test_committed_surfaces_keep_live_cash(self) -> None:
        root = Path(board_ingest.ROOT)
        cases = [
            (root / "by/LATCH.html", "../"),
            (root / "by/PAD.html", "../"),
            (root / "names.html", "./"),
            (root / "live.html", "./"),
            (root / "board.html", "./"),
        ]
        for path, prefix in cases:
            text = path.read_text(encoding="utf-8")
            self.assertIn('id="live-cash"', text, path.name)
            self.assertIn(prefix + "agent-rescue.html", text, path.name)
            self.assertIn("$29 Autopsy", text, path.name)
            self.assertNotIn("buy.stripe.com", text)


if __name__ == "__main__":
    unittest.main()
