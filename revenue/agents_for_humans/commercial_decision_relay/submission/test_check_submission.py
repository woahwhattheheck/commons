from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from submission import check_submission as check

FIXTURE_ROOT = Path(__file__).resolve().parents[1]


def load_manifest():
    return json.loads((FIXTURE_ROOT / "submission" / "manifest.json").read_text(encoding="utf-8"))


class SubmissionCheckTests(unittest.TestCase):
    def test_real_packet_is_internal_ready_external_pending(self):
        result = check.validate(load_manifest(), FIXTURE_ROOT)
        self.assertEqual(result["state"], "INTERNAL_READY_EXTERNAL_PENDING")
        self.assertEqual(
            result["pending_required_external"],
            ["aws_builder_id", "devpost_submission", "public_demo_video"],
        )
        self.assertFalse(result["devpost_submission_authorized"])
        self.assertFalse(result["prize_awarded"])
        self.assertFalse(result["revenue_recognized"])

    def test_all_required_external_complete_can_be_submission_ready(self):
        manifest = load_manifest()
        values = {
            "aws_builder_id": "builder-id-entered",
            "public_demo_video": "https://www.youtube.com/watch?v=example",
            "devpost_submission": "https://devpost.com/software/example",
        }
        for item in manifest["external_requirements"]:
            if item["id"] in values:
                item["status"] = "COMPLETE"
                item["value"] = values[item["id"]]
        result = check.validate(manifest, FIXTURE_ROOT)
        self.assertEqual(result["state"], "SUBMISSION_READY")
        self.assertEqual(result["pending_required_external"], [])
        self.assertFalse(result["devpost_submission_authorized"])

    def test_complete_requires_value(self):
        manifest = load_manifest()
        target = next(x for x in manifest["external_requirements"] if x["id"] == "aws_builder_id")
        target["status"] = "COMPLETE"
        target["value"] = None
        with self.assertRaisesRegex(check.SubmissionError, "COMPLETE requires"):
            check.validate(manifest, FIXTURE_ROOT)

    def test_pending_must_not_smuggle_value(self):
        manifest = load_manifest()
        target = next(x for x in manifest["external_requirements"] if x["id"] == "aws_builder_id")
        target["value"] = "secret-ish-surprise"
        with self.assertRaisesRegex(check.SubmissionError, "non-COMPLETE"):
            check.validate(manifest, FIXTURE_ROOT)

    def test_repo_url_must_be_repository_root(self):
        manifest = load_manifest()
        manifest["public_code_repo_url"] += "/tree/main/revenue"
        with self.assertRaisesRegex(check.SubmissionError, "repository-root URL"):
            check.validate(manifest, FIXTURE_ROOT)

    def test_project_source_must_be_under_repo(self):
        manifest = load_manifest()
        manifest["project_source_url"] = "https://github.com/other/repo/tree/main"
        with self.assertRaisesRegex(check.SubmissionError, "must be under"):
            check.validate(manifest, FIXTURE_ROOT)

    def test_unknown_external_requirement_rejected(self):
        manifest = load_manifest()
        manifest["external_requirements"].append({
            "id": "invented",
            "required": False,
            "status": "OPTIONAL_PENDING",
            "value": None,
        })
        with self.assertRaisesRegex(check.SubmissionError, "ids mismatch"):
            check.validate(manifest, FIXTURE_ROOT)

    def test_duplicate_external_requirement_rejected(self):
        manifest = load_manifest()
        manifest["external_requirements"].append(copy.deepcopy(manifest["external_requirements"][0]))
        with self.assertRaisesRegex(check.SubmissionError, "duplicate external requirement"):
            check.validate(manifest, FIXTURE_ROOT)

    def test_missing_required_artifact_rejected(self):
        manifest = load_manifest()
        manifest["required_artifacts"].append("does-not-exist.txt")
        with self.assertRaisesRegex(check.SubmissionError, "required artifact missing"):
            check.validate(manifest, FIXTURE_ROOT)

    def test_path_escape_rejected(self):
        manifest = load_manifest()
        manifest["required_artifacts"].append("../README.md")
        with self.assertRaisesRegex(check.SubmissionError, "under project root"):
            check.validate(manifest, FIXTURE_ROOT)

    def test_authority_escalation_rejected(self):
        manifest = load_manifest()
        manifest["authority"]["devpost_submission_authorized"] = True
        with self.assertRaisesRegex(check.SubmissionError, "authority block"):
            check.validate(manifest, FIXTURE_ROOT)

    def test_bool_is_not_accepted_as_required_string(self):
        manifest = load_manifest()
        manifest["project_name"] = True
        with self.assertRaisesRegex(check.SubmissionError, "non-empty string"):
            check.validate(manifest, FIXTURE_ROOT)

    def test_deadline_must_have_timezone(self):
        manifest = load_manifest()
        manifest["competition"]["deadline"] = "2026-09-14T17:00:00"
        with self.assertRaisesRegex(check.SubmissionError, "include timezone"):
            check.validate(manifest, FIXTURE_ROOT)


if __name__ == "__main__":
    unittest.main()
