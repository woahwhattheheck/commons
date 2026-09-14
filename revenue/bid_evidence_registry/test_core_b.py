from __future__ import annotations

import unittest

from revenue.bid_evidence_registry.engine import RegistryError, compile_registry
from revenue.bid_evidence_registry.test_support import H, H2, evidence, payload, req

class CoreBTests(unittest.TestCase):
    def state(self, p):
        return compile_registry(p)["requirements"][0]["state"]

    def test_financial_class_mismatch_is_missing_not_substituted(self):
        ev = evidence("fin-reviewed", "FINANCIAL_STATEMENT", metadata={"financial_class": "REVIEWED"})
        p = payload([ev], [req("r", "FINANCIAL_STATEMENT", financial="AUDITED")])
        self.assertEqual(self.state(p), "MISSING")

    def test_financial_exact_class_passes(self):
        ev = evidence("fin-reviewed", "FINANCIAL_STATEMENT", metadata={"financial_class": "REVIEWED"})
        p = payload([ev], [req("r", "FINANCIAL_STATEMENT", financial="REVIEWED")])
        self.assertEqual(self.state(p), "CURRENT_VERIFIED")

    def test_entity_transplant_cannot_green(self):
        ev = evidence("w9-other", "W9", entity_id="other-company")
        self.assertEqual(self.state(payload([ev], [req("r", "W9")])), "MISSING")

    def test_opportunity_only_not_reused_globally(self):
        ev = evidence("w9-op", "W9", reuse_scope="OPPORTUNITY_ONLY", opportunity_ids=["usac-it-26-139"])
        self.assertEqual(self.state(payload([ev], [req("r", "W9", opportunity="wrf-5417")])), "MISSING")

    def test_opportunity_only_exact_scope_passes(self):
        ev = evidence("w9-op", "W9", reuse_scope="OPPORTUNITY_ONLY", opportunity_ids=["usac-it-26-139"])
        self.assertEqual(self.state(payload([ev], [req("r", "W9", opportunity="usac-it-26-139")])), "CURRENT_VERIFIED")

    def test_submission_award_stage_separation(self):
        ev = evidence("coi-award", "INSURANCE_COI", stages=["AWARD"])
        p = payload([ev], [req("r", "INSURANCE_COI", stage="SUBMISSION")])
        self.assertEqual(self.state(p), "MISSING")

    def test_award_requirement_can_consume_award_evidence(self):
        ev = evidence("coi-award", "INSURANCE_COI", stages=["AWARD"])
        p = payload([ev], [req("r", "INSURANCE_COI", stage="AWARD")])
        self.assertEqual(self.state(p), "CURRENT_VERIFIED")
