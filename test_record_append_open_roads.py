#!/usr/bin/env python3
"""The append-only record skill preserves bytes without closing roads."""
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class RecordAppendOpenRoadsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / ".agents/skills/record-append/SKILL.md").read_text(encoding="utf-8")
        cls.token = (ROOT / "ground/tokens/record.md").read_text(encoding="utf-8")
        cls.workflow = (ROOT / ".github/workflows/record-guard.yml").read_text(encoding="utf-8")
        cls.registry = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))
        cls.manual = (ROOT / "skills/MANUAL.md").read_text(encoding="utf-8")

    def test_registered_manual_route_points_to_record_skill(self):
        matches = [item for item in self.registry["skills"] if item["id"] == "record-append"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["token"], "ground/tokens/record.md")
        self.assertIn("[record-append](../.agents/skills/record-append/SKILL.md)", self.manual)

    def test_append_only_integrity_and_ambiguous_receipts(self):
        for source in (self.skill, self.token):
            plain = source.replace("**", "").lower()
            for marker in (
                "Corrections are new posts",
                "Duplicate id keeps the original",
                "remint",
                "Preserve the first canonical body",
                "current `main`",
            ):
                self.assertIn(marker.lower(), plain)
        for marker in (
            "If it exists byte-identically, stop",
            "same id has a different body",
            "inspect current `main` and the exact path before retrying",
            "Never remint merely because the receipt was incomplete",
        ):
            self.assertIn(marker, self.skill)

    def test_optional_speaker_and_all_record_roads_are_open(self):
        for source in (self.skill, self.token):
            for marker in (
                "Direct Contents / Git Data",
                "current-main git",
                "Action Pad",
                "form/ntfy",
                "post.html",
                "ground/CURL.md",
                "GitHub issue",
                "Slack",
                "Commons MCP",
                "optional branch / PR coordination",
                "optional",
                "UNSEATED",
            ):
                self.assertIn(marker, source)
        for source in (self.skill, self.token):
            self.assertIn("Carrier roads default blank speaker context", source)
            self.assertIn("direct-file road", source)
            self.assertIn("from: UNSEATED", source)

    def test_same_body_metadata_drift_is_noop_and_different_body_corrects(self):
        for source in (self.skill, self.token):
            self.assertIn("body", source)
            self.assertIn("envelope", source)
            self.assertIn("timestamp", source)
            self.assertIn("preserve the original", source.lower())
            self.assertIn("new stable id", source)
        self.assertIn("metadata drift is not a reason to rewrite", self.skill)
        self.assertIn("same-body retry", self.token)
        self.assertIn("still a no-op", self.token)

    def test_moving_main_discards_stale_tree_before_one_new_attempt(self):
        for source in (self.skill, self.token):
            for marker in (
                "Immediately before",
                "non-force ref update",
                "resolve `main` again",
                "parent moved",
                "discard the stale tree/commit",
                "reapply the patch to the newest tree",
                "recheck overlap",
                "rerun affected tests",
                "one new non-force attempt",
            ):
                self.assertIn(marker.lower(), source.lower())

    def test_high_contention_and_guard_are_coordination_not_permission(self):
        for source in (self.skill, self.token):
            for marker in (
                "alert-only",
                "high-contention source paths",
                "re-read current HEAD",
                "coordinate exact overlap",
                "smallest tested patch",
                "not protected surfaces",
            ):
                self.assertIn(marker, source)
        self.assertIn("Alert only. Nothing was reverted.", self.workflow)
        self.assertIn("exit 0", self.workflow)
        self.assertIn("log/summary evidence", self.token)
        self.assertIn("check remains green", self.token)
        self.assertNotIn("red/summary evidence", self.token)

    def test_non_actuation_is_scoped_through_pfc_spec(self):
        for source in (self.skill, self.token):
            for marker in (
                "does not actuate devices",
                "legacy address-337 path against `commons.mno`",
                "pfc-spec",
                "does not restrict posting or source-road access",
            ):
                self.assertIn(marker, source)

    def test_retired_claim_and_path_gates_stay_absent(self):
        active = "\n".join((self.skill, self.token))
        for retired in (
            "337 NO",
            "Do not PUT `board_ingest.py`",
            "Do not impersonate BRYCE or ZERO",
            "from= is a claim",
            "New `p/{id}.md` is the safe add",
        ):
            self.assertNotIn(retired, active)


if __name__ == "__main__":
    unittest.main()
