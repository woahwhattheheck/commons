from teaming_conversion_test_support import *


class TeamingConversionIntegrityTests(unittest.TestCase):
    def test_unapproved_mandatory_commitment_blocks(self):
        evidence = base_evidence()
        evidence["commitments"][0]["approved"] = False
        _, _, _, receipt = compile_fixture(evidence=evidence)
        self.assertEqual(receipt["disposition"], "QUALIFICATION_BLOCKED")
        self.assertIn(
            "mandatory_commitment_unapproved:commit-price",
            receipt["qualification_blockers"],
        )

    def test_bool_integer_alias_is_rejected(self):
        evidence = base_evidence()
        evidence["qualification_gates"][0]["mandatory"] = 1
        evidence_bytes, roots = build_roots(base_evidence())
        with self.assertRaises(ControlError):
            compile_historical_bytes(
                canonical_bytes(base_candidate()),
                canonical_bytes(evidence),
                roots,
                evaluated_at=NOW,
            )

    def test_duplicate_json_key_is_rejected(self):
        with self.assertRaises(DuplicateKeyError):
            parse_json_bytes(b'{"schema":"x","schema":"y"}\n')

    def test_non_finite_json_is_rejected(self):
        with self.assertRaises(ControlError):
            parse_json_bytes(b'{"value":NaN}\n')

    def test_valid_linear_supersession_uses_unique_terminal(self):
        evidence = base_evidence()
        evidence["observations"].append(
            {
                "observation_id": "obs-2",
                "message_ref": "gmail-msg-2",
                "source_class": "GMAIL",
                "sender_ref": "sender-acme",
                "thread_id": "thread-acme-1",
                "received_at": ts(NOW - timedelta(minutes=15)),
                "content_sha256": "7" * 64,
                "supersedes": "obs-1",
            }
        )
        evidence["interpretations"].append(
            {
                "interpretation_id": "interpretation-2",
                "observation_id": "obs-2",
                "message_ref": "gmail-msg-2",
                "content_sha256": "7" * 64,
                "decision": "DECLINED",
                "reviewed_at": ts(NOW - timedelta(minutes=14)),
                "owner_review_ref": "owner-review-2",
                "owner_review_sha256": "8" * 64,
            }
        )
        _, _, _, receipt = compile_fixture(evidence=evidence)
        self.assertEqual(receipt["disposition"], "DECLINED")
        self.assertEqual(receipt["current_observation"]["observation_id"], "obs-2")

    def test_non_increasing_supersession_time_holds(self):
        evidence = base_evidence()
        evidence["observations"].append(
            {
                "observation_id": "obs-2",
                "message_ref": "gmail-msg-2",
                "source_class": "GMAIL",
                "sender_ref": "sender-acme",
                "thread_id": "thread-acme-1",
                "received_at": evidence["observations"][0]["received_at"],
                "content_sha256": "7" * 64,
                "supersedes": "obs-1",
            }
        )
        evidence["interpretations"].append(
            {
                "interpretation_id": "interpretation-2",
                "observation_id": "obs-2",
                "message_ref": "gmail-msg-2",
                "content_sha256": "7" * 64,
                "decision": "POSITIVE_CONTINUE",
                "reviewed_at": ts(NOW - timedelta(minutes=20)),
                "owner_review_ref": "owner-review-2",
                "owner_review_sha256": "8" * 64,
            }
        )
        _, _, _, receipt = compile_fixture(evidence=evidence)
        self.assertEqual(receipt["disposition"], "HOLD")
        self.assertIn("supersession_time_not_increasing:obs-2", receipt["trust_blockers"])

    def test_missing_owner_interpretation_holds(self):
        evidence = base_evidence()
        evidence["interpretations"] = []
        _, _, _, receipt = compile_fixture(evidence=evidence)
        self.assertEqual(receipt["disposition"], "HOLD")
        self.assertIn("owner_interpretation_missing:obs-1", receipt["trust_blockers"])

    def test_interpretation_content_binding_mismatch_holds(self):
        evidence = base_evidence()
        evidence["interpretations"][0]["content_sha256"] = "9" * 64
        _, _, _, receipt = compile_fixture(evidence=evidence)
        self.assertEqual(receipt["disposition"], "HOLD")
        self.assertIn("owner_interpretation_content_mismatch:obs-1", receipt["trust_blockers"])

    def test_ambiguous_interpretation_needs_clarification(self):
        evidence = base_evidence()
        evidence["interpretations"][0]["decision"] = "AMBIGUOUS"
        _, _, _, receipt = compile_fixture(evidence=evidence)
        self.assertEqual(receipt["disposition"], "NEEDS_CLARIFICATION")

