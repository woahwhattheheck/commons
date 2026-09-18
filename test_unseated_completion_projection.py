import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import completion_projection as cp


OP = "INBOUND-PAID-SCOPE-OWNER-CLOSE-DESK-20260916-ZSOL"


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(("blob %d\0" % len(data)).encode("ascii") + data).hexdigest()


class CompletionProjectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "p").mkdir()
        self.source = self.root / "p" / (OP + ".md")
        self.source.write_text(
            "---\nfrom: UNSEATED\nto: TABLE\nid: %s\n---\nwork\n" % OP,
            encoding="utf-8",
        )
        self.issue = {
            "number": 15130,
            "state": "closed",
            "state_reason": "completed",
            "closed_at": "2026-09-17T00:41:27Z",
            "html_url": "https://github.com/woahwhattheheck/commons/issues/15130",
        }
        self.pr = {
            "number": 15138,
            "merged": True,
            "merged_at": "2026-09-17T00:41:26Z",
            "merge_commit_sha": "c" * 40,
            "base": {"ref": "main"},
            "body": "Closes #15130.",
            "html_url": "https://github.com/woahwhattheheck/commons/pull/15138",
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_verified_marker_suppresses_only_exact_actionable_route(self):
        marker = cp.build_marker(self.root, OP, self.issue, self.pr)
        self.assertEqual("wrote", cp.write_marker(self.root, marker))
        completed = cp.completed_operation_ids(self.root)
        self.assertEqual(frozenset({OP}), completed)
        self.assertTrue(
            cp.is_completed_actionable(
                {"id": OP, "from": "UNSEATED", "to": "TABLE"}, completed
            )
        )
        self.assertFalse(
            cp.is_completed_actionable(
                {"id": OP, "from": "UNSEATED", "to": "COURT"}, completed
            )
        )
        self.assertFalse(
            cp.is_completed_actionable(
                {"id": OP, "from": "PLAYER1", "to": "TABLE"}, completed
            )
        )
        self.assertFalse(
            cp.is_completed_actionable(
                {"id": "OTHER-OPEN-OPERATION-0001", "from": "UNSEATED", "to": "TABLE"},
                completed,
            )
        )

    def test_closed_or_duplicate_alone_cannot_mint_completion(self):
        for reason in ("not_planned", None):
            issue = dict(self.issue, state_reason=reason)
            with self.assertRaises(cp.CompletionEvidenceError):
                cp.build_marker(self.root, OP, issue, self.pr)
        duplicate = dict(self.issue, number=15616, state_reason="duplicate")
        with self.assertRaises(cp.CompletionEvidenceError):
            cp.build_marker(self.root, OP, duplicate, self.pr)

    def test_merge_must_be_main_merged_and_explicitly_close_issue(self):
        bad = dict(self.pr, merged=False)
        with self.assertRaises(cp.CompletionEvidenceError):
            cp.build_marker(self.root, OP, self.issue, bad)
        bad = dict(self.pr, base={"ref": "feature"})
        with self.assertRaises(cp.CompletionEvidenceError):
            cp.build_marker(self.root, OP, self.issue, bad)
        bad = dict(self.pr, body="Mentions #15130 without closing it.")
        with self.assertRaises(cp.CompletionEvidenceError):
            cp.build_marker(self.root, OP, self.issue, bad)
        bad = dict(self.pr, merged_at="2026-09-17T00:41:28Z")
        with self.assertRaises(cp.CompletionEvidenceError):
            cp.build_marker(self.root, OP, self.issue, bad)
        bad = dict(self.pr, html_url="https://github.com/other/repo/pull/15138")
        with self.assertRaises(cp.CompletionEvidenceError):
            cp.build_marker(self.root, OP, self.issue, bad)

    def test_source_mismatch_fails_closed_instead_of_hiding_work(self):
        marker = cp.build_marker(self.root, OP, self.issue, self.pr)
        cp.write_marker(self.root, marker)
        self.source.write_text("tampered\n", encoding="utf-8")
        self.assertEqual(frozenset(), cp.completed_operation_ids(self.root))

    def test_reopen_removes_only_matching_issue_marker(self):
        marker = cp.build_marker(self.root, OP, self.issue, self.pr)
        cp.write_marker(self.root, marker)
        self.assertFalse(cp.remove_marker(self.root, OP, 99999))
        self.assertTrue(cp.remove_marker(self.root, OP, 15130))
        self.assertEqual(frozenset(), cp.completed_operation_ids(self.root))

    def test_marker_reader_rejects_tampered_provenance(self):
        marker = cp.build_marker(self.root, OP, self.issue, self.pr)
        marker["issue"]["url"] = "https://github.com/other/repo/issues/15130"
        path = self.root / cp.marker_rel(OP)
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(marker), encoding="utf-8")
        self.assertEqual(frozenset(), cp.completed_operation_ids(self.root))

    def test_marker_binds_git_blob_identity(self):
        marker = cp.build_marker(self.root, OP, self.issue, self.pr)
        expected = git_blob_sha1(self.source.read_bytes())
        self.assertEqual(expected, marker["source"]["blob_sha1"])


class CheckedInPredecessorTests(unittest.TestCase):
    def test_15130_backfill_is_valid_and_historical_source_survives(self):
        root = Path(__file__).resolve().parent
        marker_path = root / cp.marker_rel(OP)
        source_path = root / cp.source_rel(OP)
        self.assertTrue(source_path.is_file())
        self.assertTrue(marker_path.is_file())
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        self.assertEqual(15130, marker["issue"]["number"])
        self.assertEqual(15138, marker["merge"]["pr_number"])
        self.assertEqual(
            "ccab91f74dfec13e1dcb8228b422e044fbc19e08",
            marker["merge"]["merge_commit_sha"],
        )
        self.assertTrue(cp.marker_is_valid(root, marker))
        self.assertIn(OP, cp.completed_operation_ids(root))

    def test_projection_wiring_observes_close_reopen_without_faking_open_receipts(self):
        root = Path(__file__).resolve().parent
        workflow = (root / ".github" / "workflows" / "commons-board.yml").read_text(
            encoding="utf-8"
        )
        publisher = (root / "board_ingest.py").read_text(encoding="utf-8")
        self.assertIn("types: [opened, closed, reopened]", workflow)
        self.assertIn("github.event.action == 'opened'", workflow)
        self.assertIn('PROJECTION_PROTOCOL = "v2"', publisher)
        self.assertIn("completion_projection.source_paths(ROOT)", publisher)
        self.assertIn("completion_projection.completed_operation_ids(ROOT)", publisher)
        self.assertIn('action in ("closed", "reopened")', publisher)


if __name__ == "__main__":
    unittest.main()
