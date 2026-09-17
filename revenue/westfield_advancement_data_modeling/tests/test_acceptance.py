import copy
import pathlib
import sys
import unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from acceptance import ContractError, compile_acceptance, load_strict_json, make_receipt, verify_receipt

MANIFEST = {
    "schema": "advancement-model-acceptance/v1",
    "opportunity": {"buyer": "Westfield State University", "solicitation": "RFP #2027-002 Advancement Data Modeling", "deadline": "2026-09-25", "submission_route": "Bonfire/Euna"},
    "commercial": {"role": "paid_subcontract_workshare", "state": "PROPOSED_NOT_ACCEPTED", "pricing_basis": "scope-and-deliverables to be agreed with qualified prime before any work starts"},
    "sources": [
        {"kind": "buyer_official", "url": "https://www.westfield.ma.edu/offices/open-general-bids", "note": "Official university open-bids index."},
        {"kind": "partner_public", "url": "https://khowconsulting.com/", "note": "Public advancement strategy and analytics profile; not evidence of pursuit."},
    ],
    "authority": {"prime_vendor_confirmed": False, "buyer_approved": False, "references_verified": False, "production_data_access": False, "award_received": False, "payment_received": False, "revenue_recognized": False},
    "workshare": {
        "deliverables": ["source-to-feature provenance ledger", "entity and household duplicate-control report", "time-anchored training and holdout contract", "calibration and ranked-lift acceptance report", "reproducible model-card and handoff receipt"],
        "exclusions": ["buyer portal submission", "prime responsibility", "reference ownership", "production-data custody", "campaign strategy representation"],
    },
    "model_acceptance": {
        "entity_key_policy": "split and score only after constituent/household grouping prevents cross-fold identity leakage",
        "time_anchor_policy": "all features must be knowable as of the scoring cutoff; outcomes occur strictly after cutoff",
        "required_checks": ["source_provenance", "entity_deduplication", "household_leakage", "temporal_leakage", "target_window", "calibration", "ranking_lift", "reproducible_handoff"],
        "metrics": {"calibration": "brier_and_reliability", "ranking": "lift_at_k", "evaluation_split": "temporal_holdout"},
        "handoff_artifacts": ["data dictionary/provenance map", "split manifest", "metric definitions", "model/config digest", "acceptance exception log"],
    },
}

class AcceptanceTests(unittest.TestCase):
    def test_good_manifest_compiles_and_receipt_verifies(self):
        plan = compile_acceptance(copy.deepcopy(MANIFEST))
        self.assertEqual(plan["commercial"]["state"], "PROPOSED_NOT_ACCEPTED")
        self.assertEqual(plan["acceptance_plan"]["metrics"]["evaluation_split"], "temporal_holdout")
        self.assertTrue(verify_receipt(MANIFEST, make_receipt(MANIFEST)))

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(ContractError):
            load_strict_json('{"schema":"a","schema":"b"}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(ContractError):
            load_strict_json('{"x":NaN}')

    def test_authority_claim_cannot_be_promoted(self):
        for key in MANIFEST["authority"]:
            bad = copy.deepcopy(MANIFEST)
            bad["authority"][key] = True
            with self.subTest(key=key), self.assertRaises(ContractError):
                compile_acceptance(bad)

    def test_temporal_holdout_required(self):
        bad = copy.deepcopy(MANIFEST)
        bad["model_acceptance"]["metrics"]["evaluation_split"] = "random_split"
        with self.assertRaises(ContractError):
            compile_acceptance(bad)

    def test_required_leakage_check_cannot_be_removed(self):
        bad = copy.deepcopy(MANIFEST)
        bad["model_acceptance"]["required_checks"].remove("household_leakage")
        with self.assertRaises(ContractError):
            compile_acceptance(bad)

    def test_binding_price_not_admitted(self):
        bad = copy.deepcopy(MANIFEST)
        bad["commercial"]["pricing_basis"] = "$12,000 fixed"
        with self.assertRaises(ContractError):
            compile_acceptance(bad)

    def test_tampered_receipt_rejected(self):
        receipt = make_receipt(MANIFEST)
        receipt["plan_sha256"] = "0" * 64
        self.assertFalse(verify_receipt(MANIFEST, receipt))

if __name__ == "__main__":
    unittest.main()
