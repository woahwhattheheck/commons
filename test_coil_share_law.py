#!/usr/bin/env python3
"""Hermetic: share.json law stays nonempty with PC-button cite."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHARE = ROOT / "share.json"


class CoilShareLawTest(unittest.TestCase):
    def test_share_law(self) -> None:
        data = json.loads(SHARE.read_text(encoding="utf-8"))
        law = data.get("law") or ""
        self.assertGreaterEqual(len(law), 40)
        low = law.lower()
        self.assertTrue(
            "button" in low or "muhl" in low or "tools" in low or "pc" in low,
            "share.law should cite tools/PC button trail",
        )
        self.assertEqual(data.get("button"), "python host/muhl_tools_once.py --go")


if __name__ == "__main__":
    unittest.main()
