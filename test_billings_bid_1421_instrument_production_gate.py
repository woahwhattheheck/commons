from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "revenue" / "billings_bid_1421" / "instrument_fixtures"
GATE_PATH = PACK / "production_gate.py"
SPEC = importlib.util.spec_from_file_location("billings_production_gate", GATE_PATH)
assert SPEC and SPEC.loader
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class BillingsInstrumentProductionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.requirements = json.loads(
            (PACK / "production_acceptance_requirements.json").read_text(encoding="utf-8")
        )
        cls.candidate = json.loads(
            (PACK / "production_candidate_evidence.json").read_text(encoding="utf-8")
        )
        cls.source = json.loads(
            (PACK / "production_source_evidence.json").read_text(encoding="utf-8")
        )

    def test_current_candidate_fails_closed(self) -> None:
        result = GATE.evaluate(self.requirements, self.candidate)
        self.assertFalse(result["production_ready"])
        self.assertEqual(result["release_decision"], "NOT_READY")
        self.assertEqual(result["required_gates"], 24)
        self.assertEqual(result["satisfied_gates"], 1)
        self.assertEqual(result["unsatisfied_gates"], 23)

    def test_complete_evidence_can_pass_the_real_gate(self) -> None:
        candidate = copy.deepcopy(self.candidate)
        candidate["release_decision"] = "PRODUCTION_READY"
        for requirement in self.requirements["requirements"]:
            row = candidate["gates"][requirement["gate_id"]]
            row.update(
                {
                    "state": "SATISFIED",
                    "evidence": [
                        {
                            "uri": f"artifact:test/{requirement['gate_id']}",
                            "sha256": "a" * 64,
                            "artifact_type": "test_only_evidence",
                            "verification": "UNIT_TEST",
                        }
                    ],
                    "assertions_passed": requirement["acceptance_assertions"],
                    "verified_by": "unit-test",
                    "verified_at": "2026-08-31T00:00:00Z",
                    "gap": None,
                }
            )
        result = GATE.evaluate(self.requirements, candidate)
        self.assertTrue(result["production_ready"])
        self.assertEqual(result["unsatisfied_gates"], 0)

    def test_false_ready_claim_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.candidate)
        candidate["release_decision"] = "PRODUCTION_READY"
        with self.assertRaisesRegex(GATE.GateInputError, "release_decision must be NOT_READY"):
            GATE.evaluate(self.requirements, candidate)

    def test_satisfied_gate_requires_complete_evidence_and_assertions(self) -> None:
        candidate = copy.deepcopy(self.candidate)
        row = candidate["gates"]["device-inventory-identity"]
        row.update(
            {
                "state": "SATISFIED",
                "evidence": [],
                "assertions_passed": [],
                "verified_by": "tester",
                "verified_at": "2026-08-31T00:00:00Z",
            }
        )
        with self.assertRaisesRegex(GATE.GateInputError, "SATISFIED requires evidence"):
            GATE.evaluate(self.requirements, candidate)

    def test_secret_bearing_keys_are_rejected(self) -> None:
        candidate = copy.deepcopy(self.candidate)
        candidate["gates"]["official-source-traceability"]["evidence"][0]["password"] = (
            "redacted-test-value"
        )
        with self.assertRaisesRegex(GATE.GateInputError, "forbidden secret-bearing key"):
            GATE.evaluate(self.requirements, candidate)

    def test_addenda_models_and_netdmr_layout_are_exact(self) -> None:
        models = [
            row["addendum_1_response_label"]
            for row in self.source["official_targets"]["instrument_models"]
            if row["addendum_1_response_label"]
        ]
        self.assertEqual(
            models,
            [
                "Perkin Elmer PinAAcle 900Z",
                "Metrohm Eco IC",
                "Seivers M5310C",
                "Seal Analytical AQ300",
            ],
        )
        netdmr = self.source["addendum_4_netdmr"]
        self.assertEqual(netdmr["sheet_name"], "Permit= ")
        self.assertEqual(netdmr["used_range"], "A1:AI1")
        self.assertEqual(netdmr["field_count"], 35)
        self.assertEqual(len(netdmr["fields"]), 35)
        addendum_3 = self.source["official_source_set"]["addenda"][2]
        self.assertFalse(addendum_3["macros_executed"])
        self.assertIn("NOT_OPENED", addendum_3["inspection"])


if __name__ == "__main__":
    unittest.main()
