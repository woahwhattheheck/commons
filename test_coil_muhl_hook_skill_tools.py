#!/usr/bin/env python3
"""Hermetic: muhl-hook SKILL.md File a TOOLS job section."""

from __future__ import annotations

import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent / ".agents" / "skills" / "muhl-hook" / "SKILL.md"


class CoilMuhlHookSkillToolsTest(unittest.TestCase):
    def test_file_tools_job_section(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        section = text.split("## File a TOOLS job", 1)[1].split("## Do this", 1)[0]
        self.assertIn("tools.json", section)
        self.assertIn("job.html", section)
        self.assertIn("manual.html", section)
        self.assertIn("commands.json", section)
        self.assertIn("tools-board", section)
        self.assertIn("muhl_tools_once.py --go", section)
        self.assertIn("Not an Action Pad verb", section)


if __name__ == "__main__":
    unittest.main()
