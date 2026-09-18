from __future__ import annotations

import copy
import json
import unittest

from tools.revenue_collection_desk import core as c

H = "a" * 64

def ev(event_id, at, kind, **extra):
    return {
        "event_id": event_id,
        "at": at,
        "kind": kind,
        "source_ref": f"src-{event_id}",
        "source_digest": H,
        **extra,
    }

def claim(cid="c1", instrument="USD", amount="10.00", events=None, **extra):
    return {
        "claim_id": cid,
        "counterparty_id": f"party-{cid}",
        "work_ref": f"work-{cid}",
        "instrument": instrument,
        "amount": amount,
        "events": events or [
            ev("e1", "2026-09-01T00:00:00Z", "WORK_SUBMITTED"),
            ev("e2", "2026-09-02T00:00:00Z", "ACCEPTED"),
        ],
        **extra,
    }

def ledger(claims=None, as_of="2026-09-18T00:00:00Z"):
    return {
        "schema": c.LEDGER_SCHEMA,
        "as_of": as_of,
        "claims": claims or [claim()],
    }

class RevenueCollectionDeskTests(unittest.TestCase):
    def test_strict_json_rejects_duplicate_and_nonfinite(self):
        with self.assertRaises(c.ContractError):
            c.loads_strict('{"a":1,"a":2}')
        with self.assertRaises(c.ContractError):
            c.loads_strict('{"a":NaN}')

    def test_accepted_is_collection_eligible_not_paid(self):
        out = c.compile_ledger(ledger())
        row = out["claims"][0]
        self.assertEqual(row["state"], c.STATE_ACCEPTED)
        self.assertEqual(row["next_action"], "COLLECTION_ELIGIBLE")
        self.assertEqual(out["settled_cash_by_currency"], {})
        self.assertEqual(out["totals_by_instrument"]["USD"]["accepted_outstanding"], "10")

    def test_future_payment_hold_waits(self):
        cl = claim(events=[
            ev("e1", "2026-09-01T00:00:00Z", "WORK_SUBMITTED"),
            ev("e2", "2026-09-02T00:00:00Z", "ACCEPTED"),
            ev("e3", "2026-09-03T00:00:00Z", "PAYMENT_ASSERTED",
               hold_until="2026-09-20T00:00:00Z"),
        ])
        out = c.compile_ledger(ledger([cl]))
        self.assertEqual(out["claims"][0]["next_action"], "WAIT_HOLD")
        self.assertEqual(out["totals_by_instrument"]["USD"]["asserted_hold"], "10")

    def test_expired_payment_hold_verifies_available(self):
        cl = claim(events=[
            ev("e1", "2026-09-01T00:00:00Z", "WORK_SUBMITTED"),
            ev("e2", "2026-09-02T00:00:00Z", "ACCEPTED"),
            ev("e3", "2026-09-03T00:00:00Z", "PAYMENT_ASSERTED",
               hold_until="2026-09-10T00:00:00Z"),
        ])
        out = c.compile_ledger(ledger([cl]))
        self.assertEqual(out["claims"][0]["next_action"], "VERIFY_AVAILABLE")

    def test_available_is_not_settled_cash(self):
        cl = claim(instrument="RTC", amount="25", events=[
            ev("e1", "2026-09-01T00:00:00Z", "WORK_SUBMITTED"),
            ev("e2", "2026-09-02T00:00:00Z", "ACCEPTED"),
            ev("e3", "2026-09-03T00:00:00Z", "PAYMENT_AVAILABLE"),
        ])
        out = c.compile_ledger(ledger([cl]))
        self.assertEqual(out["claims"][0]["next_action"], "VERIFY_SETTLEMENT")
        self.assertEqual(out["settled_cash_by_currency"], {})
        self.assertEqual(out["totals_by_instrument"]["RTC"]["available_not_settled"], "25")

    def test_direct_settlement_records_explicit_currency_only(self):
        cl = claim(instrument="RTC", amount="25", events=[
            ev("e1", "2026-09-01T00:00:00Z", "WORK_SUBMITTED"),
            ev("e2", "2026-09-02T00:00:00Z", "ACCEPTED"),
            ev("e3", "2026-09-03T00:00:00Z", "SETTLED_CASH",
               settlement_currency="USD", settlement_amount="1.00"),
        ])
        out = c.compile_ledger(ledger([cl]))
        self.assertEqual(out["claims"][0]["state"], c.STATE_SETTLED)
        self.assertEqual(out["settled_cash_by_currency"], {"USD": "1"})
        self.assertNotIn("RTC", out["settled_cash_by_currency"])

    def test_reference_valuation_never_becomes_cash(self):
        ref = {
            "currency": "USD", "amount": "999.99", "source_ref": "rate-ref",
            "source_digest": H,
        }
        cl = claim(instrument="RTC", amount="25", reference_valuation=ref)
        out = c.compile_ledger(ledger([cl]))
        self.assertFalse(out["reference_valuations_recognized_as_cash"])
        self.assertEqual(out["settled_cash_by_currency"], {})

    def test_contact_creates_dnr_and_silence_never_releases(self):
        cl = claim(events=[
            ev("e1", "2026-09-01T00:00:00Z", "WORK_SUBMITTED"),
            ev("e2", "2026-09-02T00:00:00Z", "ACCEPTED"),
            ev("e3", "2026-09-03T00:00:00Z", "COLLECTION_CONTACT_SENT",
               cooldown_until="2026-09-04T00:00:00Z"),
        ])
        out = c.compile_ledger(ledger([cl], as_of="2026-10-01T00:00:00Z"))
        row = out["claims"][0]
        self.assertEqual(row["next_action"], "WAIT_REPLY")
        self.assertTrue(row["route"]["contact_open_dnr"])
        self.assertFalse(row["route"]["silence_authorizes_retry"])

    def test_bounce_requires_route_repair(self):
        cl = claim(events=[
            ev("e1", "2026-09-01T00:00:00Z", "WORK_SUBMITTED"),
            ev("e2", "2026-09-02T00:00:00Z", "ACCEPTED"),
            ev("e3", "2026-09-03T00:00:00Z", "COLLECTION_CONTACT_SENT",
               cooldown_until="2026-09-04T00:00:00Z"),
            ev("e4", "2026-09-03T01:00:00Z", "DELIVERY_BOUNCED"),
        ])
        out = c.compile_ledger(ledger([cl]))
        self.assertEqual(out["claims"][0]["next_action"], "ROUTE_REPAIR_REQUIRED")
        self.assertTrue(out["claims"][0]["route"]["route_dead"])
        self.assertFalse(out["claims"][0]["route"]["contact_open_dnr"])

    def test_route_repair_after_bounce_restores_eligibility(self):
        cl = claim(events=[
            ev("e1", "2026-09-01T00:00:00Z", "WORK_SUBMITTED"),
            ev("e2", "2026-09-02T00:00:00Z", "ACCEPTED"),
            ev("e3", "2026-09-03T00:00:00Z", "COLLECTION_CONTACT_SENT",
               cooldown_until="2026-09-04T00:00:00Z"),
            ev("e4", "2026-09-03T01:00:00Z", "DELIVERY_BOUNCED"),
            ev("e5", "2026-09-05T00:00:00Z", "ROUTE_REPAIRED"),
        ])
        out = c.compile_ledger(ledger([cl]))
        self.assertEqual(out["claims"][0]["next_action"], "COLLECTION_ELIGIBLE")

    def test_confirmed_contact_waits_until_explicit_release(self):
        base = [
            ev("e1", "2026-09-01T00:00:00Z", "WORK_SUBMITTED"),
            ev("e2", "2026-09-02T00:00:00Z", "ACCEPTED"),
            ev("e3", "2026-09-03T00:00:00Z", "COLLECTION_CONTACT_SENT",
               cooldown_until="2026-09-04T00:00:00Z"),
            ev("e4", "2026-09-03T01:00:00Z", "DELIVERY_CONFIRMED"),
        ]
        out = c.compile_ledger(ledger([claim(events=base)]))
        self.assertEqual(out["claims"][0]["next_action"], "WAIT_REPLY")
        released = base + [ev("e5", "2026-09-10T00:00:00Z", "COLLECTION_RELEASED")]
        out2 = c.compile_ledger(ledger([claim(events=released)]))
        self.assertEqual(out2["claims"][0]["next_action"], "COLLECTION_ELIGIBLE")

    def test_duplicate_contact_without_release_fails(self):
        cl = claim(events=[
            ev("e1", "2026-09-01T00:00:00Z", "WORK_SUBMITTED"),
            ev("e2", "2026-09-02T00:00:00Z", "ACCEPTED"),
            ev("e3", "2026-09-03T00:00:00Z", "COLLECTION_CONTACT_SENT",
               cooldown_until="2026-09-04T00:00:00Z"),
            ev("e4", "2026-09-05T00:00:00Z", "COLLECTION_CONTACT_SENT",
               cooldown_until="2026-09-06T00:00:00Z"),
        ])
        with self.assertRaises(c.ContractError):
            c.compile_ledger(ledger([cl]))

    def test_future_settlement_cannot_be_current_cash(self):
        cl = claim(events=[
            ev("e1", "2026-09-01T00:00:00Z", "WORK_SUBMITTED"),
            ev("e2", "2026-09-02T00:00:00Z", "ACCEPTED"),
            ev("e3", "2026-09-19T00:00:00Z", "SETTLED_CASH",
               settlement_currency="USD", settlement_amount="10.00"),
        ])
        with self.assertRaisesRegex(c.ContractError, "after ledger as_of"):
            c.compile_ledger(ledger([cl], as_of="2026-09-18T00:00:00Z"))

    def test_future_collection_release_cannot_reopen_contact(self):
        cl = claim(events=[
            ev("e1", "2026-09-01T00:00:00Z", "WORK_SUBMITTED"),
            ev("e2", "2026-09-02T00:00:00Z", "ACCEPTED"),
            ev("e3", "2026-09-03T00:00:00Z", "COLLECTION_CONTACT_SENT",
               cooldown_until="2026-09-04T00:00:00Z"),
            ev("e4", "2026-09-03T01:00:00Z", "DELIVERY_CONFIRMED"),
            ev("e5", "2026-09-19T00:00:00Z", "COLLECTION_RELEASED"),
        ])
        with self.assertRaisesRegex(c.ContractError, "after ledger as_of"):
            c.compile_ledger(ledger([cl], as_of="2026-09-18T00:00:00Z"))

    def test_duplicate_claim_id_fails(self):
        with self.assertRaisesRegex(c.ContractError, "duplicate claim_id"):
            c.compile_ledger(ledger([claim("same"), claim("same")]))

    def test_duplicate_event_id_fails(self):
        cl = claim(events=[
            ev("x", "2026-09-01T00:00:00Z", "WORK_SUBMITTED"),
            ev("x", "2026-09-02T00:00:00Z", "ACCEPTED"),
        ])
        with self.assertRaisesRegex(c.ContractError, "duplicate event_id"):
            c.compile_ledger(ledger([cl]))

    def test_nonmonotone_event_time_fails(self):
        cl = claim(events=[
            ev("e1", "2026-09-02T00:00:00Z", "WORK_SUBMITTED"),
            ev("e2", "2026-09-01T00:00:00Z", "ACCEPTED"),
        ])
        with self.assertRaisesRegex(c.ContractError, "strictly increasing"):
            c.compile_ledger(ledger([cl]))

    def test_illegal_financial_skip_fails(self):
        cl = claim(events=[
            ev("e1", "2026-09-01T00:00:00Z", "WORK_SUBMITTED"),
            ev("e2", "2026-09-02T00:00:00Z", "PAYMENT_ASSERTED"),
        ])
        with self.assertRaisesRegex(c.ContractError, "illegal financial transition"):
            c.compile_ledger(ledger([cl]))

    def test_unknown_field_fails(self):
        bad = claim()
        bad["secret_body"] = "nope"
        with self.assertRaises(c.ContractError):
            c.compile_ledger(ledger([bad]))

    def test_bool_as_timestamp_fails(self):
        bad = ledger()
        bad["as_of"] = True
        with self.assertRaises(c.ContractError):
            c.compile_ledger(bad)

    def test_claim_list_order_invariant(self):
        a = claim("a", amount="1.00")
        b = claim("b", instrument="RTC", amount="2")
        one = c.compile_ledger(ledger([a, b]))
        two = c.compile_ledger(ledger([b, a]))
        self.assertEqual(one, two)

    def test_no_mixed_currency_sum(self):
        out = c.compile_ledger(ledger([
            claim("usd", instrument="USD", amount="10"),
            claim("rtc", instrument="RTC", amount="25"),
        ]))
        self.assertIsNone(out["mixed_currency_sum"])
        self.assertEqual(set(out["totals_by_instrument"]), {"RTC", "USD"})

    def test_dispute_is_conflict_not_cash(self):
        cl = claim(events=[
            ev("e1", "2026-09-01T00:00:00Z", "WORK_SUBMITTED"),
            ev("e2", "2026-09-02T00:00:00Z", "ACCEPTED"),
            ev("e3", "2026-09-03T00:00:00Z", "DISPUTED"),
        ])
        out = c.compile_ledger(ledger([cl]))
        self.assertEqual(out["claims"][0]["next_action"], "HOLD_CONFLICT")
        self.assertEqual(out["settled_cash_by_currency"], {})

    def test_verify_detects_tamper(self):
        inp = ledger()
        report = c.compile_ledger(inp)
        self.assertTrue(c.verify_ledger(inp, report))
        tampered = copy.deepcopy(report)
        tampered["claims"][0]["next_action"] = "DONE"
        self.assertFalse(c.verify_ledger(inp, tampered))

    def test_receipt_is_deterministic(self):
        a = c.compile_ledger(ledger())
        b = c.compile_ledger(ledger())
        self.assertEqual(a["receipt_sha256"], b["receipt_sha256"])
        self.assertRegex(a["receipt_sha256"], r"^[0-9a-f]{64}$")

    def test_authority_is_hard_false(self):
        out = c.compile_ledger(ledger())
        self.assertTrue(out["authority"])
        self.assertTrue(all(value is False for value in out["authority"].values()))

    def test_settlement_event_requires_explicit_amount_and_currency(self):
        cl = claim(events=[
            ev("e1", "2026-09-01T00:00:00Z", "WORK_SUBMITTED"),
            ev("e2", "2026-09-02T00:00:00Z", "ACCEPTED"),
            ev("e3", "2026-09-03T00:00:00Z", "SETTLED_CASH"),
        ])
        with self.assertRaises(c.ContractError):
            c.compile_ledger(ledger([cl]))

    def test_contact_not_allowed_before_acceptance(self):
        cl = claim(events=[
            ev("e1", "2026-09-01T00:00:00Z", "WORK_SUBMITTED"),
            ev("e2", "2026-09-02T00:00:00Z", "COLLECTION_CONTACT_SENT",
               cooldown_until="2026-09-03T00:00:00Z"),
        ])
        with self.assertRaises(c.ContractError):
            c.compile_ledger(ledger([cl]))

if __name__ == "__main__":
    unittest.main()
