#!/usr/bin/env python3
import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MODULE_PATH = ROOT / "host" / "checkout_handoff.py"
SPEC = importlib.util.spec_from_file_location("checkout_handoff", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class CheckoutHandoffTests(unittest.TestCase):
    def setUp(self):
        self.catalog = {
            "listings": [{
                "id": "same-day-agent-survival-proof",
                "name": "Same-Day Agent Survival Proof",
                "pricing": {
                    "currency": "USD",
                    "components": [{"id": "entry_fee", "kind": "fixed", "amount": "2500.00"}],
                },
            }],
        }
        self.request = load("revenue/checkout_handoff/example_request.json")
        self.events = load("revenue/checkout_handoff/example_events.json")

    def test_examples_and_schemas_are_json(self):
        for path in (
            "revenue/checkout_handoff/request.schema.json",
            "revenue/checkout_handoff/event.schema.json",
            "revenue/checkout_handoff/example_request.json",
            "revenue/checkout_handoff/example_events.json",
        ):
            self.assertIsNotNone(load(path))

    def test_acceptance_digest_and_catalog_amount_are_locked(self):
        validated = MODULE.validate_request(self.request, self.catalog)
        self.assertEqual(
            validated["acceptance_digest"],
            MODULE.acceptance_digest(validated["acceptance"]),
        )
        changed = copy.deepcopy(self.request)
        changed["acceptance"]["then"] += " changed"
        with self.assertRaisesRegex(MODULE.HandoffError, "acceptance_digest"):
            MODULE.validate_request(changed, self.catalog)
        changed = copy.deepcopy(self.request)
        changed["quote"]["amount"] = "2499.00"
        with self.assertRaisesRegex(MODULE.HandoffError, "canonical"):
            MODULE.validate_request(changed, self.catalog)

    def test_build_is_hosted_secret_free_and_source_bound(self):
        envelope = MODULE.build_checkout_envelope(self.request, self.catalog)
        params = envelope["parameters"]
        self.assertEqual(params["mode"], "payment")
        self.assertEqual(params["ui_mode"], "hosted")
        self.assertEqual(params["line_items"][0]["price_data"]["unit_amount"], 250000)
        self.assertEqual(params["line_items"][0]["price_data"]["currency"], "usd")
        self.assertEqual(params["metadata"]["commons_crm_record"], "recEXAMPLE0000000")
        self.assertEqual(params["metadata"]["commons_acceptance_sha256"], self.request["acceptance_digest"])
        self.assertRegex(params["integration_identifier"], r"^commons_checkout_[a-p]{8}$")
        serialized = MODULE.canonical(envelope).lower()
        self.assertNotIn("payment_method_types", serialized)
        self.assertNotIn("automatic_tax", serialized)
        for forbidden in ("api_key", "secret", "card_number", "routing_number"):
            self.assertNotIn(forbidden, serialized)

    def test_unverified_or_misbinding_event_is_rejected(self):
        bad = copy.deepcopy(self.events[0])
        bad["verification"] = "UNVERIFIED"
        with self.assertRaisesRegex(MODULE.HandoffError, "integrity verification"):
            MODULE.payment_projection(self.request, [bad], self.catalog)
        bad = copy.deepcopy(self.events[0])
        bad["amount_minor"] = 1
        with self.assertRaisesRegex(MODULE.HandoffError, "acceptance-locked"):
            MODULE.payment_projection(self.request, [bad], self.catalog)

    def test_checkout_created_or_unpaid_does_not_start_delivery(self):
        projection = MODULE.payment_projection(self.request, self.events[:1], self.catalog)
        self.assertFalse(projection["fulfillment"]["delivery_start_allowed"])
        unpaid = copy.deepcopy(self.events[0])
        unpaid["event_id"] = "checkout-observation-example-unpaid"
        unpaid["provider_event_id"] = "evt_example_checkout_unpaid_01"
        unpaid["provider_event_type"] = "checkout.session.completed"
        unpaid["facts"] = {"payment_status": "unpaid"}
        projection = MODULE.payment_projection(self.request, [unpaid], self.catalog)
        self.assertEqual(projection["payment_truth"]["authorization"], "UNMEASURED")
        self.assertFalse(projection["fulfillment"]["delivery_start_allowed"])

    def test_verified_payment_authorization_starts_delivery(self):
        projection = MODULE.payment_projection(self.request, self.events[:2], self.catalog)
        self.assertEqual(projection["payment_truth"]["authorization"], "CONFIRMED")
        self.assertTrue(projection["fulfillment"]["delivery_start_allowed"])
        self.assertIsNone(projection["crm_mutation_plan"]["stage_change"])
        self.assertEqual(projection["crm_mutation_plan"]["policy"], "UPDATE_EXISTING_RECORD_ONLY")

    def test_provider_event_dedupe_is_exactly_once(self):
        duplicate = copy.deepcopy(self.events[1])
        projection = MODULE.payment_projection(
            self.request, [self.events[0], self.events[1], duplicate], self.catalog
        )
        self.assertEqual(projection["source_event_count"], 3)
        self.assertEqual(projection["unique_event_count"], 2)
        self.assertEqual(
            projection["deduped_provider_event_ids"],
            ["evt_example_payment_succeeded_01"],
        )
        conflicting = copy.deepcopy(duplicate)
        conflicting["payload_sha256"] = "f" * 64
        with self.assertRaisesRegex(MODULE.HandoffError, "conflicting duplicate"):
            MODULE.payment_projection(self.request, [self.events[1], conflicting], self.catalog)

    def test_settlement_and_payout_do_not_claim_bank_cash(self):
        projection = MODULE.payment_projection(self.request, self.events, self.catalog)
        truth = projection["payment_truth"]
        self.assertEqual(truth["authorization"], "CONFIRMED")
        self.assertEqual(truth["settlement"], "CONFIRMED")
        self.assertEqual(truth["payout"], "CONFIRMED")
        self.assertEqual(truth["bank_available"], "UNMEASURED")
        self.assertFalse(truth["cash_claimed"])

    def test_bank_available_requires_positive_private_readback(self):
        bank = copy.deepcopy(self.events[-1])
        bank.update({
            "event_id": "checkout-observation-example-bank",
            "provider": "bank-readback",
            "provider_event_id": "bank_example_posted_01",
            "provider_event_type": "commons.bank_available.confirmed",
            "provider_object_ref": "bank_readback_example_01",
            "verification": "PRIVATE_READBACK_VERIFIED",
            "payload_sha256": "5" * 64,
            "facts": {"bank_posted": True},
        })
        projection = MODULE.payment_projection(self.request, self.events + [bank], self.catalog)
        self.assertEqual(projection["payment_truth"]["bank_available"], "CONFIRMED")
        self.assertTrue(projection["payment_truth"]["cash_claimed"])
        bad = copy.deepcopy(bank)
        bad["facts"] = {"bank_posted": False}
        with self.assertRaisesRegex(MODULE.HandoffError, "positive private bank readback"):
            MODULE.payment_projection(self.request, [bad], self.catalog)

    def test_refund_disables_delivery(self):
        refunded = copy.deepcopy(self.events[1])
        refunded.update({
            "event_id": "checkout-observation-example-refund",
            "provider_event_id": "evt_example_refund_succeeded_01",
            "provider_event_type": "charge.refunded",
            "provider_object_ref": "ch_example_survival_01",
            "payload_sha256": "6" * 64,
            "facts": {"refund_status": "succeeded"},
        })
        projection = MODULE.payment_projection(self.request, [self.events[1], refunded], self.catalog)
        self.assertEqual(projection["payment_truth"]["refunded"], "CONFIRMED")
        self.assertFalse(projection["fulfillment"]["delivery_start_allowed"])
        self.assertFalse(projection["payment_truth"]["cash_claimed"])

    def test_private_or_unknown_fields_are_rejected(self):
        bad = copy.deepcopy(self.request)
        bad["api_key"] = "do-not-store"
        with self.assertRaisesRegex(MODULE.HandoffError, "fields mismatch"):
            MODULE.validate_request(bad, self.catalog)


if __name__ == "__main__":
    unittest.main()
