#!/usr/bin/env python3
"""Hermetic: docs/mcp-carriers.md cites Commons tools board for Grok seats."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [
    ROOT / "docs" / "mcp-carriers.md",
    ROOT / "mcp-carriers.md",
]


class CoilDocsMcpCarriersToolsTest(unittest.TestCase):
    def test_tools_cite(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        text = path.read_text(encoding="utf-8")
        self.assertIn("tools.html", text)
        # invented tools / tools board / job path
        self.assertTrue(
            "tools.json" in text
            or "job.html" in text
            or "Tools board" in text
            or "invented" in text.lower()
        )


if __name__ == "__main__":
    unittest.main()
