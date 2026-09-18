from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from tools.linden_rfp_26_07_readiness import (
    AUTHORITY_KEYS,
    MUSE_AUTH_BLOCKER,
    OWNER_AUTH_BLOCKER,
    PACKAGE_AUTH_BLOCKER,
    PACKAGE_BOOL_GATES,
    PORTAL_BOOL_GATES,
    RESPONSE_BOOL_GATES,
    ReadinessError,
    build_report,
    load_json_bytes,
    verify_report,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "revenue" / "procurement" / "linden-rfp-26-07" / "source_register.json"
STATE_PATH = ROOT / "revenue" / "procurement" / "linden-rfp-26-07" / "readiness_state.json"
GOOD_SHA = "a" * 64


def loaded():
    return json.loads(SOURCE_PATH.read_text()), json.loads(STATE_PATH.read_text())


def promote_local_claims(source, state):
    """Make every caller-controlled readiness claim positive.

    This deliberately does NOT create authenticated provider evidence. The
    resulting report may become candidate-ready, but terminal readiness must
    stay false.
    """
    source = copy.deepcopy(source)
    state = copy.deepcopy(state)
    for row in source["sources"]:
        if row["source_id"] == "controlling_rfp_package_26_07":
            row["status"] = "VERIFIED_PACKAGE"
            row["sha256"] = GOOD_SHA
    for key in source["package_only_truth"]:
        source["package_only_truth"][key] = "VERIFIED_PACKAGE"
    state["package"]["status"] = "VERIFIED_PACKAGE"
    state["package"]["sha256"] = GOOD_SHA
    for key in PACKAGE_BOOL_GATES:
        state["package"][key] = True
    for key in PORTAL_BOOL_GATES:
        state["portal"][key] = True
    state["portal"]["support_route_conflict_resolved"] = True
    for key in RESPONSE_BOOL_GATES:
        state["response"][key] = True
    for key in AUTHORITY_KEYS:
        state["authority"][key] = True
    return source, state


class LindenRfpReadinessTests(unittest.TestCase):
    def test_current_recovery_is_truthfully_not_submission_ready(self):
        source, state = loaded()
        report = build_report(source, state)
        self.assertFalse(report["submission_ready"])
        self.assertFalse(report["submission_candidate_ready"])
        self.assertTrue(report["questions_window_open"])
        self.assertTrue(report["proposal_window_open"])
        self.assertIn("package.status", report["submission_candidate_blockers"])
        self.assertIn("package.sha256", report["submission_candidate_blockers"])
        self.assertIn(PACKAGE_AUTH_BLOCKER, report["submission_blockers"])
        self.assertFalse(report["portal_registration_ready"])
        self.assertFalse(report["buyer_question_ready"])
        self.assertTrue(all(value is False for value in report["authority"].values()))
        self.assertFalse(report["receipt"]["provider_authenticated_package"])
        self.assertFalse(report["receipt"]["provider_authenticated_owner_authorization"])
        self.assertFalse(report["receipt"]["provider_authenticated_muse_election"])
        self.assertTrue(verify_report(source, state, report))

    def test_public_notice_cannot_be_promoted_to_package_truth(self):
        source, state = loaded()
        source["package_only_truth"]["scope_detail"] = "VERIFIED_FROM_PUBLIC_NOTICE"
        with self.assertRaises(ReadinessError):
            build_report(source, state)

    def test_missing_package_cannot_claim_response_completion(self):
        source, state = loaded()
        state["response"]["technical_response_complete"] = True
        with self.assertRaises(ReadinessError):
            build_report(source, state)

    def test_missing_package_cannot_claim_extracted_requirements(self):
        source, state = loaded()
        state["package"]["requirements_extracted"] = True
        with self.assertRaises(ReadinessError):
            build_report(source, state)

    def test_caller_minted_package_and_authority_can_only_make_candidate_ready(self):
        source, state = promote_local_claims(*loaded())
        report = build_report(source, state)
        self.assertTrue(report["submission_candidate_ready"])
        self.assertEqual(report["submission_candidate_blockers"], [])
        self.assertFalse(report["submission_ready"])
        self.assertIn(PACKAGE_AUTH_BLOCKER, report["submission_blockers"])
        self.assertIn(OWNER_AUTH_BLOCKER, report["submission_blockers"])

    def test_caller_minted_muse_clearance_cannot_make_buyer_question_terminal_ready(self):
        source, state = promote_local_claims(*loaded())
        report = build_report(source, state)
        self.assertTrue(report["buyer_question_candidate_ready"])
        self.assertFalse(report["buyer_question_ready"])
        self.assertIn(PACKAGE_AUTH_BLOCKER, report["buyer_question_blockers"])
        self.assertIn(MUSE_AUTH_BLOCKER, report["buyer_question_blockers"])
        self.assertIn(OWNER_AUTH_BLOCKER, report["buyer_question_blockers"])

    def test_caller_minted_registration_authority_is_candidate_only(self):
        source, state = loaded()
        for key in (
            "legal_company_identity_verified",
            "authorized_site_administrator_verified",
            "authorized_agent_for_vendor_agreement_verified",
            "company_information_truthfulness_attested",
        ):
            state["portal"][key] = True
        state["authority"]["owner_authorized_portal_registration"] = True
        report = build_report(source, state)
        self.assertTrue(report["portal_registration_candidate_ready"])
        self.assertFalse(report["portal_registration_ready"])
        self.assertIn(OWNER_AUTH_BLOCKER, report["portal_registration_blockers"])

    def test_submission_authority_still_required_for_candidate_readiness(self):
        source, state = promote_local_claims(*loaded())
        state["authority"]["owner_authorized_submission"] = False
        report = build_report(source, state)
        self.assertFalse(report["submission_candidate_ready"])
        self.assertIn(
            "authority.owner_authorized_submission",
            report["submission_candidate_blockers"],
        )
        self.assertFalse(report["submission_ready"])

    def test_support_phone_disagreement_remains_explicit(self):
        source, state = loaded()
        report = build_report(source, state)
        self.assertTrue(report["support_phone_conflict_observed"])
        source["support_route_observations"]["status"] = "RESOLVED"
        with self.assertRaises(ReadinessError):
            build_report(source, state)

    def test_deadlines_are_code_owned_not_caller_extendable(self):
        source, state = loaded()
        source["public_notice_facts"]["proposal_deadline"] = "2036-10-09T14:30:00-04:00"
        state["known_deadlines"]["proposal_deadline"] = "2036-10-09T14:30:00-04:00"
        with self.assertRaises(ReadinessError):
            build_report(source, state)

    def test_deadline_override_closes_windows_without_mutating_source(self):
        source, state = loaded()
        at_question_deadline = build_report(
            source,
            state,
            as_of_override="2026-09-21T15:30:00-04:00",
        )
        self.assertFalse(at_question_deadline["questions_window_open"])
        self.assertTrue(at_question_deadline["proposal_window_open"])
        after_proposal = build_report(
            source,
            state,
            as_of_override="2026-10-09T14:30:00-04:00",
        )
        self.assertFalse(after_proposal["proposal_window_open"])
        self.assertIn(
            "proposal_deadline_passed",
            after_proposal["submission_candidate_blockers"],
        )
        self.assertFalse(after_proposal["submission_ready"])

    def test_naive_as_of_override_is_rejected(self):
        source, state = loaded()
        with self.assertRaises(ReadinessError):
            build_report(source, state, as_of_override="2026-09-21T15:30:00")

    def test_unknown_authority_key_rejected(self):
        source, state = loaded()
        state["authority"]["self_authorized_send"] = True
        with self.assertRaises(ReadinessError):
            build_report(source, state)

    def test_bool_int_confusion_rejected(self):
        source, state = loaded()
        state["package"]["requirements_extracted"] = 1
        with self.assertRaises(ReadinessError):
            build_report(source, state)

    def test_duplicate_json_keys_fail_closed(self):
        with self.assertRaises(ReadinessError):
            load_json_bytes(b'{"schema":"a","schema":"b"}')

    def test_oversize_json_fails_before_decode(self):
        with self.assertRaises(ReadinessError):
            load_json_bytes(b" " * 1_048_577)

    def test_receipt_is_deterministic_and_recompile_verified(self):
        source, state = loaded()
        first = build_report(source, state)
        second = build_report(source, state)
        self.assertEqual(first, second)
        self.assertTrue(verify_report(source, state, first))
        tampered = copy.deepcopy(first)
        tampered["submission_ready"] = True
        self.assertFalse(verify_report(source, state, tampered))
        resealed = copy.deepcopy(first)
        resealed["receipt"]["report_core_sha256"] = "b" * 64
        self.assertFalse(verify_report(source, state, resealed))


if __name__ == "__main__":
    unittest.main()
