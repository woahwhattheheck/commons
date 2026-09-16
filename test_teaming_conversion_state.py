from teaming_conversion_test_support import *


class TeamingConversionStateTests(unittest.TestCase):
    def test_disconnected_newer_observation_holds(self):
        evidence = base_evidence()
        evidence["observations"].append(
            {
                "observation_id": "obs-2",
                "message_ref": "gmail-msg-2",
                "source_class": "GMAIL",
                "sender_ref": "sender-acme",
                "thread_id": "thread-acme-1",
                "received_at": ts(NOW - timedelta(minutes=5)),
                "content_sha256": "7" * 64,
                "supersedes": None,
            }
        )
        evidence["interpretations"].append(
            {
                "interpretation_id": "interpretation-2",
                "observation_id": "obs-2",
                "message_ref": "gmail-msg-2",
                "content_sha256": "7" * 64,
                "decision": "POSITIVE_CONTINUE",
                "reviewed_at": ts(NOW - timedelta(minutes=4)),
                "owner_review_ref": "owner-review-2",
                "owner_review_sha256": "8" * 64,
            }
        )
        _, _, _, receipt = compile_fixture(evidence=evidence)
        self.assertEqual(receipt["disposition"], "HOLD")
        self.assertIn("supersession_root_count_invalid", receipt["trust_blockers"])

    def test_counterparty_sender_binding_is_explicit(self):
        evidence = base_evidence()
        evidence["observations"][0]["sender_ref"] = "sender-unrelated"
        _, _, _, receipt = compile_fixture(evidence=evidence)
        self.assertEqual(receipt["disposition"], "HOLD")
        self.assertIn("observation_sender_not_counterparty:obs-1", receipt["trust_blockers"])

    def test_cross_thread_observation_holds(self):
        evidence = base_evidence()
        evidence["observations"][0]["thread_id"] = "thread-other"
        _, _, _, receipt = compile_fixture(evidence=evidence)
        self.assertEqual(receipt["disposition"], "HOLD")
        self.assertIn("observation_cross_thread:obs-1", receipt["trust_blockers"])

    def test_current_verification_rereads_repository_roots(self):
        from revenue.teaming_conversion.control import _compile_at

        candidate, evidence, roots, _ = compile_fixture()
        receipt = _compile_at(
            candidate,
            evidence,
            roots,
            evaluated_at=NOW,
            mode=CURRENT_MODE,
        )
        self.assertEqual(receipt["disposition"], "FOLLOWUP_READY")
        receipt_bytes = canonical_bytes(receipt)
        self.assertTrue(verify_integrity_bytes(candidate, evidence, roots, receipt_bytes))

        current = verify_current_bytes(candidate, evidence, receipt_bytes)
        self.assertFalse(current["integrity_valid"])
        self.assertFalse(current["current_valid"])
        self.assertEqual(current["current_disposition"], "HOLD")

    def test_current_receipt_uses_short_recheck_window(self):
        from revenue.teaming_conversion.control import _compile_at

        candidate, evidence, roots, _ = compile_fixture()
        receipt = _compile_at(
            candidate,
            evidence,
            roots,
            evaluated_at=NOW,
            mode=CURRENT_MODE,
        )
        valid_until = datetime.fromisoformat(
            receipt["current_valid_until"].replace("Z", "+00:00")
        )
        self.assertEqual(valid_until, NOW + timedelta(minutes=5))

    def test_descriptor_mutation_with_old_release_does_not_project(self):
        evidence = base_evidence()
        evidence["assets"][0]["safe_snippets"] = ["Mutated prospect copy."]
        _, _, _, receipt = compile_fixture(evidence=evidence)
        self.assertEqual(receipt["disposition"], "ASSET_PREP_REQUIRED")
        self.assertIn(
            "required_asset_exact_release_missing:asset-capability",
            receipt["asset_blockers"],
        )
        self.assertEqual(receipt["safe_assets"], [])

    def test_internal_only_asset_never_projects(self):
        evidence = base_evidence()
        evidence["assets"][0]["release_class"] = "INTERNAL_ONLY"
        evidence["releases"] = []
        _, _, _, receipt = compile_fixture(evidence=evidence)
        self.assertEqual(receipt["disposition"], "ASSET_PREP_REQUIRED")
        self.assertIn("required_asset_internal_only:asset-capability", receipt["asset_blockers"])
        self.assertEqual(receipt["safe_assets"], [])

    def test_missing_requested_asset_blocks(self):
        candidate = base_candidate()
        candidate["requested_asset_ids"].append("asset-missing")
        _, _, _, receipt = compile_fixture(candidate=candidate)
        self.assertEqual(receipt["disposition"], "ASSET_PREP_REQUIRED")
        self.assertIn("required_asset_missing:asset-missing", receipt["asset_blockers"])

    def test_future_release_is_trust_hold(self):
        evidence = base_evidence()
        evidence["releases"][0]["released_at"] = ts(NOW + timedelta(minutes=1))
        _, _, _, receipt = compile_fixture(evidence=evidence)
        self.assertEqual(receipt["disposition"], "HOLD")
        self.assertIn("asset_release_after_capture:release-1", receipt["trust_blockers"])
