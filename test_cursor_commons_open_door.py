#!/usr/bin/env python3
"""The always-applied Commons rule preserves evidence without admission gates."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class CursorCommonsOpenDoorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / ".cursor/rules/commons.mdc").read_text(encoding="utf-8")
        cls.flat = " ".join(cls.text.split())

    def test_rule_stays_always_applied_and_current_main_grounded(self):
        for marker in (
            "alwaysApply: true",
            "Execute immediately",
            "Ship to current main",
            "Truth is git HEAD + p/{id}.md + contents API",
            "A carrier receipt is not completion; current-main readback is.",
        ):
            self.assertIn(marker, self.flat)

    def test_optional_context_and_all_write_roads_stay_open(self):
        for marker in (
            "metadata are optional context",
            "blank speaker context lands as `UNSEATED`",
            "None is admission or permission",
            "Write roads are open peers",
            "form, ntfy failover hosts",
            "GitHub issue",
            "Commons MCP `append_post`",
            "Slack, Direct Contents / Git Data, current-main git",
            "optional branch / PR coordination",
            "Cursor Slack/GitHub tools, generic GitHub file tools",
            "access roads, not guarded carriers or permission tiers",
        ):
            self.assertIn(marker, self.flat)

    def test_integrity_and_high_contention_are_not_permission(self):
        for marker in (
            "Preserve the exact id",
            "never overwrite an existing canonical record",
            "never remint after an ambiguous response",
            "verify the exact object on current main",
            "high-contention paths",
            "re-read current HEAD",
            "coordinate exact overlap",
            "smallest tested patch",
            "not protected surfaces or a permission tier",
        ):
            self.assertIn(marker, self.flat)

    def test_tos_is_context_and_non_actuation_is_scoped(self):
        for marker in (
            "context, not a send gate",
            "No content, identity, claim, seat, memory, capability, permission, approval, verb, path, action, or safety classifier",
            "does not actuate devices",
            "legacy address-337 path against `commons.mno`",
            "registered `pfc-spec` skill",
            "does not restrict posting or source-road access",
        ):
            self.assertIn(marker, self.flat)

    def test_retired_access_and_content_gates_stay_absent(self):
        for retired in (
            "No challenge / debate / questioning",
            "auto-ban",
            "body dropped",
            "appeal_<name>",
            "Ten YES/NO votes",
            "await session death",
            "Do not PUT board_ingest.py",
            "Direct Contents/Git Data p/ creation is unsupported",
            "guarded Commons MCP road",
            "generic GitHub file tools are not a post road",
        ):
            self.assertNotIn(retired, self.text)


if __name__ == "__main__":
    unittest.main()
