"""Independent acceptance for the single Framer reviewed-source generation.

ZZ-COPPERLINE; no runtime implementation. Run against the original or reviewed
candidate lane; this tests preserved evidence, not new source integration. The baseline qualification digest comes from native
GitHub blob 8e24ca9ea6adb91213180c49972a07585740ed4c, not the candidate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import unittest

BASELINE_QUALIFICATION_SHA256 = "c66135fa1e4e08acf14e6985aaaef339d703d7e9bd9922b5016b72090c8d7630"
BASELINE_PACKET_SHA256 = "13018ee1b2fe14b3b8171acc734e0ea57a52006a5e96f095600e88bcbca63a02"
BASELINE_WORKSHARE_SHA256 = "9825e29c23028dffb23158f7b1db8fb751ba45c0ecedad681764d77bc5ac3b4d"
GATES = (
    "two_lms_platform_implementations", "adult_learning_packaging",
    "start_capacity_2026_10_13", "w9_available", "general_liability_available",
    "professional_liability_available", "cybersecurity_insurance_available",
    "two_relevant_project_examples", "two_prior_client_references",
)
EXPECTED_STATES = ("MISSING", "HOLD", "HOLD", "HOLD", "HOLD", "HOLD", "HOLD", "MISSING", "MISSING")
AUTHORITY = (
    "external_contact_authorized", "submission_authorized", "signature_authorized",
    "contract_acceptance_authorized", "spend_authorized", "payment_authorized",
    "award_or_revenue_asserted",
)


def canonical_digest(value):
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8", "strict")
    return hashlib.sha256(body).hexdigest()



class PreservedEvidenceTests(unittest.TestCase):
    """These tests do not derive their expected truth from candidate constants."""

    lane: Path

    @classmethod
    def setUpClass(cls):
        if not hasattr(cls, "lane"):
            raise RuntimeError("run the script with --lane PATH; no silent default candidate")
        cls.packet = json.loads((cls.lane / "current_packet.json").read_text(encoding="utf-8"))
        cls.ws = json.loads((cls.lane / "partner_workshare.json").read_text(encoding="utf-8"))

    def test_nine_original_qualification_objects_are_preserved_exactly(self):
        selected = {name: self.packet["qualification"][name] for name in GATES}
        self.assertEqual(canonical_digest(selected), BASELINE_QUALIFICATION_SHA256)

    def test_nine_original_states_are_not_upgraded(self):
        self.assertEqual(tuple(self.packet["qualification"][name]["state"] for name in GATES), EXPECTED_STATES)

    def test_source_recovery_is_not_a_new_private_evidence_search(self):
        q = self.packet["qualification"]
        for name in GATES:
            if name != "start_capacity_2026_10_13":
                with self.subTest(name=name):
                    self.assertEqual(q[name]["evidence_refs"], [])
        self.assertEqual(len(q["start_capacity_2026_10_13"]["evidence_refs"]), 1)
        self.assertIn("checked 2026-09-16", q["start_capacity_2026_10_13"]["evidence_refs"][0])

    def test_full_proposal_is_still_unpriced(self):
        for name in ("proposed_total_usd", "year1_license_usd", "post_year1_recurring_usd"):
            with self.subTest(field=name):
                self.assertEqual(type(self.packet["proposal"][name]), int)
                self.assertEqual(self.packet["proposal"][name], 0)

    def test_bidder_responses_still_incomplete(self):
        self.assertIs(self.packet["proposal"]["attachments_complete"], False)

    def test_no_platform_selected(self):
        self.assertTrue(self.packet["proposal"]["platform_recommendation"].startswith("UNSELECTED"))

    def test_qualification_authorities_are_literal_false(self):
        for field in AUTHORITY:
            with self.subTest(field=field):
                self.assertIs(self.packet["authority"][field], False)

    def test_commercial_authorities_are_literal_false(self):
        self.assertGreaterEqual(len(self.ws["authority"]), 7)
        for field, value in self.ws["authority"].items():
            with self.subTest(field=field):
                self.assertIs(value, False)

    def test_existing_price_is_not_acceptance_or_buyer_budget_fit(self):
        self.assertEqual(self.ws["commercial"], {
            "price_usd": 24000,
            "commercial_status": "PROPOSED_NOT_ACCEPTED",
            "buyer_budget_integration_state": "UNRESOLVED_QUALIFIED_PRIME_MUST_INTEGRATE_WITH_60000_CAP",
        })

    def test_single_writer_condition_is_not_external_permission(self):
        self.assertEqual(self.ws["single_writer_gate"], {
            "fresh_opportunity_and_route_census_required": True,
            "muse_dm_clearance_required": True,
            "maximum_external_messages_if_cleared": 1,
        })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", type=Path, required=True,
                        help="Directory containing the candidate packet and workshare JSON")
    args = parser.parse_args()
    PreservedEvidenceTests.lane = args.lane.resolve()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PreservedEvidenceTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() and result.testsRun == 10 and not result.skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
