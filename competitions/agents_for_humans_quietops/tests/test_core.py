import copy
import json
import unittest
from decimal import Decimal

from quietops.core import (
    QuietOpsError,
    decide,
    digest,
    make_receipt,
    process_offline,
    process_queue,
    strict_json_loads,
    verify_receipt,
)

H1 = "1" * 64
H2 = "2" * 64


def base(kind="RECONCILE_RECORDS"):
    return {
        "task_id": "task-001",
        "event_id": "event-001",
        "kind": kind,
        "action": "reconcile expected and observed totals",
        "evidence": [{"ref": "snapshot://ledger/2026-09", "sha256": H1}],
        "confidence_bps": 10000,
        "ambiguous_evidence": False,
        "external_effect": False,
        "context": {"expected_minor": 10000, "observed_minor": 10000, "currency": "USD"},
    }


class QuietOpsTests(unittest.TestCase):
    def test_safe_reconciliation_is_autonomous(self):
        d = decide(base())
        self.assertTrue(d.autonomous)
        self.assertEqual(d.authority, "AUTONOMOUS_REVERSIBLE")

    def test_receipt_verifies(self):
        out = process_offline(base())
        self.assertTrue(verify_receipt(base(), out["receipt"]))

    def test_receipt_tamper_fails(self):
        out = process_offline(base())
        receipt = copy.deepcopy(out["receipt"])
        receipt["result"]["variance_minor"] = 1
        self.assertFalse(verify_receipt(decide(base()), receipt))

    def test_input_generation_tamper_fails(self):
        out = process_offline(base())
        changed = base()
        changed["context"]["observed_minor"] = 9999
        self.assertFalse(verify_receipt(changed, out["receipt"]))

    def test_contact_requires_human(self):
        x = base("CONTACT_CUSTOMER")
        x.pop("context")
        d = decide(x)
        self.assertTrue(d.human_decision_required)
        self.assertFalse(process_offline(x)["receipt"])

    def test_vendor_contact_requires_human(self):
        x = base("CONTACT_VENDOR"); x.pop("context")
        self.assertFalse(decide(x).autonomous)

    def test_payment_requires_human(self):
        x = base("MOVE_MONEY"); x.pop("context")
        self.assertFalse(decide(x).autonomous)

    def test_price_requires_human(self):
        x = base("PRICE_COMMITMENT"); x.pop("context")
        self.assertFalse(decide(x).autonomous)

    def test_legal_requires_human(self):
        x = base("LEGAL_INTERPRETATION"); x.pop("context")
        self.assertFalse(decide(x).autonomous)

    def test_unknown_kind_fails_closed(self):
        x = base("MAGIC_ACTION"); x.pop("context")
        self.assertFalse(decide(x).autonomous)

    def test_nonzero_money_marks_human_even_safe_kind(self):
        x = base(); x["amount_minor"] = 1
        self.assertFalse(decide(x).autonomous)

    def test_zero_amount_does_not_change_safe_authority(self):
        x = base(); x["amount_minor"] = 0
        self.assertTrue(decide(x).autonomous)

    def test_external_effect_marks_human(self):
        x = base(); x["external_effect"] = True
        self.assertFalse(decide(x).autonomous)

    def test_ambiguity_marks_human(self):
        x = base(); x["ambiguous_evidence"] = True
        self.assertFalse(decide(x).autonomous)

    def test_low_confidence_marks_human(self):
        x = base(); x["confidence_bps"] = 9499
        self.assertFalse(decide(x).autonomous)

    def test_threshold_confidence_allows(self):
        x = base(); x["confidence_bps"] = 9500
        self.assertTrue(decide(x).autonomous)

    def test_duplicate_ref_different_generation_rejected(self):
        x = base(); x["evidence"].append({"ref": x["evidence"][0]["ref"], "sha256": H2})
        with self.assertRaises(QuietOpsError): decide(x)

    def test_duplicate_evidence_row_rejected(self):
        x = base(); x["evidence"].append(copy.deepcopy(x["evidence"][0]))
        with self.assertRaises(QuietOpsError): decide(x)

    def test_uppercase_hash_rejected(self):
        x = base(); x["evidence"][0]["sha256"] = "A" * 64
        with self.assertRaises(QuietOpsError): decide(x)

    def test_binary_float_rejected(self):
        x = base(); x["context"]["expected_minor"] = 1.0
        with self.assertRaises(QuietOpsError): decide(x)

    def test_unsafe_key_rejected(self):
        x = base(); x["context"]["__proto__"] = {"polluted": True}
        with self.assertRaises(QuietOpsError): decide(x)

    def test_deep_context_rejected(self):
        x = base()
        value = "leaf"
        for _ in range(40): value = {"x": value}
        x["context"] = value
        with self.assertRaises(QuietOpsError): decide(x)

    def test_oversized_context_string_rejected(self):
        x = base(); x["context"]["note"] = "x" * 131073
        with self.assertRaises(QuietOpsError): decide(x)

    def test_extra_top_level_key_rejected(self):
        x = base(); x["send_authorized"] = True
        with self.assertRaises(QuietOpsError): decide(x)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(QuietOpsError): strict_json_loads('{"a":1,"a":2}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(QuietOpsError): strict_json_loads('{"a":NaN}')

    def test_decimal_parses_without_float(self):
        obj = strict_json_loads('{"a":1.25}')
        self.assertIsInstance(obj["a"], Decimal)

    def test_decision_stable_under_evidence_order(self):
        x = base(); x["evidence"].append({"ref": "snapshot://crm/2026-09", "sha256": H2})
        y = copy.deepcopy(x); y["evidence"].reverse()
        self.assertEqual(decide(x).evidence_sha256, decide(y).evidence_sha256)
        self.assertEqual(decide(x).input_sha256, decide(y).input_sha256)
        self.assertEqual(decide(x).operation_id, decide(y).operation_id)

    def test_exact_queue_replay_collapses(self):
        x = base()
        rows = process_queue([x, copy.deepcopy(x)])
        self.assertEqual(rows[0]["status"], "PROCESSED")
        self.assertEqual(rows[1]["status"], "EXACT_REPLAY_SKIPPED")
        self.assertIsNone(rows[1]["receipt"])

    def test_event_id_reuse_for_changed_generation_fails_closed(self):
        a = base()
        b = base(); b["context"]["observed_minor"] = 9999
        with self.assertRaises(QuietOpsError):
            process_queue([a, b])

    def test_durable_completed_operation_is_skipped(self):
        x = base()
        op = decide(x).operation_id
        rows = process_queue([x], completed_operation_ids=[op])
        self.assertEqual(rows[0]["status"], "DURABLE_REPLAY_SKIPPED")
        self.assertIsNone(rows[0]["receipt"])

    def test_bad_completed_operation_id_rejected(self):
        with self.assertRaises(QuietOpsError):
            process_queue([base()], completed_operation_ids=["not-a-hash"])

    def test_operation_id_is_content_bound(self):
        a = decide(base())
        x = base(); x["event_id"] = "event-002"
        b = decide(x)
        self.assertNotEqual(a.operation_id, b.operation_id)

    def test_fabricated_decision_object_cannot_bypass_public_minter(self):
        # The public API accepts raw work items, not caller-minted Decision authority.
        x = base("CONTACT_CUSTOMER"); x.pop("context")
        fake = decide(base())
        with self.assertRaises((QuietOpsError, TypeError, AttributeError)):
            make_receipt(fake, result={"ok": True})

    def test_verifier_recomputes_authority_from_raw_item(self):
        safe = base()
        receipt = process_offline(safe)["receipt"]
        human = base("CONTACT_CUSTOMER"); human.pop("context")
        self.assertFalse(verify_receipt(human, receipt))

    def test_human_decision_cannot_mint_execution_receipt(self):
        x = base("CONTRACT_ACCEPTANCE"); x.pop("context")
        with self.assertRaises(QuietOpsError): make_receipt(x, result={"ok": True})

    def test_variance_is_owner_review_but_reconciliation_itself_is_reversible(self):
        x = base(); x["context"]["observed_minor"] = 8500
        out = process_offline(x)
        self.assertEqual(out["result"]["status"], "OWNER_REVIEW_VARIANCE")
        self.assertTrue(verify_receipt(x, out["receipt"]))
        self.assertTrue(out["followup"]["human_decision_required"])
        self.assertEqual(out["followup"]["variance_minor"], -1500)
        self.assertFalse(out["followup"]["external_action_taken"])

    def test_exact_reconciliation_match_has_no_followup(self):
        out = process_offline(base())
        self.assertEqual(out["result"]["status"], "MATCH")
        self.assertIsNone(out["followup"])

    def test_initial_human_authority_has_deterministic_followup_card(self):
        x = base("CONTACT_CUSTOMER"); x.pop("context")
        out = process_offline(x)
        self.assertIsNone(out["receipt"])
        self.assertTrue(out["followup"]["human_decision_required"])
        self.assertEqual(out["followup"]["kind"], "INPUT_AUTHORITY_DECISION")
        self.assertFalse(out["followup"]["external_action_taken"])

    def test_safe_integer_bound(self):
        x = base(); x["context"]["expected_minor"] = 9_000_000_000_000_001
        with self.assertRaises(QuietOpsError): process_offline(x)


if __name__ == "__main__":
    unittest.main()
