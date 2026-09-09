#!/usr/bin/env python3
"""Hermetic: capabilities.html has catalog cash hook."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "capabilities.html"


class CoilCapabilitiesCashHookTest(unittest.TestCase):
    def test_cash_hook(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="cash-hook"', text)
        hook = re.search(
            r'<p[^>]*id="cash-hook"[^>]*>.*?</p>',
            text,
            re.S | re.I,
        )
        self.assertIsNotNone(hook, "cash-hook paragraph missing")
        body = hook.group(0)
        self.assertIn("./tools.json", body)
        self.assertIn("./tools-cash.html", body)
        self.assertIn("coil-tools-json-live-cash-20260905-01", body)


if __name__ == "__main__":
    unittest.main()
