from __future__ import annotations

import copy
import unittest

from revenue.commercial_lifecycle_ledger.lifecycle import (
    LedgerError,
    compile_ledger,
    subject_commitment,
    verify_receipt,
)


def base():
    return {
        "version": "commons-commercial-lifecycle/v1",
        "deal_id": "deal-ingestion-001",
        "opportunity_sha256": "1" * 64,
        "offer_sha256": "2" * 64,
        "scope_sha256": "3" * 64,
        "buyer_ref_sha256": "4" * 64,
        "currency": "USD",
        "contract_amount_minor": 250000,
        "offer_expires_at": "2026-10-01T00:00:00Z",
        "events": [],
    }


def ev(payload, n, kind, authority, when, *, amount=None, currency=None):
    return {
        "event_id": f"i{n:02d}",
        "kind": kind,
        "occurred_at": when,
        "authority": authority,
        "evidence_sha256": (f"{n:x}" * 64)[:64],
        "subject_sha256": subject_commitment(payload),
        "amount_minor": amount,
        "currency": currency,
        "reversal_of": None,
    }


def staged_payload():
    p = base()
    p["events"] = [
        ev(p, 1, "OPPORTUNITY_QUALIFIED", "owner", "2026-09-13T10:00:00Z"),
        ev(p, 2, "OFFER_OWNER_APPROVED", "owner", "2026-09-13T10:01:00Z"),
        ev(p, 3, "OFFER_SENT", "transport", "2026-09-13T10:02:00Z"),
        ev(p, 4, "BUYER_ACCEPTED", "buyer", "2026-09-13T10:03:00Z"),
        ev(p, 5, "FUNDING_VERIFIED", "funding", "2026-09-13T10:04:00Z",
           amount=250000, currency="USD"),
    ]
    return p


class IngestionHardeningTests(unittest.TestCase):
    ASOF = "2026-09-13T11:00:00Z"

    def test_delayed_exact_retry_collapses_before_chronology(self):
        p = staged_payload()
        baseline = compile_ledger(copy.deepcopy(p), trusted_as_of=self.ASOF)
        p["events"].append(copy.deepcopy(p["events"][0]))
        replayed = compile_ledger(p, trusted_as_of=self.ASOF)
        self.assertEqual(replayed["unique_event_count"], 5)
        self.assertEqual(replayed["input_event_count"], 6)
        self.assertEqual(replayed["state"], baseline["state"])
        self.assertEqual(replayed["event_chain_head_sha256"], baseline["event_chain_head_sha256"])
        self.assertEqual(replayed["normalized_input_sha256"], baseline["normalized_input_sha256"])
        self.assertTrue(verify_receipt(p, replayed, trusted_as_of=self.ASOF))

    def test_delayed_conflicting_retry_still_fails_closed(self):
        p = staged_payload()
        dup = copy.deepcopy(p["events"][0])
        dup["evidence_sha256"] = "f" * 64
        p["events"].append(dup)
        with self.assertRaisesRegex(LedgerError, "conflicting duplicate event_id"):
            compile_ledger(p, trusted_as_of=self.ASOF)

    def test_unique_out_of_order_event_still_fails(self):
        p = staged_payload()
        late_insert = copy.deepcopy(p["events"][0])
        late_insert["event_id"] = "i99"
        late_insert["evidence_sha256"] = "e" * 64
        p["events"].append(late_insert)
        with self.assertRaisesRegex(LedgerError, "unique events must be nondecreasing"):
            compile_ledger(p, trusted_as_of=self.ASOF)

    def test_offer_expiry_rejects_space_separator_alias(self):
        p = base()
        p["offer_expires_at"] = "2026-10-01 00:00:00Z"
        with self.assertRaisesRegex(LedgerError, "canonical whole-second UTC"):
            subject_commitment(p)

    def test_offer_expiry_rejects_iso_week_date_alias(self):
        p = base()
        p["offer_expires_at"] = "2026-W40-4T00:00:00Z"
        with self.assertRaisesRegex(LedgerError, "canonical whole-second UTC"):
            subject_commitment(p)

    def test_event_time_rejects_space_separator_alias(self):
        p = staged_payload()
        p["events"][0]["occurred_at"] = "2026-09-13 10:00:00Z"
        with self.assertRaisesRegex(LedgerError, "canonical whole-second UTC"):
            compile_ledger(p, trusted_as_of=self.ASOF)

    def test_trusted_as_of_rejects_space_separator_alias(self):
        p = staged_payload()
        with self.assertRaisesRegex(LedgerError, "canonical whole-second UTC"):
            compile_ledger(p, trusted_as_of="2026-09-13 11:00:00Z")

    def test_invalid_calendar_date_fails_after_grammar_match(self):
        p = base()
        p["offer_expires_at"] = "2026-02-30T00:00:00Z"
        with self.assertRaisesRegex(LedgerError, "not a valid UTC timestamp"):
            subject_commitment(p)


if __name__ == "__main__":
    unittest.main()
