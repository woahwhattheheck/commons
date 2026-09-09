#!/usr/bin/env python3
"""Hermetic: MANUAL ## Refuse list matches tools.json refuse (drift lock)."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"
MANUAL = ROOT / "ground" / "MANUAL.md"


class CoilToolsRefuseSyncTest(unittest.TestCase):
    def test_refuse_lists_match(self) -> None:
        self.assertTrue(TOOLS.is_file(), "tools.json missing")
        self.assertTrue(MANUAL.is_file(), "ground/MANUAL.md missing")
        refuse = json.loads(TOOLS.read_text(encoding="utf-8")).get("refuse")
        self.assertIsInstance(refuse, list)
        self.assertGreater(len(refuse), 0)
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("## Refuse", text)
        section = text.split("## Refuse", 1)[1].split("##", 1)[0]
        m = re.search(r"Do not file:\s*(.+)", section)
        self.assertIsNotNone(m, "MANUAL Refuse missing 'Do not file:' line")
        manual = [x.strip() for x in m.group(1).split(",") if x.strip()]
        self.assertEqual(manual, refuse, "MANUAL Refuse drifted from tools.json refuse")


if __name__ == "__main__":
    unittest.main()
