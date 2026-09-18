#!/usr/bin/env python3
"""Hermetic: ground/MANUAL.md No-JS job hook."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "ground" / "MANUAL.md"


class CoilGroundManualNoJsJobHookTest(unittest.TestCase):
    def test_no_js_job_hook(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("No-JS job hook", text)


if __name__ == "__main__":
    unittest.main()
