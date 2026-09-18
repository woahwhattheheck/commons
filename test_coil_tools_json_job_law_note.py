#!/usr/bin/env python3
"""Hermetic: tools.json job law/note contract."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / "tools.json"


class CoilToolsJsonJobLawNoteTest(unittest.TestCase):
    def test_job_law_and_note(self) -> None:
        job = json.loads(TOOLS.read_text(encoding="utf-8"))["job"]
        self.assertEqual(
            job["law"],
            "One job per PC button press. Oldest open job first. Prefer a claim not already waiting on another open job. Not a hard ceiling.",
        )
        self.assertEqual(
            job["note"],
            "Machine-readable job hook for the tools catalog. Cite share/button — do not remint muhl_tools_once.",
        )


if __name__ == "__main__":
    unittest.main()
