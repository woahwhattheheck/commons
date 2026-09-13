import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import validate_submission as validator


BASE = Path(__file__).resolve().parent


class SubmissionValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in [
            "README.md",
            "REQUIREMENTS-EVIDENCE.md",
            "SCIENTIFIC-BASIS.md",
            "PROPOSAL-DRAFT.md",
            "SUBMISSION-CHECKLIST.md",
            "readiness.json",
        ]:
            shutil.copy2(BASE / name, self.root / name)

    def tearDown(self):
        self.temp.cleanup()

    def manifest(self):
        return json.loads((self.root / "readiness.json").read_text(encoding="utf-8"))

    def write_manifest(self, data):
        (self.root / "readiness.json").write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def test_baseline_blocked_manifest_is_structurally_valid(self):
        state, errors = validator.validate(self.root)
        self.assertEqual("BLOCKED", state)
        self.assertEqual([], errors)

    def test_ready_requires_every_human_gate(self):
        data = self.manifest()
        data["state"] = "READY"
        self.write_manifest(data)
        state, errors = validator.validate(self.root)
        self.assertEqual("READY", state)
        self.assertTrue(any("READY requires every human gate true" in item for item in errors))
        self.assertTrue(any("hashed final human proposal" in item for item in errors))

    def test_artifact_path_traversal_is_rejected(self):
        data = self.manifest()
        data["artifacts"]["final_proposal"] = {
            "path": "../outside.md",
            "sha256": "0" * 64,
        }
        self.write_manifest(data)
        _, errors = validator.validate(self.root)
        self.assertTrue(any("path must stay inside" in item for item in errors))

    def test_artifact_hash_mismatch_is_rejected(self):
        final = self.root / "FINAL-HUMAN-PROPOSAL.md"
        final.write_text("human final\n", encoding="utf-8")
        data = self.manifest()
        data["artifacts"]["final_proposal"] = {
            "path": final.name,
            "sha256": "0" * 64,
        }
        self.write_manifest(data)
        _, errors = validator.validate(self.root)
        self.assertTrue(any("sha256 does not match" in item for item in errors))

    def test_submitted_cannot_be_true_without_authorization(self):
        data = self.manifest()
        data["external_actions"]["submitted"] = True
        self.write_manifest(data)
        _, errors = validator.validate(self.root)
        self.assertTrue(any("submitted cannot be true" in item for item in errors))

    def test_challenge_agreement_acceptance_requires_review(self):
        data = self.manifest()
        data["external_actions"]["challenge_agreement_accepted"] = True
        self.write_manifest(data)
        _, errors = validator.validate(self.root)
        self.assertTrue(any("cannot be marked accepted before human review" in item for item in errors))

    def test_fully_armed_human_rewritten_package_can_be_ready(self):
        final = self.root / "FINAL-HUMAN-PROPOSAL.md"
        final.write_text(
            "Final proposal independently reviewed and rewritten by the authorized human applicant.\n",
            encoding="utf-8",
        )
        digest = hashlib.sha256(final.read_bytes()).hexdigest()

        data = self.manifest()
        data["state"] = "READY"
        data["human_gates"] = {key: True for key in validator.REQUIRED_GATES}
        data["external_actions"]["challenge_agreement_accepted"] = True
        data["artifacts"]["final_proposal"] = {
            "path": final.name,
            "sha256": digest,
        }
        self.write_manifest(data)

        state, errors = validator.validate(self.root)
        self.assertEqual("READY", state)
        self.assertEqual([], errors)

    def test_ready_cannot_point_at_ai_draft_as_final(self):
        draft = self.root / "PROPOSAL-DRAFT.md"
        digest = hashlib.sha256(draft.read_bytes()).hexdigest()
        data = self.manifest()
        data["state"] = "READY"
        data["human_gates"] = {key: True for key in validator.REQUIRED_GATES}
        data["external_actions"]["challenge_agreement_accepted"] = True
        data["artifacts"]["final_proposal"] = {
            "path": "PROPOSAL-DRAFT.md",
            "sha256": digest,
        }
        self.write_manifest(data)
        _, errors = validator.validate(self.root)
        self.assertTrue(any("separate human-rewritten artifact" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
