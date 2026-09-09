#!/usr/bin/env python3
"""Hermetic: manual.html keeps #super-mcp-hook for catalog paint."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "manual.html"


class CoilManualHtmlSuperMcpHookTest(unittest.TestCase):
    def test_hook(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn('id="super-mcp-hook"', text)
        self.assertTrue("super_mcp" in text or "data.super_mcp" in text)


if __name__ == "__main__":
    unittest.main()
