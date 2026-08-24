#!/usr/bin/env python3
"""Active instructions name the real boundary instead of regenerating slogans."""
from pathlib import Path
import unittest


ROOT = Path(__file__).parent
ACTIVE = (
    "AGENTS.md",
    ".cursor/rules/commons.mdc",
    ".agents/skills/record-append/SKILL.md",
    ".agents/skills/write-roads/SKILL.md",
    ".github/workflows/commons-board.yml",
    ".github/workflows/harness-ping.yml",
    ".github/workflows/harness-wakeup.yml",
    ".github/workflows/job-watchdog.yml",
    ".github/workflows/llms-txt.yml",
)


class ActiveInstructionDrift(unittest.TestCase):
    def test_cryptic_337_slogan_is_absent_from_active_sources(self):
        for name in ACTIVE:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn("337 NO", text, name)

    def test_each_source_states_the_scoped_non_actuation_boundary(self):
        for name in ACTIVE:
            text = (ROOT / name).read_text(encoding="utf-8").lower()
            self.assertIn("actuat", text, name)
            self.assertIn(".mno", text, name)

    def test_curl_does_not_restore_removed_tos_rejector_claim(self):
        text = (ROOT / "ground/CURL.md").read_text(encoding="utf-8")
        self.assertNotIn("TOS rejects ingest", text)
        self.assertNotIn("tos_gate.reject_reason", text)
        self.assertIn("are not files on current main", text)


if __name__ == "__main__":
    unittest.main()
