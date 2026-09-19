"""Synthetic chronological-order invariants for the completion-marker reader.

The production module is imported unchanged. An independent datetime oracle
checks equivalent instants under four UTC offsets, including date rollover.
No provider requests or board renderer imports occur in these tests.
"""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import completion_projection as cp

OP = "COPPER-TIME-MATRIX-OPERATION-20260919"
MERGE = "c" * 40
OFFSETS = tuple(timezone(timedelta(minutes=m)) for m in (-420, 0, 120, 330))
INSTANTS = tuple(
    datetime(2026, 9, 18, tzinfo=timezone.utc) + timedelta(minutes=m)
    for m in (-30, 0, 30)
)
NAIVE = ("2026-09-18", "2026-09-18T00:00:00", "2026-09-18 00:00:00", "2026-09-18T00:00:00.123456")


class CompletionTimeMatrixTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "p").mkdir()
        (self.root / cp.source_rel(OP)).write_text(
            f"---\nfrom: UNSEATED\nto: TABLE\nid: {OP}\n---\nSynthetic work.\n",
            encoding="utf-8",
        )
        self.issue = {
            "number": 15130, "title": OP, "body": f"Operation: {OP}",
            "state": "closed", "state_reason": "completed",
            "closed_at": "2026-09-18T00:00:01Z",
            "html_url": "https://github.com/woahwhattheheck/commons/issues/15130",
        }
        self.pr = {
            "number": 15138, "merged": True,
            "merged_at": "2026-09-18T00:00:00Z", "merge_commit_sha": MERGE,
            "base": {"ref": "main"}, "body": "Closes #15130.",
            "html_url": "https://github.com/woahwhattheheck/commons/pull/15138",
        }

    @staticmethod
    def ancestor(sha):
        return sha == MERGE

    @staticmethod
    def cases():
        for merge_instant in INSTANTS:
            for close_instant in INSTANTS:
                for merge_offset in OFFSETS:
                    for close_offset in OFFSETS:
                        yield (
                            merge_instant.astimezone(merge_offset).isoformat(),
                            close_instant.astimezone(close_offset).isoformat(),
                            merge_instant <= close_instant,
                        )

    def test_control_preserves_canonical_evidence_strings(self):
        marker = cp.build_marker(self.root, OP, self.issue, self.pr)
        self.assertEqual(self.issue["closed_at"], marker["issue"]["closed_at"])
        self.assertEqual(self.pr["merged_at"], marker["merge"]["merged_at"])
        self.assertTrue(cp.marker_is_valid(self.root, marker, self.ancestor))

    def test_builder_orders_instants_across_offsets_and_date_rollover(self):
        count = 0
        for merged_at, closed_at, expected in self.cases():
            count += 1
            with self.subTest(merged_at=merged_at, closed_at=closed_at):
                issue = dict(self.issue, closed_at=closed_at)
                pr = dict(self.pr, merged_at=merged_at)
                try:
                    cp.build_marker(self.root, OP, issue, pr)
                except cp.CompletionEvidenceError:
                    accepted = False
                else:
                    accepted = True
                self.assertEqual(expected, accepted)
        self.assertEqual(144, count)

    def test_reader_orders_instants_across_offsets_and_date_rollover(self):
        count = 0
        for merged_at, closed_at, expected in self.cases():
            count += 1
            with self.subTest(merged_at=merged_at, closed_at=closed_at):
                marker = cp.build_marker(self.root, OP, self.issue, self.pr)
                marker["issue"]["closed_at"] = closed_at
                marker["merge"]["merged_at"] = merged_at
                self.assertEqual(expected, cp.marker_is_valid(self.root, marker, self.ancestor))
        self.assertEqual(144, count)

    def test_builder_rejects_timezone_naive_evidence(self):
        for value in NAIVE:
            with self.subTest(value=value):
                # Equal lexical values avoid accidentally passing a malformed
                # timestamp case through unrelated ordering rejection.
                issue = dict(self.issue, closed_at=value)
                pr = dict(self.pr, merged_at=value)
                with self.assertRaises(cp.CompletionEvidenceError):
                    cp.build_marker(self.root, OP, issue, pr)

    def test_reader_rejects_timezone_naive_evidence(self):
        for value in NAIVE:
            with self.subTest(value=value):
                marker = cp.build_marker(self.root, OP, self.issue, self.pr)
                marker["issue"]["closed_at"] = value
                marker["merge"]["merged_at"] = value
                self.assertFalse(cp.marker_is_valid(self.root, marker, self.ancestor))


if __name__ == "__main__":
    unittest.main()
