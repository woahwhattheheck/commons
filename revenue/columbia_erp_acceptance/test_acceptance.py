import copy
import math
import unittest

from revenue.columbia_erp_acceptance.acceptance import (
    AcceptanceError,
    ETL_PHASES,
    build_receipt,
    reconcile_records,
    verify_receipt,
)


def phase_evidence():
    return {phase: f"sha256:{phase}-evidence" for phase in ETL_PHASES}


def interfaces():
    return [
        {
            "name": "Dayforce payroll",
            "status": "PASS",
            "evidence_id": "sha256:dayforce",
        },
        {
            "name": "Club Automation",
            "status": "PASS",
            "evidence_id": "sha256:club",
        },
    ]


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.source = [
            {"key": "GL-100", "amount": "10.00", "account": "1000", "version": 3},
            {"key": "GL-200", "amount": "20.00", "account": "2000", "version": 1},
        ]
        self.target = list(reversed(copy.deepcopy(self.source)))

    def test_happy_receipt_is_deterministic_across_record_and_interface_order(self):
        a = build_receipt(
            self.source,
            self.target,
            phase_evidence(),
            interfaces(),
            scope_id="ledger-wave-1",
        )
        b = build_receipt(
            list(reversed(self.source)),
            list(reversed(self.target)),
            phase_evidence(),
            list(reversed(interfaces())),
            scope_id="ledger-wave-1",
        )
        self.assertEqual(a, b)
        self.assertTrue(verify_receipt(a))
        self.assertEqual(a["payload"]["reconciliation"]["status"], "PASS")

    def test_missing_unexpected_and_field_mismatch_hold(self):
        target = [
            {"key": "GL-100", "amount": "11.00", "account": "1000", "version": 3},
            {"key": "GL-999", "amount": "9.00", "account": "9999", "version": 1},
        ]
        result = reconcile_records(self.source, target)
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(result["missing_target_keys"], ["GL-200"])
        self.assertEqual(result["unexpected_target_keys"], ["GL-999"])
        self.assertEqual(result["field_mismatches"][0]["field"], "amount")
        with self.assertRaisesRegex(AcceptanceError, "blocking exceptions"):
            build_receipt(self.source, target, phase_evidence(), interfaces())

    def test_duplicate_and_conflicting_duplicate_are_rejected(self):
        same_duplicate = self.source + [copy.deepcopy(self.source[0])]
        with self.assertRaisesRegex(AcceptanceError, "duplicate key"):
            reconcile_records(same_duplicate, self.target)
        conflict = self.source + [{**self.source[0], "amount": "99.00"}]
        with self.assertRaisesRegex(AcceptanceError, "conflicting duplicate"):
            reconcile_records(conflict, self.target)

    def test_nonfinite_values_fail_closed(self):
        bad = copy.deepcopy(self.source)
        bad[0]["amount"] = math.nan
        with self.assertRaisesRegex(AcceptanceError, "non-finite"):
            reconcile_records(bad, self.target)

    def test_incomplete_etl_phase_evidence_cannot_issue_receipt(self):
        evidence = phase_evidence()
        evidence.pop("validate")
        with self.assertRaisesRegex(AcceptanceError, "missing ETL evidence: validate"):
            build_receipt(self.source, self.target, evidence, interfaces())

    def test_failed_or_duplicate_interface_cannot_issue_receipt(self):
        failed = interfaces()
        failed[0]["status"] = "HOLD"
        with self.assertRaisesRegex(AcceptanceError, "not PASS"):
            build_receipt(self.source, self.target, phase_evidence(), failed)
        duplicate = interfaces() + [interfaces()[0]]
        with self.assertRaisesRegex(AcceptanceError, "duplicate interface"):
            build_receipt(self.source, self.target, phase_evidence(), duplicate)

    def test_receipt_tamper_is_detected(self):
        receipt = build_receipt(
            self.source, self.target, phase_evidence(), interfaces()
        )
        receipt["payload"]["reconciliation"]["source_count"] = 999
        self.assertFalse(verify_receipt(receipt))

    def test_compare_fields_can_bound_the_acceptance_contract(self):
        target = copy.deepcopy(self.target)
        target[0]["noncontract_note"] = "target-only annotation"
        result = reconcile_records(
            self.source,
            target,
            compare_fields=["amount", "account", "version"],
        )
        self.assertEqual(result["status"], "PASS")

    def test_malformed_compare_fields_fail_closed_with_acceptance_error(self):
        with self.assertRaisesRegex(AcceptanceError, "sequence of field names"):
            reconcile_records(self.source, self.target, compare_fields="amount")
        with self.assertRaisesRegex(AcceptanceError, "invalid field name"):
            reconcile_records(self.source, self.target, compare_fields=["amount", 7])

    def test_non_string_phase_key_fails_closed_with_acceptance_error(self):
        evidence = phase_evidence()
        evidence[7] = "sha256:bad-key"
        with self.assertRaisesRegex(AcceptanceError, "phase evidence keys must be strings"):
            build_receipt(self.source, self.target, evidence, interfaces())

    def test_invalid_key_field_fails_closed_with_acceptance_error(self):
        with self.assertRaisesRegex(AcceptanceError, "key_field must be a non-empty string"):
            reconcile_records(self.source, self.target, key_field="")
        with self.assertRaisesRegex(AcceptanceError, "key_field must be a non-empty string"):
            reconcile_records(self.source, self.target, key_field=7)


if __name__ == "__main__":
    unittest.main()
