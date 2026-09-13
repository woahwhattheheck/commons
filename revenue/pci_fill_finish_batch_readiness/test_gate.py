from __future__ import annotations

import copy
import unittest

from revenue.pci_fill_finish_batch_readiness.acceptance import AS_OF, VERIFY_AT, base_packet, run_acceptance
from revenue.pci_fill_finish_batch_readiness.gate import ReadinessError, canonical_json, evaluate, normalize_packet, verify_decision


class GateTests(unittest.TestCase):
    def code(self, expected, fn):
        with self.assertRaises(ReadinessError) as ctx:
            fn()
        self.assertEqual(ctx.exception.code, expected)

    def test_acceptance_contract_180(self):
        result = run_acceptance()
        self.assertEqual((result["ready_count"], result["hold_count"]), (144, 36))
        self.assertEqual(set(result["reason_counts"].values()), {6})

    def test_ready_packet(self):
        decision = evaluate(base_packet(1))
        self.assertEqual(decision["status"], "READY")
        self.assertEqual(decision["hold_reasons"], [])
        self.assertTrue(all(v is False for v in decision["authority"].values()))

    def test_recipe_mismatch(self):
        p = base_packet(2); p["recipe"]["scheduled_version"] = "v2"
        self.assertEqual(evaluate(p)["hold_reasons"], ["RECIPE_MISMATCH"])

    def test_unreleased_material(self):
        p = base_packet(3); p["materials"][1]["released"] = False
        self.assertEqual(evaluate(p)["hold_reasons"], ["MATERIAL_UNRELEASED"])

    def test_expired_calibration(self):
        p = base_packet(4); p["equipment"][0]["calibration_valid_until"] = "2026-09-14T11:59:59Z"
        self.assertEqual(evaluate(p)["hold_reasons"], ["CALIBRATION_EXPIRED"])

    def test_environment_hold(self):
        p = base_packet(5); p["environment"]["em_state"] = "HOLD"
        self.assertEqual(evaluate(p)["hold_reasons"], ["ENVIRONMENT_HOLD"])

    def test_inspection_lineage_mismatch(self):
        p = base_packet(6); p["fill_inspection"]["recipe_digest"] = "9" * 64
        self.assertEqual(evaluate(p)["hold_reasons"], ["INSPECTION_LINEAGE_MISMATCH"])

    def test_bom_mismatch(self):
        p = base_packet(7); p["bom"]["staged"][0]["version"] = "v9"
        self.assertEqual(evaluate(p)["hold_reasons"], ["BOM_MISMATCH"])

    def test_multiple_hold_reasons_have_fixed_order(self):
        p = base_packet(8)
        p["recipe"]["scheduled_version"] = "v2"
        p["materials"][0]["released"] = False
        p["bom"]["staged"][0]["version"] = "v9"
        self.assertEqual(evaluate(p)["hold_reasons"], ["RECIPE_MISMATCH", "MATERIAL_UNRELEASED", "BOM_MISMATCH"])

    def test_input_list_order_is_canonicalized(self):
        p = base_packet(9)
        q = copy.deepcopy(p)
        q["materials"].reverse(); q["equipment"].reverse(); q["bom"]["required"].reverse(); q["bom"]["staged"].reverse()
        self.assertEqual(evaluate(p), evaluate(q))

    def test_evaluate_does_not_mutate_input(self):
        p = base_packet(10); before = copy.deepcopy(p)
        evaluate(p)
        self.assertEqual(p, before)

    def test_unknown_packet_field_rejected(self):
        p = base_packet(11); p["note"] = "nope"
        self.code("PACKET_FIELDS", lambda: evaluate(p))

    def test_duplicate_material_lot_rejected(self):
        p = base_packet(12); p["materials"].append(copy.deepcopy(p["materials"][0]))
        self.code("DUPLICATE_MATERIAL_LOT", lambda: evaluate(p))

    def test_duplicate_equipment_rejected(self):
        p = base_packet(13); p["equipment"].append(copy.deepcopy(p["equipment"][0]))
        self.code("DUPLICATE_EQUIPMENT", lambda: evaluate(p))

    def test_duplicate_bom_pair_rejected(self):
        p = base_packet(14); p["bom"]["required"].append(copy.deepcopy(p["bom"]["required"][0]))
        self.code("DUPLICATE_BOM_COMPONENT", lambda: evaluate(p))

    def test_bad_digest_rejected(self):
        p = base_packet(15); p["recipe"]["approved_digest"] = "abc"
        self.code("INVALID_DIGEST", lambda: evaluate(p))

    def test_boolean_is_strict(self):
        p = base_packet(16); p["recipe"]["approved"] = 1
        self.code("BOOLEAN_REQUIRED", lambda: evaluate(p))

    def test_noncanonical_timestamp_rejected(self):
        p = base_packet(17); p["as_of"] = "2026-09-13T12:00:00+00:00"
        self.code("NONCANONICAL_TIMESTAMP", lambda: evaluate(p))

    def test_as_of_after_slot_rejected(self):
        p = base_packet(18); p["as_of"] = "2026-09-15T12:00:00Z"
        self.code("AS_OF_AFTER_PLANNED_SLOT", lambda: evaluate(p))

    def test_future_environment_evidence_rejected(self):
        p = base_packet(19); p["environment"]["captured_at"] = "2026-09-13T12:00:01Z"
        self.code("EVIDENCE_AFTER_AS_OF", lambda: evaluate(p))

    def test_verifier_success_and_freshness(self):
        p = base_packet(20); d = evaluate(p)
        result = verify_decision(p, d, verify_at=VERIFY_AT)
        self.assertTrue(result["valid"] and result["fresh"])
        self.assertEqual(result["age_minutes"], 60)

    def test_verifier_rejects_decision_tamper(self):
        p = base_packet(21); d = evaluate(p); d["status"] = "HOLD"
        self.code("DECISION_MISMATCH", lambda: verify_decision(p, d, verify_at=VERIFY_AT))

    def test_verifier_rejects_source_tamper(self):
        p = base_packet(22); d = evaluate(p); p["materials"][0]["released"] = False
        self.code("DECISION_MISMATCH", lambda: verify_decision(p, d, verify_at=VERIFY_AT))

    def test_verifier_rejects_stale(self):
        p = base_packet(23); d = evaluate(p)
        self.code("DECISION_STALE", lambda: verify_decision(p, d, verify_at="2026-09-15T12:00:01Z", max_age_minutes=1440))

    def test_verifier_rejects_time_travel(self):
        p = base_packet(24); d = evaluate(p)
        self.code("VERIFY_BEFORE_AS_OF", lambda: verify_decision(p, d, verify_at="2026-09-13T11:59:59Z"))

    def test_receipt_is_deterministic(self):
        p = base_packet(25)
        self.assertEqual(canonical_json(evaluate(p)), canonical_json(evaluate(copy.deepcopy(p))))

    def test_normalized_source_has_only_durable_fields(self):
        p = normalize_packet(base_packet(26))
        self.assertNotIn("calibration_valid_until_epoch", canonical_json(p))
        self.assertEqual(p["as_of"], AS_OF)


if __name__ == "__main__":
    unittest.main()
