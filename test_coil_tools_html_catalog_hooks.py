#!/usr/bin/env python3
"""Hermetic: tools.html cites tools.json job + super_mcp (≠ Live-cash)."""

from __future__ import annotations

import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "tools.html"


class CoilToolsHtmlCatalogHooksTest(unittest.TestCase):
    def test_catalog_hooks(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="job-hook"', text)
        self.assertIn('id="super-mcp-hook"', text)
        self.assertIn("./tools.json", text)
        self.assertIn("python host/muhl_tools_once.py --go", text)
        self.assertIn("commons-spark-mcp.vercel.app/mcp", text)
        self.assertIn("./wire.html", text)
        self.assertIn("coil-tools-json-job-hook-20260905-01", text)


if __name__ == "__main__":
    unittest.main()
