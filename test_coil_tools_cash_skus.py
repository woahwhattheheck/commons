#!/usr/bin/env python3
"""Hermetic: tools.json cash.doors skus unique, kebab-case, tied to href."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"

SKU_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class CoilToolsCashSkusTest(unittest.TestCase):
    def test_skus_unique_and_tied(self) -> None:
        doors = json.loads(TOOLS.read_text(encoding="utf-8"))["cash"]["doors"]
        self.assertGreaterEqual(len(doors), 5)
        skus = [d["sku"] for d in doors]
        self.assertEqual(len(skus), len(set(skus)), "duplicate cash door sku")
        for door in doors:
            sku = door["sku"]
            href = door["href"]
            self.assertTrue(SKU_RE.match(sku), f"bad sku shape: {sku}")
            base = href.lstrip("./").removesuffix(".html")
            if base == "agent-rescue":
                self.assertEqual(sku, "agent-failure-autopsy-29")
            else:
                self.assertEqual(sku, base, f"sku must equal href basename: {sku} vs {href}")


if __name__ == "__main__":
    unittest.main()
