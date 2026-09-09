#!/usr/bin/env python3
"""Hermetic: tools.json button == job.button == share.json button."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"
SHARE = ROOT / "share.json"
EXPECTED = "python host/muhl_tools_once.py --go"


class CoilToolsButtonTripleTest(unittest.TestCase):
    def test_triple_buttons(self) -> None:
        tools = json.loads(TOOLS.read_text(encoding="utf-8"))
        share = json.loads(SHARE.read_text(encoding="utf-8"))
        top = tools.get("button")
        job = tools.get("job", {}).get("button")
        sh = share.get("button")
        self.assertEqual(top, EXPECTED)
        self.assertEqual(job, EXPECTED)
        self.assertEqual(sh, EXPECTED)
        self.assertEqual(top, job)
        self.assertEqual(job, sh)


if __name__ == "__main__":
    unittest.main()
