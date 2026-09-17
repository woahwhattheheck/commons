from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime

from .engine import (
    AUTHORITY,
    ContractError,
    CURRENT_FOR_OWNER_USE,
    EXPIRED_REQUOTE_REQUIRED,
    HOLD_NO_VALIDITY_BASIS,
    HOLD_SOURCE_DRIFT,
    SUPERSEDED,
    canonical_bytes,
    compile_at,
    strict_json_loads,
    verify_at,
)

NOW = datetime(2026, 9, 17, 18, 0, 0, tzinfo=UTC)
A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64
E = "e" * 64


def offer() -> dict:
    return {
        "schema": "proposal-validity-offer/v1",
        "opportunity_id": "opp-001",
        "offer_id": "offer-001",
        "source_generation": "buyer-gen-7",
        "source_digest_sha256": A,
        "pricing_revision": "price-r3",
        "currency": "USD",
        "scope_sha256": B,
        "economics_sha256": C,
        "issued_at_utc": "2026-09-10T18:00:00Z",
        "validity": {"kind": "UNTIL", "valid_until_utc": "2026-10-10T18:00:00Z"},
        "buyer_deadline_utc": "2026-10-01T18:00:00Z",
        "payment_rail": {
            "rail_id": "stripe-link-1",
            "rail_revision": "rail-r2",
            "checkout_ref_sha256": D,
            "state": "ACTIVE",
        },
    }


def current() -> dict:
    return {
        "schema": "proposal-validity-current/v1",
        "opportunity_id": "opp-001",
        "source_generation": "buyer-gen-7",
        "source_digest_sha256": A,
        "source_status": "CURRENT",
        "source_observed_at_utc": "2026-09-17T17:00:00Z",
        "pricing_revision": "price-r3",
        "currency": "USD",
        "scope_sha256": B,
        "economics_sha256": C,
        "buyer_deadline_utc": "2026-10-01T18:00:00Z",
        "supersession_events": [],
        "payment_rail": {
            "rail_id": "stripe-link-1",
            "rail_revision": "rail-r2",
            "checkout_ref_sha256": D,
            "state": "ACTIVE",
        },
    }


def raw(value: dict) -> bytes:
    return canonical_bytes(value)


