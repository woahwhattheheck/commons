from teaming_conversion_test_support import *


class TeamingConversionAuthorityTests(unittest.TestCase):
    def test_positive_historical_is_ready_but_labeled_historical_only(self):
        _, _, _, receipt = compile_fixture()
        self.assertEqual(receipt["disposition"], "FOLLOWUP_READY")
        self.assertEqual(receipt["mode"], HISTORICAL_MODE)
        self.assertTrue(receipt["historical_integrity_only"])
        self.assertTrue(receipt["owner_review_only"])
        self.assertTrue(all(value is False for value in receipt["external_authority"].values()))

    def test_default_current_registry_cannot_be_minted_by_candidate(self):
        candidate = canonical_bytes(base_candidate())
        evidence = canonical_bytes(base_evidence())
        receipt = compile_current_bytes(candidate, evidence)
        self.assertEqual(receipt["mode"], CURRENT_MODE)
        self.assertEqual(receipt["disposition"], "HOLD")
        self.assertIn("trusted_root_missing", receipt["trust_blockers"])
        self.assertEqual(receipt["safe_assets"], [])
        self.assertEqual(receipt["safe_commercial_facts"], [])

    def test_current_positive_path_uses_fixed_registry_loader(self):
        candidate, evidence, roots, _ = compile_fixture()
        with mock.patch(
            "revenue.teaming_conversion.control.load_current_roots_bytes",
            return_value=roots,
        ), mock.patch("revenue.teaming_conversion.control._utc_now", return_value=NOW):
            receipt = compile_current_bytes(candidate, evidence)
        self.assertEqual(receipt["mode"], CURRENT_MODE)
        self.assertEqual(receipt["disposition"], "FOLLOWUP_READY")
        self.assertFalse(receipt["historical_integrity_only"])

    def test_candidate_cannot_embed_authority_records(self):
        candidate = base_candidate()
        candidate["observations"] = []
        evidence, roots = build_roots(base_evidence())
        with self.assertRaises(ControlError):
            compile_historical_bytes(
                canonical_bytes(candidate), evidence, roots, evaluated_at=NOW
            )

    def test_policy_identity_is_repository_owned(self):
        _, _, _, receipt = compile_fixture(root_mutate={"policy_sha256": "f" * 64})
        self.assertEqual(receipt["disposition"], "HOLD")
        self.assertIn("trusted_policy_identity_mismatch", receipt["trust_blockers"])

    def test_exact_evidence_byte_mismatch_holds(self):
        evidence = base_evidence()
        original_bytes, roots = build_roots(evidence)
        evidence["commitments"][0]["safe_fact"] = "Mutated fact."
        mutated_bytes = canonical_bytes(evidence)
        receipt = compile_historical_bytes(
            canonical_bytes(base_candidate()), mutated_bytes, roots, evaluated_at=NOW
        )
        self.assertEqual(receipt["disposition"], "HOLD")
        self.assertIn("trusted_evidence_bytes_mismatch", receipt["trust_blockers"])
        self.assertEqual(receipt["safe_commercial_facts"], [])
        self.assertNotEqual(original_bytes, mutated_bytes)

    def test_section_digest_mismatch_holds_even_with_updated_whole_digest(self):
        evidence = base_evidence()
        evidence_bytes, roots = build_roots(
            evidence,
            mutate={"assets_sha256": "e" * 64},
        )
        receipt = compile_historical_bytes(
            canonical_bytes(base_candidate()), evidence_bytes, roots, evaluated_at=NOW
        )
        self.assertEqual(receipt["disposition"], "HOLD")
        self.assertIn("trusted_assets_mismatch", receipt["trust_blockers"])

    def test_mandatory_curable_gate_blocks_without_policy_duplication(self):
        evidence = base_evidence()
        evidence["qualification_gates"].append(
            {
                "gate_id": "gate-security-cure",
                "mandatory": True,
                "state": "CURABLE",
                "owner_action": "Provide current security evidence.",
                "decided_at": ts(NOW - timedelta(minutes=15)),
                "decision_ref": "gate-decision-2",
                "decision_sha256": "6" * 64,
            }
        )
        _, _, _, receipt = compile_fixture(evidence=evidence)
        self.assertEqual(receipt["disposition"], "QUALIFICATION_BLOCKED")
        self.assertIn(
            "mandatory_gate_not_clear:gate-security-cure:CURABLE",
            receipt["qualification_blockers"],
        )

    def test_supersession_fork_holds(self):
        evidence = base_evidence()
        for suffix, minute, decision, digit in [
            ("2", 20, "DECLINED", "7"),
            ("3", 10, "POSITIVE_CONTINUE", "8"),
        ]:
            evidence["observations"].append(
                {
                    "observation_id": f"obs-{suffix}",
                    "message_ref": f"gmail-msg-{suffix}",
                    "source_class": "GMAIL",
                    "sender_ref": "sender-acme",
                    "thread_id": "thread-acme-1",
                    "received_at": ts(NOW - timedelta(minutes=minute)),
                    "content_sha256": digit * 64,
                    "supersedes": "obs-1",
                }
            )
            evidence["interpretations"].append(
                {
                    "interpretation_id": f"interpretation-{suffix}",
                    "observation_id": f"obs-{suffix}",
                    "message_ref": f"gmail-msg-{suffix}",
                    "content_sha256": digit * 64,
                    "decision": decision,
                    "reviewed_at": ts(NOW - timedelta(minutes=minute - 1)),
                    "owner_review_ref": f"owner-review-{suffix}",
                    "owner_review_sha256": digit * 64,
                }
            )
        _, _, _, receipt = compile_fixture(evidence=evidence)
        self.assertEqual(receipt["disposition"], "HOLD")
        self.assertIn("supersession_fork:obs-1", receipt["trust_blockers"])

