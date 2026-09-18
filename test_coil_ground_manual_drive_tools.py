#!/usr/bin/env python3
"""Hermetic: ground/MANUAL.md keeps Drive Bryce's tools cue."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANUAL = ROOT / "ground" / "MANUAL.md"


class CoilGroundManualDriveToolsTest(unittest.TestCase):
    def test_drive(self) -> None:
        text = MANUAL.read_text(encoding="utf-8")
        self.assertIn("Drive Bryce's tools from the board", text)


if __name__ == "__main__":
    unittest.main()
