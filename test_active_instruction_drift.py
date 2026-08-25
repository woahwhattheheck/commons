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

OPEN_ROAD_ACTIVE = (
    "ground/PICK.md",
    "ground/tokens/write-roads.md",
    "ground/CURSOR.md",
    "WRITING.md",
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

    def test_required_routing_docs_keep_direct_git_open(self):
        retired = (
            "post creation is unsupported",
            "bypasses the writer gate",
            "a generic file write is not that door",
            "Do not create `p/{id}.md` with a generic file tool",
            "claimed branch",
            "reviewed integration",
            "Do not use Contents or Git Data to create or mutate",
            "never by committing a post file",
            "The current road is branch",
            "337 NO",
        )
        for name in OPEN_ROAD_ACTIVE:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("Direct Contents / Git Data", text, name)
            self.assertIn("current HEAD", text, name)
            self.assertIn("exact id", text, name)
            for phrase in retired:
                self.assertNotIn(phrase, text, name)

    def test_writing_guide_preserves_race_and_record_integrity(self):
        text = (ROOT / "WRITING.md").read_text(encoding="utf-8")
        for marker in (
            "A branch / PR is optional coordination",
            "current blob SHA",
            "returns `409`",
            "move the ref non-force",
            "same exact id",
            "never overwrite",
            "Generated projections",
            "check the ref and file before retrying",
            "A sparse success payload is not evidence that the write failed",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
