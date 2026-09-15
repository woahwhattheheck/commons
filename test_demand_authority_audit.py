import copy
import json
import tempfile
import unittest
from pathlib import Path

from host.demand_authority_audit import EvidenceError, audit, main

A = "a" * 40
B = "b" * 40
C = "c" * 40
D = "d" * 40


def envelope():
    repo = "woahwhattheheck/commons"
    return {
        "schema": "demand-authority-audit/v1",
        "demand": {
            "demand_id": "synthetic-open-001",
            "advertised_state": "OPEN",
            "repo": repo,
            "required_paths": ["host/example.py", "test_example.py"],
        },
        "authority": {
            "repo": repo,
            "observed_ref": "main",
            "observed_commit": A,
            "evidence_commit": A,
            "paths": [
                {"path": "host/example.py", "repo": repo, "commit": A, "present": True, "blob_sha": D},
                {"path": "test_example.py", "repo": repo, "commit": A, "present": True, "blob_sha": C},
            ],
            "carrier": {
                "repo": repo,
                "number": 7774,
                "state": "MERGED",
                "head_sha": B,
                "merge_commit_sha": C,
                "merge_commit_is_ancestor_of_evidence_commit": True,
                "source": {"kind": "github_pr", "locator": "https://github.com/woahwhattheheck/commons/pull/7774"},
            },
        },
    }


class AuditTest(unittest.TestCase):
    def test_merged_plus_paths_lands(self):
        report = audit(envelope())
        self.assertEqual(report["decision"], "LANDED")
        self.assertEqual(report["mutations_performed"], 0)

    def test_missing_path_evidence_fails_open(self):
        data = envelope()
        data["authority"]["paths"].pop()
        report = audit(data)
        self.assertEqual(report["decision"], "KEEP_OPEN")
        self.assertIn("MISSING_PATH_EVIDENCE", {r["code"] for r in report["reasons"]})

    def test_absent_required_path_fails_open(self):
        data = envelope()
        data["authority"]["paths"][1] = {"path": "test_example.py", "repo": data["demand"]["repo"], "commit": A, "present": False}
        report = audit(data)
        self.assertEqual(report["decision"], "KEEP_OPEN")
        self.assertIn("REQUIRED_PATH_ABSENT", {r["code"] for r in report["reasons"]})

    def test_open_carrier_fails_open(self):
        data = envelope()
        data["authority"]["carrier"].update(state="OPEN", merge_commit_sha=None, merge_commit_is_ancestor_of_evidence_commit=False)
        self.assertEqual(audit(data)["decision"], "KEEP_OPEN")

    def test_unproven_merge_fails_open(self):
        data = envelope()
        data["authority"]["carrier"]["merge_commit_is_ancestor_of_evidence_commit"] = False
        report = audit(data)
        self.assertEqual(report["decision"], "KEEP_OPEN")
        self.assertIn("MERGE_NOT_PROVEN_ON_OBSERVED_AUTHORITY", {r["code"] for r in report["reasons"]})

    def test_head_drift_invalidates_snapshot(self):
        data = envelope()
        data["authority"]["observed_commit"] = B
        report = audit(data)
        self.assertEqual(report["decision"], "KEEP_OPEN")
        self.assertEqual(report["reasons"][0]["code"], "STALE_AUTHORITY_SNAPSHOT")

    def test_repository_fence_wins(self):
        data = envelope()
        data["authority"]["fence"] = {
            "active": True,
            "reason": "DO_NOT_RECONSTRUCT",
            "source": {"kind": "repository_artifact", "locator": "p/fence.md", "commit": A},
        }
        self.assertEqual(audit(data)["decision"], "FENCED")

    def test_github_issue_fence(self):
        data = envelope()
        data["authority"]["carrier"] = None
        data["authority"]["paths"] = []
        data["demand"]["required_paths"] = []
        data["authority"]["fence"] = {
            "active": True,
            "reason": "SOURCE_BYTES_LOST",
            "source": {"kind": "github_issue", "locator": "https://github.com/woahwhattheheck/commons/issues/12"},
        }
        self.assertEqual(audit(data)["decision"], "FENCED")

    def test_repository_artifact_fence_must_bind_evidence_commit(self):
        data = envelope()
        data["authority"]["fence"] = {
            "active": True,
            "reason": "DO_NOT_RECONSTRUCT",
            "source": {"kind": "repository_artifact", "locator": "p/fence.md", "commit": B},
        }
        with self.assertRaises(EvidenceError):
            audit(data)

    def test_landed_successor_supersedes(self):
        data = envelope()
        data["authority"]["carrier"] = None
        data["authority"]["paths"] = []
        data["authority"]["superseded_by"] = {
            "operation_id": "replacement-v2",
            "status": "LANDED",
            "commit": B,
            "commit_is_ancestor_of_evidence_commit": True,
            "source": {"kind": "github_pr", "locator": "https://github.com/woahwhattheheck/commons/pull/8888"},
        }
        self.assertEqual(audit(data)["decision"], "SUPERSEDED")

    def test_unproven_successor_fails_open(self):
        data = envelope()
        data["authority"]["carrier"] = None
        data["authority"]["paths"] = []
        data["authority"]["superseded_by"] = {
            "operation_id": "replacement-v2",
            "status": "LANDED",
            "commit": B,
            "commit_is_ancestor_of_evidence_commit": False,
            "source": {"kind": "github_pr", "locator": "https://github.com/woahwhattheheck/commons/pull/8888"},
        }
        self.assertEqual(audit(data)["decision"], "KEEP_OPEN")

    def test_conflicting_path_is_conflict(self):
        data = envelope()
        data["authority"]["paths"].append({"path": "host/example.py", "repo": data["demand"]["repo"], "commit": A, "present": False})
        report = audit(data)
        self.assertEqual(report["decision"], "CONFLICT")
        self.assertIn("PATH_CONFLICT:host/example.py", report["reasons"][0]["details"])

    def test_cross_repo_path_is_conflict(self):
        data = envelope()
        data["authority"]["paths"][0]["repo"] = "someone/else"
        report = audit(data)
        self.assertEqual(report["decision"], "CONFLICT")
        self.assertIn("PATH_REPO_MISMATCH:host/example.py", report["reasons"][0]["details"])

    def test_wrong_repo_pr_source_rejected(self):
        data = envelope()
        data["authority"]["carrier"]["source"]["locator"] = "https://github.com/other/repo/pull/7"
        with self.assertRaises(EvidenceError):
            audit(data)

    def test_unsafe_path_rejected(self):
        data = envelope()
        data["demand"]["required_paths"] = ["../secret"]
        with self.assertRaises(EvidenceError):
            audit(data)

    def test_receipt_deterministic(self):
        one = audit(envelope())
        two = audit(copy.deepcopy(envelope()))
        self.assertEqual(json.dumps(one, sort_keys=True, separators=(",", ":")), json.dumps(two, sort_keys=True, separators=(",", ":")))
        self.assertEqual(one["receipt_sha256"], two["receipt_sha256"])

    def test_slack_state_string_never_closes_work(self):
        data = envelope()
        data["demand"]["advertised_state"] = "CLOSED"
        data["authority"]["carrier"] = None
        data["authority"]["paths"] = []
        report = audit(data)
        self.assertEqual(report["decision"], "KEEP_OPEN")
        self.assertIn("ADVERTISED_STATE_NOT_OPEN", {r["code"] for r in report["reasons"]})

    def test_cli_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "input.json"
            path.write_text(json.dumps(envelope()), encoding="utf-8")
            self.assertEqual(main([str(path)]), 0)


if __name__ == "__main__":
    unittest.main()
