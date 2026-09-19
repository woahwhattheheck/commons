"""Synthetic boundary regressions for Commons #16289; no provider I/O.

ZZ-COPPER / GPT-6 Astra Pro. The production completion_projection module is
imported unchanged. These tests do not execute board_ingest or its renderer.
"""
import json
import tempfile
import unittest
from pathlib import Path

import completion_projection as cp

OP = "COPPER-COMPLETED-OPERATION-20260919"
OTHER = "COPPER-STILL-OPEN-OPERATION-20260919"
MERGE = "c" * 40


class CompletionProvenanceReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "p").mkdir()
        for operation in (OP, OTHER):
            (self.root / cp.source_rel(operation)).write_text(
                f"---\nfrom: UNSEATED\nto: TABLE\nid: {operation}\n---\nSynthetic work.\n",
                encoding="utf-8",
            )
        self.issue = {
            "number": 15130, "title": OP, "body": f"Operation: {OP}",
            "state": "closed", "state_reason": "completed",
            "closed_at": "2026-09-18T12:00:01Z",
            "html_url": "https://github.com/woahwhattheheck/commons/issues/15130",
        }
        self.pr = {
            "number": 15138, "merged": True,
            "merged_at": "2026-09-18T12:00:00Z", "merge_commit_sha": MERGE,
            "base": {"ref": "main"}, "body": "Closes #15130.",
            "html_url": "https://github.com/woahwhattheheck/commons/pull/15138",
        }

    @staticmethod
    def ancestor(sha):
        return sha == MERGE

    def test_control_valid_marker_roundtrip(self):
        marker = cp.build_marker(self.root, OP, self.issue, self.pr)
        self.assertEqual("wrote", cp.write_marker(self.root, marker, self.ancestor))
        self.assertEqual(frozenset({OP}), cp.completed_operation_ids(self.root, self.ancestor))

    def test_builder_rejects_another_operation_from_same_issue_proof(self):
        self.assertEqual(OP, cp.stable_operation_id_from_issue(self.issue))
        with self.assertRaises(cp.CompletionEvidenceError):
            cp.build_marker(self.root, OTHER, self.issue, self.pr)

    def test_builder_rejects_conflicting_operation_identity(self):
        self.issue["body"] = f"Operation: {OTHER}"
        self.assertEqual("", cp.stable_operation_id_from_issue(self.issue))
        with self.assertRaises(cp.CompletionEvidenceError):
            cp.build_marker(self.root, OP, self.issue, self.pr)

    def test_builder_rejects_missing_operation_identity(self):
        self.issue.pop("title")
        self.issue.pop("body")
        with self.assertRaises(cp.CompletionEvidenceError):
            cp.build_marker(self.root, OP, self.issue, self.pr)

    def test_builder_rejects_non_timestamp_strings(self):
        self.issue["closed_at"] = "not-a-date"
        self.pr["merged_at"] = "not-a-date"
        with self.assertRaises(cp.CompletionEvidenceError):
            cp.build_marker(self.root, OP, self.issue, self.pr)

    def test_reader_rejects_non_timestamp_strings(self):
        marker = cp.build_marker(self.root, OP, self.issue, self.pr)
        marker["issue"]["closed_at"] = "not-a-date"
        marker["merge"]["merged_at"] = "not-a-date"
        self.assertFalse(cp.marker_is_valid(self.root, marker, self.ancestor))

    def test_reader_does_not_project_malformed_time_marker_as_complete(self):
        marker = cp.build_marker(self.root, OP, self.issue, self.pr)
        marker["issue"]["closed_at"] = "not-a-date"
        marker["merge"]["merged_at"] = "not-a-date"
        path = self.root / cp.marker_rel(OP)
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(marker), encoding="utf-8")
        self.assertEqual(frozenset(), cp.completed_operation_ids(self.root, self.ancestor))

    def test_reader_rejects_impossible_calendar_date(self):
        marker = cp.build_marker(self.root, OP, self.issue, self.pr)
        marker["issue"]["closed_at"] = "2026-02-30T12:00:01Z"
        marker["merge"]["merged_at"] = "2026-02-30T12:00:00Z"
        self.assertFalse(cp.marker_is_valid(self.root, marker, self.ancestor))

    def test_reader_rejects_non_string_timestamp_values(self):
        marker = cp.build_marker(self.root, OP, self.issue, self.pr)
        marker["issue"]["closed_at"] = True
        marker["merge"]["merged_at"] = True
        self.assertFalse(cp.marker_is_valid(self.root, marker, self.ancestor))

    def test_reader_rejects_merge_after_close_with_different_utc_offsets(self):
        marker = cp.build_marker(self.root, OP, self.issue, self.pr)
        # Close is 12:00 UTC; merge is 12:30 UTC, despite lexicographic order.
        marker["issue"]["closed_at"] = "2026-09-18T13:00:00+01:00"
        marker["merge"]["merged_at"] = "2026-09-18T12:30:00Z"
        self.assertFalse(cp.marker_is_valid(self.root, marker, self.ancestor))

    def test_control_reopen_restores_eligibility(self):
        marker = cp.build_marker(self.root, OP, self.issue, self.pr)
        cp.write_marker(self.root, marker, self.ancestor)
        self.assertEqual((OP,), cp.remove_markers_for_issue(self.root, self.issue["number"]))
        self.assertEqual(frozenset(), cp.completed_operation_ids(self.root, self.ancestor))


if __name__ == "__main__":
    unittest.main()
