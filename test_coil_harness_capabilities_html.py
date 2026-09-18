#!/usr/bin/env python3
"""Hermetic: capabilities with html lists keep nonempty .html paths."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [ROOT / "harnesses" / "catalog.json", ROOT / "catalog.json"]


class CoilHarnessCapabilitiesHtmlTest(unittest.TestCase):
    def test_html(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        caps = json.loads(path.read_text(encoding="utf-8"))["capabilities"]
        saw = 0
        for c in caps:
            html = c.get("html")
            if html is None:
                continue
            self.assertIsInstance(html, list)
            self.assertGreater(len(html), 0, f"empty html id={c.get('id')}")
            for h in html:
                self.assertIsInstance(h, str)
                self.assertTrue(h.endswith(".html") or h.endswith(".md"), h)
            saw += 1
        self.assertGreaterEqual(saw, 3)


if __name__ == "__main__":
    unittest.main()