class ProposalValidityGateTests(unittest.TestCase):
    def compile(self, o: dict | None = None, c: dict | None = None, now: datetime = NOW) -> dict:
        return compile_at(raw(o or offer()), raw(c or current()), now)

    def test_current_offer_is_owner_review_only(self):
        receipt = self.compile()
        self.assertEqual(receipt["currentness_state"], CURRENT_FOR_OWNER_USE)
        self.assertFalse(receipt["requote_delta"]["required"])
        self.assertEqual(receipt["authority"], AUTHORITY)
        self.assertTrue(all(value is False for value in receipt["authority"].values()))

    def test_missing_validity_basis_holds(self):
        o = offer()
        o["validity"] = {"kind": "NONE"}
        receipt = self.compile(o=o)
        self.assertEqual(receipt["currentness_state"], HOLD_NO_VALIDITY_BASIS)
        self.assertIn("no_validity_basis", receipt["requote_delta"]["reasons"])

    def test_validity_expiry_requires_requote(self):
        late = datetime(2026, 10, 10, 18, 0, 0, tzinfo=UTC)
        receipt = self.compile(now=late)
        self.assertEqual(receipt["currentness_state"], EXPIRED_REQUOTE_REQUIRED)
        self.assertIn("validity_expired", receipt["requote_delta"]["reasons"])

    def test_buyer_deadline_passed_requires_requote_even_if_offer_valid(self):
        late = datetime(2026, 10, 2, 18, 0, 0, tzinfo=UTC)
        receipt = self.compile(now=late)
        self.assertEqual(receipt["currentness_state"], EXPIRED_REQUOTE_REQUIRED)
        self.assertIn("buyer_deadline_passed", receipt["requote_delta"]["reasons"])

    def test_superseding_amendment_wins(self):
        c = current()
        c["source_generation"] = "buyer-gen-8"
        c["source_digest_sha256"] = E
        c["source_observed_at_utc"] = "2026-09-17T17:50:00Z"
        c["supersession_events"] = [
            {
                "event_id": "amend-8",
                "kind": "AMENDMENT",
                "opportunity_id": "opp-001",
                "supersedes_offer_id": "offer-001",
                "observed_at_utc": "2026-09-17T17:30:00Z",
                "source_digest_sha256": E,
            }
        ]
        receipt = self.compile(c=c)
        self.assertEqual(receipt["currentness_state"], SUPERSEDED)
        self.assertEqual(receipt["requote_delta"]["superseding_event_ids"], ["amend-8"])

    def test_source_generation_or_digest_drift_holds(self):
        for field, value in (("source_generation", "buyer-gen-8"), ("source_digest_sha256", E)):
            with self.subTest(field=field):
                c = current()
                c[field] = value
                receipt = self.compile(c=c)
                self.assertEqual(receipt["currentness_state"], HOLD_SOURCE_DRIFT)
                self.assertIn(field, receipt["requote_delta"]["changed_fields"])

    def test_commercial_drift_holds(self):
        cases = {
            "pricing_revision": "price-r4",
            "currency": "EUR",
            "scope_sha256": E,
            "economics_sha256": E,
            "buyer_deadline_utc": "2026-10-02T18:00:00Z",
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                c = current()
                c[field] = value
                receipt = self.compile(c=c)
                self.assertEqual(receipt["currentness_state"], HOLD_SOURCE_DRIFT)
                self.assertIn(field, receipt["requote_delta"]["changed_fields"])

    def test_stale_source_status_holds(self):
        c = current()
        c["source_status"] = "STALE"
        receipt = self.compile(c=c)
        self.assertEqual(receipt["currentness_state"], HOLD_SOURCE_DRIFT)
        self.assertIn("source_status", receipt["requote_delta"]["changed_fields"])

    def test_stale_payment_rail_holds(self):
        c = current()
        c["payment_rail"]["state"] = "REPLACED"
        receipt = self.compile(c=c)
        self.assertEqual(receipt["currentness_state"], HOLD_SOURCE_DRIFT)
        self.assertIn("payment_rail", receipt["requote_delta"]["changed_fields"])

    def test_opportunity_replay_is_rejected(self):
        c = current()
        c["opportunity_id"] = "opp-002"
        with self.assertRaisesRegex(ContractError, "opportunity_mismatch"):
            self.compile(c=c)

    def test_future_issued_and_future_source_are_rejected(self):
        o = offer()
        o["issued_at_utc"] = "2026-09-18T18:00:00Z"
        o["validity"] = {"kind": "UNTIL", "valid_until_utc": "2026-10-10T18:00:00Z"}
        with self.assertRaisesRegex(ContractError, "offer_issued_in_future"):
            self.compile(o=o)
        c = current()
        c["source_observed_at_utc"] = "2026-09-18T18:00:00Z"
        with self.assertRaisesRegex(ContractError, "current_source_observed_in_future"):
            self.compile(c=c)

    def test_naive_or_noncanonical_timestamps_and_bool_days_are_rejected(self):
        o = offer()
        o["issued_at_utc"] = "2026-09-10T18:00:00"
        with self.assertRaisesRegex(ContractError, "timestamp_utc"):
            self.compile(o=o)
        o = offer()
        o["validity"] = {"kind": "DAYS", "days": True}
        with self.assertRaisesRegex(ContractError, "days_integer_range"):
            self.compile(o=o)

    def test_packet_clock_injection_is_unknown_field(self):
        o = offer()
        o["as_of_utc"] = "2026-09-11T00:00:00Z"
        with self.assertRaisesRegex(ContractError, "offer_keys"):
            self.compile(o=o)

    def test_strict_json_rejects_duplicate_nonfinite_and_float(self):
        with self.assertRaisesRegex(ContractError, "duplicate_json_key"):
            strict_json_loads(b'{"a":1,"a":2}')
        with self.assertRaisesRegex(ContractError, "nonfinite_number"):
            strict_json_loads(b'{"a":NaN}')
        with self.assertRaisesRegex(ContractError, "float_not_allowed"):
            strict_json_loads(b'{"a":1.25}')

    def test_receipt_semantic_tamper_is_rejected(self):
        o_raw, c_raw = raw(offer()), raw(current())
        receipt = compile_at(o_raw, c_raw, NOW)
        receipt["requote_delta"]["required"] = True
        with self.assertRaisesRegex(ContractError, "semantic_hash_mismatch"):
            verify_at(o_raw, c_raw, canonical_bytes(receipt), NOW)

    def test_receipt_replay_under_changed_source_bytes_is_rejected(self):
        o_raw, c_raw = raw(offer()), raw(current())
        receipt_raw = canonical_bytes(compile_at(o_raw, c_raw, NOW))
        c = current()
        c["source_digest_sha256"] = E
        with self.assertRaisesRegex(ContractError, "receipt_current_semantics_mismatch"):
            verify_at(o_raw, raw(c), receipt_raw, NOW)

    def test_historical_current_receipt_cannot_be_replayed_after_expiry(self):
        o_raw, c_raw = raw(offer()), raw(current())
        receipt_raw = canonical_bytes(compile_at(o_raw, c_raw, NOW))
        later = datetime(2026, 10, 10, 18, 0, 0, tzinfo=UTC)
        with self.assertRaisesRegex(ContractError, "current_state_drift"):
            verify_at(o_raw, c_raw, receipt_raw, later)

    def test_exact_receipt_verifies_while_state_is_stable(self):
        o_raw, c_raw = raw(offer()), raw(current())
        receipt_raw = canonical_bytes(compile_at(o_raw, c_raw, NOW))
        later = datetime(2026, 9, 18, 18, 0, 0, tzinfo=UTC)
        result = verify_at(o_raw, c_raw, receipt_raw, later)
        self.assertTrue(result["verified"])
        self.assertEqual(result["currentness_state"], CURRENT_FOR_OWNER_USE)
        self.assertEqual(result["authority"], AUTHORITY)

    def test_supersession_order_is_canonical(self):
        c = current()
        c["source_generation"] = "buyer-gen-8"
        c["source_digest_sha256"] = E
        c["source_observed_at_utc"] = "2026-09-17T17:50:00Z"
        event_a = {
            "event_id": "event-b",
            "kind": "REDLINE",
            "opportunity_id": "opp-001",
            "supersedes_offer_id": "offer-001",
            "observed_at_utc": "2026-09-17T17:40:00Z",
            "source_digest_sha256": E,
        }
        event_b = {
            "event_id": "event-a",
            "kind": "AMENDMENT",
            "opportunity_id": "opp-001",
            "supersedes_offer_id": "offer-001",
            "observed_at_utc": "2026-09-17T17:20:00Z",
            "source_digest_sha256": E,
        }
        c["supersession_events"] = [event_a, event_b]
        one = self.compile(c=c)
        c["supersession_events"] = [copy.deepcopy(event_b), copy.deepcopy(event_a)]
        two = self.compile(c=c)
        self.assertEqual(one, two)
        self.assertEqual(one["requote_delta"]["superseding_event_ids"], ["event-a", "event-b"])

    def test_cli_compile_verify_round_trip_and_has_no_as_of_escape(self):
        o = offer()
        o["issued_at_utc"] = "2026-01-01T00:00:00Z"
        o["validity"] = {"kind": "UNTIL", "valid_until_utc": "2099-01-01T00:00:00Z"}
        o["buyer_deadline_utc"] = "2098-12-01T00:00:00Z"
        c = current()
        c["source_observed_at_utc"] = "2026-01-02T00:00:00Z"
        c["buyer_deadline_utc"] = "2098-12-01T00:00:00Z"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            offer_path = root / "offer.json"
            current_path = root / "current.json"
            receipt_path = root / "receipt.json"
            verify_path = root / "verify.json"
            offer_path.write_bytes(raw(o))
            current_path.write_bytes(raw(c))
            python_args = [sys.executable] + (["-O"] if sys.flags.optimize else [])
            compile_proc = subprocess.run(
                python_args + [
                    "-m",
                    "revenue.proposal_validity_gate",
                    "compile",
                    "--offer",
                    str(offer_path),
                    "--current",
                    str(current_path),
                    "--out",
                    str(receipt_path),
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(compile_proc.returncode, 0, compile_proc.stderr + compile_proc.stdout)
            verify_proc = subprocess.run(
                python_args + [
                    "-m",
                    "revenue.proposal_validity_gate",
                    "verify",
                    "--offer",
                    str(offer_path),
                    "--current",
                    str(current_path),
                    "--receipt",
                    str(receipt_path),
                    "--out",
                    str(verify_path),
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(verify_proc.returncode, 0, verify_proc.stderr + verify_proc.stdout)
            verified = json.loads(verify_path.read_text(encoding="utf-8"))
            self.assertTrue(verified["verified"])
            self.assertEqual(verified["currentness_state"], CURRENT_FOR_OWNER_USE)

            escape_proc = subprocess.run(
                python_args + [
                    "-m",
                    "revenue.proposal_validity_gate",
                    "compile",
                    "--offer",
                    str(offer_path),
                    "--current",
                    str(current_path),
                    "--as-of",
                    "2026-01-01T00:00:00Z",
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(escape_proc.returncode, 2)
            self.assertIn("unrecognized arguments: --as-of", escape_proc.stderr)

    def test_supersession_evidence_is_bound_to_current_source_generation(self):
        c = current()
        c["source_observed_at_utc"] = "2026-09-17T17:50:00Z"
        c["supersession_events"] = [
            {
                "event_id": "unbound-amendment",
                "kind": "AMENDMENT",
                "opportunity_id": "opp-001",
                "supersedes_offer_id": "offer-001",
                "observed_at_utc": "2026-09-17T17:30:00Z",
                "source_digest_sha256": E,
            }
        ]
        with self.assertRaisesRegex(ContractError, "event_source_digest_mismatch"):
            self.compile(c=c)

    def test_future_supersession_event_is_rejected(self):
        c = current()
        c["source_digest_sha256"] = E
        c["source_observed_at_utc"] = "2026-09-18T18:30:00Z"
        c["supersession_events"] = [
            {
                "event_id": "future-amendment",
                "kind": "AMENDMENT",
                "opportunity_id": "opp-001",
                "supersedes_offer_id": "offer-001",
                "observed_at_utc": "2026-09-18T18:00:00Z",
                "source_digest_sha256": E,
            }
        ]
        with self.assertRaisesRegex(ContractError, "observed_in_future"):
            self.compile(c=c)


if __name__ == "__main__":
    unittest.main(verbosity=2)
