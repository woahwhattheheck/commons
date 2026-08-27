import hashlib
import hmac
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HOST = ROOT / "host"
sys.path.insert(0, str(HOST))

SPEC = importlib.util.spec_from_file_location("stripe_event_bridge", HOST / "stripe_event_bridge.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)

import checkout_handoff  # noqa: E402


class StripeEventBridgeTests(unittest.TestCase):
    def setUp(self):
        self.secret = "whsec_test_fixture_not_a_real_secret"
        self.now = 1787802000
        self.request = json.loads((ROOT / "revenue" / "checkout_handoff" / "example_request.json").read_text())
        self.catalog = json.loads((ROOT / "revenue" / "outcome_commerce" / "catalog.json").read_text())
        self.metadata = {
            "commons_request_id": self.request["request_id"],
            "commons_crm_record": self.request["crm"]["record_id"],
            "commons_sku_id": self.request["sku_id"],
            "commons_acceptance_sha256": self.request["acceptance_digest"],
            "commons_dedupe_key": checkout_handoff.build_checkout_envelope(
                self.request, self.catalog,
            )["idempotency_key"],
        }

    def event(self, event_type="checkout.session.completed", **object_updates):
        obj = {
            "id": "cs_test_bound_001",
            "amount_total": 250000,
            "currency": "usd",
            "payment_status": "paid",
            "metadata": deepcopy(self.metadata),
            "client_reference_id": self.request["crm"]["record_id"],
            "customer_details": {"email": "private@example.invalid"},
        }
        obj.update(object_updates)
        return {
            "id": "evt_test_bound_001",
            "object": "event",
            "type": event_type,
            "livemode": False,
            "created": self.now,
            "data": {"object": obj},
        }

    @staticmethod
    def raw(event):
        return json.dumps(event, separators=(",", ":"), sort_keys=True).encode()

    def signature(self, raw, timestamp=None, secret=None, extra=""):
        timestamp = self.now if timestamp is None else timestamp
        secret = self.secret if secret is None else secret
        digest = hmac.new(secret.encode(), str(timestamp).encode() + b"." + raw, hashlib.sha256).hexdigest()
        return "t=%d,v1=%s%s" % (timestamp, digest, extra)

    def normalize(self, event=None, timestamp=None, signature_secret=None, verify_secret=None):
        raw = self.raw(event or self.event())
        header = self.signature(raw, timestamp=timestamp, secret=signature_secret)
        return MODULE.normalize_signed_event(
            raw,
            header,
            self.secret if verify_secret is None else verify_secret,
            self.request,
            self.catalog,
            now=self.now,
        )

    def test_valid_paid_checkout_feeds_existing_projection(self):
        result = self.normalize()
        self.assertEqual(result["status"], "NORMALIZED")
        observation = result["observation"]
        projection = checkout_handoff.payment_projection(self.request, [observation], self.catalog)
        self.assertEqual(projection["payment_truth"]["authorization"], "CONFIRMED")
        self.assertTrue(projection["fulfillment"]["delivery_start_allowed"])
        self.assertEqual(projection["payment_truth"]["bank_available"], "UNMEASURED")
        self.assertFalse(projection["payment_truth"]["cash_claimed"])

    def test_wrong_secret_and_mutated_body_fail_closed(self):
        raw = self.raw(self.event())
        header = self.signature(raw)
        with self.assertRaisesRegex(MODULE.BridgeError, "verification failed"):
            MODULE.normalize_signed_event(raw, header, "wrong", self.request, self.catalog, now=self.now)
        with self.assertRaisesRegex(MODULE.BridgeError, "verification failed"):
            MODULE.normalize_signed_event(raw + b" ", header, self.secret, self.request, self.catalog, now=self.now)

    def test_stale_and_future_timestamps_fail(self):
        for timestamp in (self.now - 301, self.now + 301):
            with self.subTest(timestamp=timestamp):
                with self.assertRaisesRegex(MODULE.BridgeError, "outside tolerance"):
                    self.normalize(timestamp=timestamp)

    def test_multiple_v1_signatures_support_secret_roll(self):
        raw = self.raw(self.event())
        valid = self.signature(raw)
        result = MODULE.normalize_signed_event(
            raw,
            valid + ",v1=" + "0" * 64 + ",v0=" + "1" * 64,
            self.secret,
            self.request,
            self.catalog,
            now=self.now,
        )
        self.assertEqual(result["status"], "NORMALIZED")

    def test_malformed_headers_fail(self):
        raw = self.raw(self.event())
        for header in ("", "garbage", "t=nope,v1=" + "0" * 64, "t=1", "t=1,t=2,v1=" + "0" * 64):
            with self.subTest(header=header):
                with self.assertRaises(MODULE.BridgeError):
                    MODULE.normalize_signed_event(raw, header, self.secret, self.request, self.catalog, now=self.now)

    def test_livemode_must_match_request(self):
        event = self.event()
        event["livemode"] = True
        with self.assertRaisesRegex(MODULE.BridgeError, "livemode"):
            self.normalize(event)

    def test_missing_or_mismatched_metadata_is_observable_but_not_projected(self):
        for metadata in ({}, {**self.metadata, "commons_sku_id": "other-sku"}):
            with self.subTest(metadata=metadata):
                result = self.normalize(self.event(metadata=metadata))
                self.assertEqual(result["status"], "SIGNED_UNBOUND_EVENT")
                self.assertIsNone(result["observation"])

    def test_dedupe_key_and_checkout_client_reference_are_bound(self):
        bad_dedupe = deepcopy(self.metadata)
        bad_dedupe["commons_dedupe_key"] = "commons-checkout-wrong"
        cases = [
            self.event(metadata=bad_dedupe),
            self.event(client_reference_id="recWRONG00000000"),
        ]
        for event in cases:
            with self.subTest(event=event["data"]["object"]):
                result = self.normalize(event)
                self.assertEqual(result["status"], "SIGNED_UNBOUND_EVENT")
                self.assertIsNone(result["observation"])

    def test_unknown_event_type_is_observable_without_an_admission_gate(self):
        result = self.normalize(self.event("customer.created"))
        self.assertEqual(result["status"], "SIGNED_UNKNOWN_EVENT")
        self.assertEqual(result["provider_event_type"], "customer.created")
        self.assertIsNone(result["observation"])

    def test_durable_replay_returns_the_first_observation(self):
        event = self.event()
        raw = self.raw(event)
        first = MODULE.normalize_signed_event(
            raw, self.signature(raw, self.now), self.secret, self.request, self.catalog, now=self.now,
        )
        second = MODULE.normalize_signed_event(
            raw, self.signature(raw, self.now + 20), self.secret, self.request, self.catalog, now=self.now + 20,
        )
        self.assertNotEqual(first["observation"]["observed_at"], second["observation"]["observed_at"])
        with tempfile.TemporaryDirectory() as directory:
            stored, first_disposition = MODULE.persist_bridge_result(first, directory)
            replayed, second_disposition = MODULE.persist_bridge_result(second, directory)
        self.assertEqual(first_disposition, "RECORDED")
        self.assertEqual(second_disposition, "REPLAYED")
        self.assertEqual(stored, replayed)

    def test_conflicting_replay_is_quarantined(self):
        first = self.normalize()
        conflicting = deepcopy(first)
        conflicting["payload_sha256"] = "f" * 64
        with tempfile.TemporaryDirectory() as directory:
            MODULE.persist_bridge_result(first, directory)
            with self.assertRaisesRegex(MODULE.BridgeError, "conflicting replay"):
                MODULE.persist_bridge_result(conflicting, directory)

    def test_corrupted_nested_replay_receipt_is_rejected(self):
        first = self.normalize()
        event_id = first["provider_event_id"]
        filename = "stripe-event-" + hashlib.sha256(event_id.encode()).hexdigest() + ".json"
        with tempfile.TemporaryDirectory() as directory:
            MODULE.persist_bridge_result(first, directory)
            receipt = Path(directory) / filename
            corrupted = json.loads(receipt.read_text())
            corrupted["observation"]["amount_minor"] = 1
            receipt.write_text(json.dumps(corrupted))
            second = self.normalize()
            with self.assertRaisesRegex(MODULE.BridgeError, "conflicting replay"):
                MODULE.persist_bridge_result(second, directory)

    def test_persisted_receipt_is_complete_and_temp_is_removed(self):
        first = self.normalize()
        with tempfile.TemporaryDirectory() as directory:
            stored, disposition = MODULE.persist_bridge_result(first, directory)
            files = list(Path(directory).iterdir())
            self.assertEqual(disposition, "RECORDED")
            self.assertEqual(len(files), 1)
            self.assertEqual(json.loads(files[0].read_text()), stored)

    def test_amount_currency_and_partial_refund_do_not_project(self):
        cases = [
            self.event(amount_total=1),
            self.event(currency="eur"),
            self.event(
                "charge.refunded",
                id="ch_test_partial",
                amount_total=None,
                amount_refunded=100,
                amount=250000,
                refunded=False,
            ),
        ]
        for event in cases:
            with self.subTest(event=event["data"]["object"]):
                result = self.normalize(event)
                self.assertEqual(result["status"], "SIGNED_UNBOUND_EVENT")
                self.assertIsNone(result["observation"])

    def test_result_never_emits_raw_private_payload_or_secret(self):
        result = self.normalize()
        text = json.dumps(result, sort_keys=True)
        self.assertNotIn("private@example.invalid", text)
        self.assertNotIn(self.secret, text)
        self.assertNotIn("customer_details", text)

    def test_duplicate_json_keys_are_rejected_after_signature_verification(self):
        raw = (
            '{"id":"evt_test_dup_001","id":"evt_test_dup_002","type":"customer.created",'
            '"livemode":false,"created":1787802000,"data":{"object":{}}}'
        ).encode()
        with self.assertRaisesRegex(MODULE.BridgeError, "duplicate"):
            MODULE.normalize_signed_event(
                raw, self.signature(raw), self.secret, self.request, self.catalog, now=self.now,
            )

    def test_aggregate_payout_is_not_falsely_request_bound(self):
        event = self.event(
            "payout.paid",
            id="po_test_bound_001",
            amount_total=None,
            amount=250000,
            status="paid",
        )
        result = self.normalize(event)
        self.assertEqual(result["status"], "SIGNED_UNKNOWN_EVENT")
        self.assertIsNone(result["observation"])

    def test_checkout_created_is_not_promoted_as_documented_payment_evidence(self):
        result = self.normalize(self.event("checkout.session.created"))
        self.assertEqual(result["status"], "SIGNED_UNKNOWN_EVENT")
        self.assertIsNone(result["observation"])

    def test_payment_intent_and_charge_success_confirm_authorization(self):
        cases = [
            self.event(
                "payment_intent.succeeded", id="pi_test_bound_001",
                amount_total=None, amount_received=250000,
            ),
            self.event(
                "charge.succeeded", id="ch_test_bound_001",
                amount_total=None, amount=250000,
            ),
        ]
        for event in cases:
            with self.subTest(event_type=event["type"]):
                result = self.normalize(event)
                projection = checkout_handoff.payment_projection(
                    self.request, [result["observation"]], self.catalog,
                )
                self.assertEqual(projection["payment_truth"]["authorization"], "CONFIRMED")

    def test_cli_uses_environment_not_secret_arguments(self):
        event = self.event()
        raw = self.raw(event)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "payload.json"
            signature = root / "signature.txt"
            receipts = root / "receipts"
            payload.write_bytes(raw)
            signature.write_text(self.signature(raw))
            env = dict(os.environ)
            env["BRIDGE_TEST_SECRET"] = self.secret
            run = subprocess.run(
                [
                    sys.executable,
                    str(HOST / "stripe_event_bridge.py"),
                    "--request", str(ROOT / "revenue" / "checkout_handoff" / "example_request.json"),
                    "--payload", str(payload),
                    "--signature-file", str(signature),
                    "--secret-env", "BRIDGE_TEST_SECRET",
                    "--now", str(self.now),
                    "--receipt-dir", str(receipts),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(run.returncode, 0, run.stderr)
        output = json.loads(run.stdout)
        self.assertEqual(output["delivery_disposition"], "RECORDED")
        self.assertEqual(output["result"]["status"], "NORMALIZED")
        self.assertNotIn(self.secret, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()

