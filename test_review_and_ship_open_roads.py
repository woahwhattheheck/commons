#!/usr/bin/env python3
"""Review-and-ship ends at verified current main without closing roads."""
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class ReviewAndShipOpenRoadsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / ".agents/skills/review-and-ship/SKILL.md").read_text(encoding="utf-8")
        cls.registry = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))
        cls.manual = (ROOT / "skills/MANUAL.md").read_text(encoding="utf-8")

    def test_unique_registry_and_manual_route_keep_blank_token(self):
        matches = [item for item in self.registry["skills"] if item["id"] == "review-and-ship"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["token"], "")
        self.assertIn("[review-and-ship](../.agents/skills/review-and-ship/SKILL.md)", self.manual)

    def test_candidate_is_not_integrated_completion(self):
        for marker in (
            "Treat a pushed, green, approved, or open PR as `CANDIDATE`",
            "do not stop at PR creation or update",
            "INTEGRATED — VERIFIED ON CURRENT MAIN",
            "`NOT_LANDED`",
            "DURABLE_ON_MAIN — p/{id}.md VERIFIED",
            "genuine blocker",
        ):
            self.assertIn(marker, self.skill)

    def test_moving_main_rebuilds_and_never_forces(self):
        for marker in (
            "Immediately before the non-force write",
            "resolve official `main` again",
            "re-read every target on the new head",
            "coordinate exact overlap",
            "smallest compatible patch",
            "rerun tests",
            "rebuild the candidate or commit",
            "Never force or move a stale ref",
        ):
            self.assertIn(marker, self.skill)

    def test_sparse_success_reads_back_before_retry(self):
        for marker in (
            "resolve official current `main` again",
            "read back every changed path or blob",
            "ambiguous or sparse success response",
            "inspect `main` and the files before retrying",
            "stop if the intended bytes already landed",
            "verify concurrent commits remain reachable",
            "verify no unrelated path disappeared",
        ):
            self.assertIn(marker, self.skill)

    def test_all_source_and_receipt_roads_are_peers(self):
        for marker in (
            "Direct Contents / Git Data",
            "current-main git",
            "branch / PR",
            "Action Pad is the preferred unrestricted direct read/write/execute road",
            "Form/ntfy",
            "GitHub issue",
            "Slack",
            "Commons MCP",
            "None is a permission tier",
        ):
            self.assertIn(marker, self.skill)

    def test_high_contention_coordinates_instead_of_refusing(self):
        for marker in (
            "`board_ingest.py`",
            "fat `index.html`",
            "`lda/README.md`",
            "high-contention paths",
            "re-read current `main`",
            "smallest tested compatible patch",
            "not protected surfaces",
        ):
            self.assertIn(marker, self.skill)

    def test_append_only_exact_id_integrity(self):
        for marker in (
            "Never overwrite or delete an existing canonical `p/{id}.md`",
            "one stable exact id",
            "verify before retrying",
            "never remint after ambiguity",
            "Run rather than bypass relevant hooks and tests",
        ):
            self.assertIn(marker, self.skill)

    def test_every_integration_publishes_and_verifies_receipts(self):
        for marker in (
            "After every integration",
            "one append-only completion receipt on the board",
            "one short Slack receipt",
            "exact `p/{id}.md` on official current `main`",
            "a carrier response alone is not durable completion",
            "exact board completion-receipt id",
            "current-HEAD `p/{id}.md` readback",
            "short Slack receipt link/timestamp",
        ):
            self.assertIn(marker, self.skill)

    def test_output_evidence_and_stale_phrases(self):
        for marker in (
            "base main SHA",
            "candidate/PR URL and candidate SHA",
            "exact changed and overlap paths",
            "completion state",
            "integrated main SHA or `NOT_LANDED`",
            "remote path/blob readback",
            "concurrent-commit reachability and unrelated-path preservation evidence",
        ):
            self.assertIn(marker, self.skill)
        for retired in (
            "with Commons refuses",
            "No ingest / fat index",
            "No edits to existing `p/*.md`",
            "Findings (critical / warning / note) · tests · PR URL.",
        ):
            self.assertNotIn(retired, self.skill)


if __name__ == "__main__":
    unittest.main()
