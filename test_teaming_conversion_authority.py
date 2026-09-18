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

    def test_current_authority_ignores_post_import_rebinding(self):
        import revenue.teaming_conversion.control as control
        import revenue.teaming_conversion.policy as policy_module
        import revenue.teaming_conversion.trusted_roots as roots_module

        candidate = canonical_bytes(base_candidate())
        evidence_bytes, attacker_roots = build_roots(base_evidence())
        attacker_policy = policy_module.policy_dict()
        attacker_policy["max_reply_age_seconds"] = 10**9

        with mock.patch.object(
            control, "load_current_roots_bytes", return_value=attacker_roots
        ), mock.patch.object(
            control, "_utc_now", return_value=NOW
        ), mock.patch.object(
            control, "policy_dict", return_value=attacker_policy
        ), mock.patch.object(
            control, "POLICY_SHA256", "f" * 64
        ), mock.patch.object(
            roots_module, "_ROOTS_PATH", Path("/attacker/roots.json")
        ), mock.patch.object(
            roots_module.os,
            "open",
            side_effect=AssertionError("CURRENT loader followed rebound os.open"),
        ):
            receipt = compile_current_bytes(candidate, evidence_bytes)

        self.assertEqual(receipt["mode"], CURRENT_MODE)
        self.assertEqual(receipt["disposition"], "HOLD")
        self.assertIn("trusted_root_missing", receipt["trust_blockers"])
        self.assertEqual(receipt["safe_assets"], [])
        self.assertEqual(receipt["safe_commercial_facts"], [])

    def test_current_exec_boundary_ignores_second_order_helper_rebinding(self):
        import revenue.teaming_conversion.assets as assets_module
        import revenue.teaming_conversion.control as control
        import revenue.teaming_conversion.parse as parse_module

        candidate = canonical_bytes(base_candidate())
        evidence_bytes, _ = build_roots(base_evidence())
        receipt = compile_current_bytes(candidate, evidence_bytes)
        receipt_bytes = canonical_bytes(receipt)

        with mock.patch.object(
            parse_module,
            "require_list",
            side_effect=AssertionError("CURRENT followed rebound parse.require_list"),
        ), mock.patch.object(
            assets_module,
            "asset_descriptor",
            side_effect=AssertionError("CURRENT followed rebound asset_descriptor"),
        ), mock.patch.object(
            control,
            "_compile_at",
            side_effect=AssertionError("CURRENT used caller interpreter compiler"),
        ), mock.patch.object(
            control,
            "_CURRENT_RPC",
            side_effect=AssertionError("CURRENT late-resolved transport"),
        ), mock.patch.object(
            control.os,
            "posix_spawn",
            side_effect=AssertionError("CURRENT late-resolved os.posix_spawn"),
        ), mock.patch.object(
            control.marshal,
            "loads",
            side_effect=AssertionError("CURRENT late-resolved marshal.loads"),
        ):
            rebound_receipt = compile_current_bytes(candidate, evidence_bytes)
            verification = verify_current_bytes(candidate, evidence_bytes, receipt_bytes)

        self.assertEqual(rebound_receipt["disposition"], "HOLD")
        self.assertIn("trusted_root_missing", rebound_receipt["trust_blockers"])
        self.assertEqual(rebound_receipt["safe_assets"], [])
        self.assertEqual(rebound_receipt["safe_commercial_facts"], [])
        self.assertTrue(verification["integrity_valid"])
        self.assertTrue(verification["current_valid"])
        self.assertEqual(verification["current_disposition"], "HOLD")

    def test_policy_helpers_cannot_rebind_transitive_evaluation(self):
        import revenue.teaming_conversion.assets as assets_module
        import revenue.teaming_conversion.control as control
        import revenue.teaming_conversion.evidence as evidence_module
        import revenue.teaming_conversion.policy as policy_module
        import revenue.teaming_conversion.qualification as qualification_module

        candidate, evidence, roots, _ = compile_fixture()
        fake_policy = policy_module.policy_dict()
        fake_policy.update(
            {
                "max_future_skew_seconds": 0,
                "max_reply_age_seconds": 0,
                "max_source_age_seconds": 0,
                "max_current_receipt_age_seconds": 0,
                "required_clear_gate_ids": ["attacker-gate"],
                "required_commitment_ids": ["attacker-commitment"],
            }
        )
        with mock.patch.object(
            control, "policy_dict", return_value=fake_policy
        ), mock.patch.object(
            control, "POLICY_SHA256", "f" * 64
        ), mock.patch.object(
            evidence_module, "policy_dict", return_value=fake_policy
        ), mock.patch.object(
            evidence_module, "POLICY_SHA256", "f" * 64
        ), mock.patch.object(
            assets_module, "policy_dict", return_value=fake_policy
        ), mock.patch.object(
            qualification_module, "policy_dict", return_value=fake_policy
        ):
            receipt = compile_historical_bytes(
                candidate, evidence, roots, evaluated_at=NOW
            )

        self.assertEqual(receipt["disposition"], "FOLLOWUP_READY")
        self.assertEqual(receipt["policy"]["sha256"], POLICY_SHA256)
        self.assertEqual(receipt["qualification_blockers"], [])

    def test_current_public_signatures_expose_no_authority_injection(self):
        import inspect

        self.assertEqual(
            list(inspect.signature(compile_current_bytes).parameters),
            ["candidate_bytes", "evidence_bytes"],
        )
        self.assertEqual(
            list(inspect.signature(verify_current_bytes).parameters),
            ["candidate_bytes", "evidence_bytes", "receipt_bytes"],
        )

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
