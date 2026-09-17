import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import validate_scope

BASE = json.loads((HERE / "scope.json").read_text(encoding="utf-8"))


class ScopeTests(unittest.TestCase):
    def test_current_package_is_valid_but_not_release_ready(self):
        self.assertEqual(validate_scope.validate(copy.deepcopy(BASE)), [])
        errors = validate_scope.validate(copy.deepcopy(BASE), release=True)
        self.assertTrue(any("every prime gate" in e for e in errors))
        self.assertTrue(any("all six role pathways" in e for e in errors))
        self.assertTrue(any("document bodies" in e for e in errors))

    def test_deadline_drift_is_rejected(self):
        p = copy.deepcopy(BASE)
        p["tender"]["closes_at_portal"] = "2026-09-17T12:00:00+02:00"
        self.assertTrue(any("provider receipt drift" in e for e in validate_scope.validate(p)))

    def test_query_deadline_drift_is_rejected(self):
        p = copy.deepcopy(BASE)
        p["tender"]["queries_deadline_at_portal"] = "2026-09-13T12:00:00+02:00"
        self.assertTrue(any("provider receipt drift" in e for e in validate_scope.validate(p)))

    def test_document_set_drift_is_rejected(self):
        p = copy.deepcopy(BASE)
        p["tender"]["documents"].pop()
        self.assertTrue(any("filename set drifted" in e for e in validate_scope.validate(p)))

    def test_commercial_state_cannot_be_upgraded_locally(self):
        p = copy.deepcopy(BASE)
        p["commercial_state"] = "ACCEPTED"
        self.assertTrue(any("PROPOSED_NOT_ACCEPTED" in e for e in validate_scope.validate(p)))

    def test_fee_cannot_be_invented(self):
        p = copy.deepcopy(BASE)
        p["fee"] = "USD 25000"
        self.assertTrue(any("TO_BE_AGREED" in e for e in validate_scope.validate(p)))

    def test_outbound_and_submission_authority_cannot_be_granted(self):
        for field in ("buyer_send_allowed", "bid_submission_allowed"):
            p = copy.deepcopy(BASE)
            p["release"][field] = True
            self.assertTrue(validate_scope.validate(p), field)

    def test_boundary_cannot_widen_to_pii_or_certification(self):
        p = copy.deepcopy(BASE)
        p["tjlabs_boundary"]["learner_pii"] = "FULL_RECORDS"
        p["tjlabs_boundary"]["legal_or_compliance_certification"] = True
        errors = validate_scope.validate(p)
        self.assertTrue(any("learner_pii" in e for e in errors))
        self.assertTrue(any("legal_or_compliance_certification" in e for e in errors))

    def test_release_requires_every_gate_and_role_criteria(self):
        p = copy.deepcopy(BASE)
        for key in p["prime_gates"]:
            p["prime_gates"][key] = True
        p["source_receipt"]["controlling_documents_read"] = True
        for i, item in enumerate(p["role_pathways"], 1):
            item["acceptance_criteria"] = [f"prime-approved criterion {i}"]
        self.assertEqual(validate_scope.validate(p, release=True), [])
        p["prime_gates"]["signatory_authority_owned"] = False
        self.assertTrue(validate_scope.validate(p, release=True))


if __name__ == "__main__":
    unittest.main()
