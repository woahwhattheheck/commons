#!/usr/bin/env python3
"""Hermetic: manual.html paints tools.json super_mcp (≠ Live-cash)."""

from __future__ import annotations

import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "manual.html"


class CoilManualSuperMcpPaintTest(unittest.TestCase):
    def test_super_mcp_paint(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="super-mcp-hook"', text)
        self.assertIn("data.super_mcp", text)
        self.assertIn("Catalog super MCP", text)
        self.assertIn("sm.url", text)
        self.assertIn("sm.door", text)
        # still paints job hook
        self.assertIn('id="job-hook"', text)
        self.assertIn("data.job", text)


if __name__ == "__main__":
    unittest.main()
