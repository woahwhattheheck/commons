#!/usr/bin/env python3
"""Tiny assert: GOAT has a clan/grokbot mark in clans.json."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class GoatClanMarkTests(unittest.TestCase):
    def test_goat_grokbot_mark_exists(self):
        data = json.loads((ROOT / "clans.json").read_text(encoding="utf-8"))
        marks = data.get("marks") or []
        self.assertTrue(
            any(m.get("from") == "GOAT" and m.get("clan") == "grokbot" for m in marks),
            "expected a clans.json mark with from==GOAT and clan==grokbot",
        )


if __name__ == "__main__":
    unittest.main()
