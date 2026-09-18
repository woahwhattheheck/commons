#!/usr/bin/env python3
"""Hermetic: tools.json job.id_pattern keeps claim/toolid/date slots."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilJobIdPatternTest(unittest.TestCase):
    def test_id_pattern(self) -> None:
        pat = json.loads(TOOLS.read_text(encoding="utf-8"))["job"].get("id_pattern") or ""
        self.assertTrue(pat)
        self.assertIn("{claim}", pat)
        self.assertIn("tools", pat)
        self.assertIn("{toolid}", pat)
        self.assertIn("YYYYMMDD", pat)
        self.assertTrue(pat.endswith("-01") or "-01" in pat)


if __name__ == "__main__":
    unittest.main()
