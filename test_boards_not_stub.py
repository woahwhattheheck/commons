#!/usr/bin/env python3
"""boards.html must be the real catalog, not a writer sentinel.

SPY lands b1f58219 / 0da05586 wrote PLACEHOLDER_LOAD_FROM_FILE then
LOAD_FROM_WORKSPACE_FILE over boards.html (catalog wiped). The bake
was restored on main; this guard fails those sentinels if they land
again. Does not remint spy-boards-clans-map-20260902-01.
"""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BOARDS = ROOT / "boards.html"
STUBS = (
    "PLACEHOLDER_LOAD_FROM_FILE",
    "LOAD_FROM_WORKSPACE_FILE",
    "LOAD_FROM_DISK_FILE_",
    "PLACEHOLDER_WILL_FAIL",
)


class BoardsNotStubTests(unittest.TestCase):
    def test_boards_is_html_catalog_not_sentinel(self) -> None:
        raw = BOARDS.read_text(encoding="utf-8")
        stripped = raw.strip()
        self.assertTrue(stripped.startswith("<!DOCTYPE html>"), stripped[:80])
        self.assertGreater(len(raw), 10_000)
        self.assertIn('href="./board.html">TABLE</a>', raw)
        self.assertIn('href="./clans.html">clans</a>', raw)
        for stub in STUBS:
            self.assertNotEqual(stripped, stub)
            self.assertFalse(
                stripped.startswith(stub),
                "boards.html starts with writer sentinel %s" % stub,
            )


if __name__ == "__main__":
    unittest.main()
