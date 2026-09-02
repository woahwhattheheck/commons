#!/usr/bin/env python3
"""Hall-pass skill stays an open road; instruction scan must not false-positive.

Do not remint open_door_guard.py, test_open_door_guard.py, or the hall-pass skill id.
"""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
SKILL = ROOT / ".agents" / "skills" / "google-ai-mode-hall-pass" / "SKILL.md"

KEEP = {
    "open_door_guard.py": "4b053e43",
    "test_open_door_guard.py": "70ee5730",
    ".github/workflows/open-door-guard.yml": "6586644c",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class HallPassOpenDoorInstructionScan(unittest.TestCase):
    def test_keep_guard_unread(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_live_skill_instruction_scan_is_clean(self) -> None:
        body = SKILL.read_text(encoding="utf-8")
        lines = [
            guard.AddedLine(SKILL.as_posix(), n, text)
            for n, text in enumerate(body.splitlines(), 1)
        ]
        self.assertEqual(guard.scan_added(lines), [])
        self.assertIn("www.google.com", body)
        self.assertIn("no login", body)
        self.assertIn("AI Mode", body)
        self.assertIn("UNSEATED", body)
        self.assertIn("Do not add Commons login", body)
        self.assertIn("intended feature, not a hack", body.lower())


if __name__ == "__main__":
    unittest.main()
