#!/usr/bin/env python3
"""Hermetic: muhl-hook SKILL.md keeps File a TOOLS job section."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = [
    ROOT / ".agents" / "skills" / "muhl-hook" / "SKILL.md",
    ROOT / "SKILL.md",
]


class CoilMuhlHookSkillToolsJobTest(unittest.TestCase):
    def test_section(self) -> None:
        path = next((p for p in CANDIDATES if p.is_file()), None)
        self.assertIsNotNone(path)
        text = path.read_text(encoding="utf-8")
        self.assertIn("## File a TOOLS job", text)
        self.assertIn("job.html", text)
        self.assertIn("muhl_tools_once.py --go", text)
        self.assertIn("tools.json", text)


if __name__ == "__main__":
    unittest.main()
