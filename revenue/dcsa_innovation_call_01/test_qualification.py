from .test_support import *  # noqa: F401,F403

class QualificationTests(unittest.TestCase):
    def test_direct_ready_requires_complete_independent_authority(self):
        report = compile_at()
        self.assertEqual(report["state"], "DIRECT_READY")
        self.assertTrue(report["current_work_authorized"])
        self.assertFalse(report["external_submission_authorized"])

    def test_missing_fcl_routes_to_teaming(self):
        s = source()
        a = authority(s, direct=False, team=True)
        report = compile_at(source_value=s, authority_value=a, floor_value=floor(a))
        self.assertEqual(report["state"], "TEAMING_REQUIRED")
        self.assertFalse(report["evidence_summary"]["direct_eligibility_verified"])

    def test_missing_team_eligibility_holds_when_direct_missing(self):
        s = source()
        a = authority(s, direct=False, team=False)
        report = compile_at(source_value=s, authority_value=a, floor_value=floor(a))
        self.assertEqual(report["state"], "HOLD")
        self.assertIn("TEAMING_PRIME_ELIGIBILITY_NOT_VERIFIED", report["blockers"])

    def test_incomplete_source_bytes_hold(self):
        s = source(complete=False)
        a = authority(s)
        report = compile_at(source_value=s, authority_value=a, floor_value=floor(a))
        self.assertEqual(report["state"], "HOLD")
        self.assertIn("CONTROLLING_SOURCE_BYTES_INCOMPLETE", report["blockers"])

    def test_stale_source_holds(self):
        s = source(observed_at="2026-09-12T04:45:00Z")
        a = authority(s)
        report = compile_at(source_value=s, authority_value=a, floor_value=floor(a))
        self.assertIn("SOURCE_OBSERVATION_STALE", report["blockers"])

    def test_future_source_holds(self):
        s = source(observed_at="2026-09-14T06:00:00Z")
        a = authority(s)
        report = compile_at(source_value=s, authority_value=a, floor_value=floor(a))
        self.assertIn("SOURCE_OBSERVED_IN_FUTURE", report["blockers"])

    def test_authority_subject_transplant_holds(self):
        s = source()
        a = authority(s, subject_id="other-subject")
        report = compile_at(source_value=s, authority_value=a, floor_value=floor(a))
        self.assertIn("AUTHORITY_SUBJECT_MISMATCH", report["blockers"])

    def test_authority_source_transplant_holds(self):
        s = source()
        a = authority(s)
        a["source_generation_sha256"] = "a" * 64
        report = compile_at(source_value=s, authority_value=a, floor_value=floor(a))
        self.assertIn("AUTHORITY_SOURCE_GENERATION_MISMATCH", report["blockers"])

    def test_authority_floor_digest_mismatch_holds(self):
        s = source()
        a = authority(s)
        f = floor(a)
        f["authority_sha256"] = "b" * 64
        report = compile_at(source_value=s, authority_value=a, floor_value=f)
        self.assertIn("AUTHORITY_DIGEST_NOT_CURRENT", report["blockers"])

    def test_authority_floor_generation_mismatch_holds(self):
        s = source()
        a = authority(s)
        f = floor(a)
        f["generation"] += 1
        report = compile_at(source_value=s, authority_value=a, floor_value=f)
        self.assertIn("AUTHORITY_GENERATION_NOT_CURRENT", report["blockers"])

    def test_future_authority_holds(self):
        s = source()
        a = authority(s, issued_at="2026-09-14T06:00:00Z", valid_until="2026-09-14T12:00:00Z")
        report = compile_at(source_value=s, authority_value=a, floor_value=floor(a))
        self.assertIn("AUTHORITY_ISSUED_IN_FUTURE", report["blockers"])

    def test_expired_authority_holds(self):
        s = source()
        a = authority(s, issued_at="2026-09-13T04:00:00Z", valid_until="2026-09-14T04:59:59Z")
        report = compile_at(source_value=s, authority_value=a, floor_value=floor(a))
        self.assertIn("AUTHORITY_EXPIRED", report["blockers"])

    def test_missing_capability_evidence_holds(self):
        s = source()
        a = authority(s)
        a["capability_evidence"][0].update(evidence("UNVERIFIED"))
        report = compile_at(source_value=s, authority_value=a, floor_value=floor(a))
        self.assertIn("CAPABILITY_EVIDENCE_INCOMPLETE", report["blockers"])

    def test_missing_capability_declaration_holds(self):
        c = candidate()
        c["declared_capabilities"].pop()
        s = source()
        a = authority(s)
        report = compile_at(c, s, a, floor(a))
        self.assertIn("REQUIRED_CAPABILITY_DECLARATIONS_INCOMPLETE", report["blockers"])

    def test_rom_requires_candidate_and_owner_approval(self):
        c = candidate()
        c["rom_state"] = "OWNER_DECISION_REQUIRED"
        report = compile_at(candidate_value=c)
        self.assertIn("ROM_OWNER_APPROVAL_REQUIRED", report["blockers"])

    def test_concept_deadline_closure_holds(self):
        report = compile_at(now=gate.CONCEPT_DEADLINE)
        self.assertEqual(report["state"], "HOLD")
        self.assertIn("CONCEPT_PAPER_DEADLINE_CLOSED", report["blockers"])

    def test_question_window_changes_at_exact_deadline(self):
        before = compile_at(now=gate.QUESTION_DEADLINE - dt.timedelta(seconds=1))
        at = compile_at(now=gate.QUESTION_DEADLINE)
        self.assertEqual(before["question_window"], "OPEN")
        self.assertEqual(at["question_window"], "CLOSED")

    def test_historical_replay_never_mints_current_state(self):
        report = compile_at(mode="HISTORICAL_INTEGRITY_ONLY")
        self.assertEqual(report["state"], "HOLD")
        self.assertEqual(report["historical_route_projection"], "DIRECT_READY")
        self.assertFalse(report["current_work_authorized"])

    def test_receipt_tamper_rejected(self):
        report = compile_at()
        report["state"] = "TEAMING_REQUIRED"
        with self.assertRaises(strict.ValidationError):
            gate.verify_report_shape(report)

    def test_report_cannot_grant_external_action_after_reseal(self):
        report = compile_at()
        report["external_submission_authorized"] = True
        report["receipt_sha256"] = hashlib.sha256(
            strict.canonical_json_bytes({**report, "receipt_sha256": ""})
        ).hexdigest()
        with self.assertRaises(strict.ValidationError):
            gate.verify_report_shape(report)

    def test_deterministic_permutation(self):
        c1 = candidate()
        c2 = copy.deepcopy(c1)
        for key in ("declared_capabilities", "background_ip", "third_party_dependencies", "risks", "question_drafts"):
            c2[key].reverse()
        self.assertEqual(compile_at(candidate_value=c1), compile_at(candidate_value=c2))

