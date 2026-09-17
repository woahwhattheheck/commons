from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from tools.linden_rfp_26_07_readiness import (
    PACKAGE_BOOL_GATES,
    PORTAL_BOOL_GATES,
    RESPONSE_BOOL_GATES,
    ReadinessError,
    build_report,
    load_json_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "revenue" / "procurement" / "linden-rfp-26-07" / "source_register.json"
STATE_PATH = ROOT / "revenue" / "procurement" / "linden-rfp-26-07" / "readiness_state.json"
GOOD_SHA = "a" * 64


def loaded():
    return json.loads(SOURCE_PATH.read_text()), json.loads(STATE_PATH.read_text())


def promote_package(source, state):
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
    for key in RESPONSE_BOOL_GATES:
        state["response"][key] = True
    return source, state


class LindenRfpReadinessTests(unittest.TestCase):
    def test_current_recovery_is_truthfully_not_submission_ready(self):
        source, state = loaded()
        report = build_report(source, state)
        self.assertFalse(report["submission_ready"])
        self.assertTrue(report["questions_window_open"])
        self.assertTrue(report["proposal_window_open"])
        self.assertIn("package.status", report["submission_blockers"])
        self.assertIn("package.sha256", report["submission_blockers"])
        self.assertFalse(report["portal_registration_ready"])
        self.assertFalse(report["buyer_question_ready"])
        self.assertTrue(all(value is False for value in report["authority"].values()))

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

    def test_verified_package_still_needs_explicit_submission_authority(self):
        source, state = promote_package(*loaded())
        state["authority"]["owner_authorized_pricing_commitment"] = True
        state["authority"]["owner_authorized_submission"] = False
        report = build_report(source, state)
        self.assertFalse(report["submission_ready"])
        self.assertIn("authority.owner_authorized_submission", report["submission_blockers"])

    def test_fully_evidenced_state_can_become_ready_without_changing_report_authority(self):
        source, state = promote_package(*loaded())
        state["authority"]["owner_authorized_pricing_commitment"] = True
        state["authority"]["owner_authorized_submission"] = True
        report = build_report(source, state)
        self.assertTrue(report["submission_ready"])
        self.assertTrue(all(value is False for value in report["authority"].values()))

    def test_question_route_requires_package_owner_and_muse(self):
        source, state = promote_package(*loaded())
        report = build_report(source, state)
        self.assertFalse(report["buyer_question_ready"])
        self.assertIn("authority.owner_authorized_buyer_question", report["buyer_question_blockers"])
        self.assertIn("authority.muse_outbound_clearance", report["buyer_question_blockers"])
        state["authority"]["owner_authorized_buyer_question"] = True
        state["authority"]["muse_outbound_clearance"] = True
        report = build_report(source, state)
        self.assertTrue(report["buyer_question_ready"])

    def test_registration_requires_real_company_authority_facts(self):
        source, state = loaded()
        report = build_report(source, state)
        expected = {
            "portal.legal_company_identity_verified",
            "portal.authorized_site_administrator_verified",
            "portal.authorized_agent_for_vendor_agreement_verified",
            "portal.company_information_truthfulness_attested",
            "authority.owner_authorized_portal_registration",
        }
        self.assertEqual(set(report["portal_registration_blockers"]), expected)
        state["portal"]["legal_company_identity_verified"] = True
        state["portal"]["authorized_site_administrator_verified"] = True
        state["portal"]["authorized_agent_for_vendor_agreement_verified"] = True
        state["portal"]["company_information_truthfulness_attested"] = True
        state["authority"]["owner_authorized_portal_registration"] = True
        report = build_report(source, state)
        self.assertTrue(report["portal_registration_ready"])
        self.assertFalse(report["submission_ready"])

    def test_support_phone_disagreement_remains_explicit(self):
        source, state = loaded()
        report = build_report(source, state)
        self.assertTrue(report["support_phone_conflict_observed"])
        source["support_route_observations"]["status"] = "RESOLVED"
        with self.assertRaises(ReadinessError):
            build_report(source, state)

    def test_duplicate_json_keys_fail_closed(self):
        with self.assertRaises(ReadinessError):
            load_json_bytes(b'{"schema":"a","schema":"b"}')

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
        self.assertIn("proposal_deadline_passed", after_proposal["submission_blockers"])

    def test_naive_deadline_is_rejected(self):
        source, state = loaded()
        source["public_notice_facts"]["questions_deadline"] = "2026-09-21T15:30:00"
        with self.assertRaises(ReadinessError):
            build_report(source, state)


if __name__ == "__main__":
    unittest.main()
