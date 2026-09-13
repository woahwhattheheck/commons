from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from submission.check_packet import PacketError, validate

ROOT = Path(__file__).resolve().parents[1]


def manifest():
    return json.loads((ROOT / "submission" / "manifest.json").read_text(encoding="utf-8"))


class PacketTests(unittest.TestCase):
    def test_real_manifest_is_external_pending(self):
        result = validate(manifest(), ROOT)
        self.assertEqual(result["state"], "LOCAL_PACKET_COMPLETE_EXTERNAL_PENDING")
        self.assertEqual(len(result["pending_external_gates"]), 4)
        self.assertFalse(result["submission_authorized"])

    def test_all_complete_still_does_not_authorize_submission(self):
        data = manifest()
        for gate in data["external_gates"]:
            gate["status"] = "COMPLETE"
        result = validate(data, ROOT)
        self.assertEqual(result["state"], "EXTERNAL_FIELDS_REPORTED_COMPLETE_REQUIRES_HUMAN_FINAL_CHECK")
        self.assertFalse(result["submission_authorized"])
        self.assertFalse(result["award_claimed"])
        self.assertFalse(result["revenue_recognized"])

    def test_real_user_validation_cannot_be_invented(self):
        data = manifest()
        data["project"]["real_user_validation"] = True
        with self.assertRaisesRegex(PacketError, "must remain false"):
            validate(data, ROOT)

    def test_external_authority_escalation_rejected(self):
        data = manifest()
        data["authority"]["submission_authorized"] = True
        with self.assertRaisesRegex(PacketError, "authority"):
            validate(data, ROOT)

    def test_duplicate_gate_rejected(self):
        data = manifest()
        data["external_gates"].append(copy.deepcopy(data["external_gates"][0]))
        with self.assertRaisesRegex(PacketError, "duplicate gate"):
            validate(data, ROOT)

    def test_missing_gate_rejected(self):
        data = manifest()
        data["external_gates"].pop()
        with self.assertRaisesRegex(PacketError, "gate set mismatch"):
            validate(data, ROOT)

    def test_missing_artifact_rejected(self):
        data = manifest()
        data["required_local_artifacts"].append("nope.txt")
        with self.assertRaisesRegex(PacketError, "missing required artifact"):
            validate(data, ROOT)

    def test_path_escape_rejected(self):
        data = manifest()
        data["required_local_artifacts"].append("../secret")
        with self.assertRaisesRegex(PacketError, "project root"):
            validate(data, ROOT)


if __name__ == "__main__":
    unittest.main()
