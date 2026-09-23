"""Synthetic exact-money regressions; no accounts, providers or contact actions."""
from __future__ import annotations

import copy
from decimal import (
    Context, Decimal, Inexact, Rounded, ROUND_DOWN, ROUND_UP,
    ROUND_HALF_EVEN, localcontext,
)
from fractions import Fraction
import json
import random
import unittest

from test_revenue_collection_desk import claim, entitlement_ev, ev, ledger
from tools.revenue_collection_desk import core as c


BUCKETS = (
    "accepted_outstanding", "accepted_unconfirmed", "asserted_hold",
    "available_not_settled", "disputed",
)
LARGE = "1234567890123456789012345678.01"


def sample(amount=LARGE, bucket="accepted_unconfirmed", cid="c1", instrument="USD"):
    events = [
        ev("e1", "2026-09-01T00:00:00Z", "WORK_SUBMITTED"),
        ev("e2", "2026-09-02T00:00:00Z", "ACCEPTED"),
    ]
    if bucket == "accepted_outstanding":
        events.append(entitlement_ev(
            "e3", "2026-09-02T01:00:00Z", instrument=instrument, amount=amount,
        ))
    elif bucket != "accepted_unconfirmed":
        kinds = {
            "asserted_hold": "PAYMENT_ASSERTED",
            "available_not_settled": "PAYMENT_AVAILABLE",
            "disputed": "DISPUTED",
            "closed": "CLOSED_NO_PAY",
        }
        events.append(ev("e3", "2026-09-03T00:00:00Z", kinds[bucket]))
    return claim(cid, instrument=instrument, amount=amount, events=events)


def settled(amount=LARGE, cid="settled", currency="USD", instrument="RTC"):
    row = sample("25", cid=cid, instrument=instrument)
    row["events"].append(ev(
        "settlement", "2026-09-04T00:00:00Z", "SETTLED_CASH",
        settlement_currency=currency, settlement_amount=amount,
    ))
    return row


def fraction_total(amounts):
    """Independent rational oracle, without Decimal arithmetic or formatting."""
    total = sum((Fraction(text) for text in amounts), Fraction(0)) * 10**18
    if total.denominator != 1:
        raise ValueError("test data exceeded the public 18-place contract")
    whole, fraction = divmod(total.numerator, 10**18)
    tail = f"{fraction:018d}".rstrip("0")
    return str(whole) + ("." + tail if tail else "")


def context_snapshot(ctx):
    return (
        ctx.prec, ctx.rounding, ctx.Emin, ctx.Emax, ctx.capitals, ctx.clamp,
        dict(ctx.flags), dict(ctx.traps),
    )


class ExactMoneyTests(unittest.TestCase):
    def exact_bucket(self, bucket):
        out = c.compile_ledger(ledger([sample(bucket=bucket)]))
        self.assertEqual(out["totals_by_instrument"]["USD"][bucket], LARGE)
        self.assertEqual(out["settled_cash_by_currency"], {})
        for other in set(BUCKETS) - {bucket}:
            self.assertEqual(out["totals_by_instrument"]["USD"][other], "0")

    def test_confirmed_bucket_preserves_cents(self):
        self.exact_bucket("accepted_outstanding")

    def test_unconfirmed_bucket_preserves_cents(self):
        self.exact_bucket("accepted_unconfirmed")

    def test_asserted_bucket_preserves_cents(self):
        self.exact_bucket("asserted_hold")

    def test_available_bucket_preserves_cents(self):
        self.exact_bucket("available_not_settled")

    def test_disputed_bucket_preserves_cents(self):
        self.exact_bucket("disputed")

    def test_settlement_preserves_cents_and_currency(self):
        out = c.compile_ledger(ledger([
            settled(), settled("0.09", "second"), settled("3.21", "eur", "EUR"),
        ]))
        self.assertEqual(out["settled_cash_by_currency"], {
            "EUR": "3.21", "USD": "1234567890123456789012345678.1",
        })
        self.assertNotIn("RTC", out["settled_cash_by_currency"])
        self.assertIsNone(out["mixed_currency_sum"])

    def test_many_terms_carry_into_new_digits(self):
        values = ["9999999999999999999999999999.99"] * 1001
        out = c.compile_ledger(ledger([sample(x, cid=f"c{i}") for i, x in enumerate(values)]))
        self.assertEqual(out["totals_by_instrument"]["USD"]["accepted_unconfirmed"], fraction_total(values))

    def test_eighteen_fractional_places_preserved(self):
        values = ["0.000000000000000001", "1234567890123456789012345678.000000000000000009"]
        out = c.compile_ledger(ledger([sample(x, cid=f"c{i}") for i, x in enumerate(values)]))
        self.assertEqual(out["totals_by_instrument"]["USD"]["accepted_unconfirmed"], fraction_total(values))

    def test_more_than_python_integer_string_limit_is_still_exact(self):
        values = ["9" * 5000 + ".99", "0.01"]
        out = c.compile_ledger(ledger([sample(x, cid=f"c{i}") for i, x in enumerate(values)]))
        self.assertEqual(out["totals_by_instrument"]["USD"]["accepted_unconfirmed"], "1" + "0" * 5000)

    def test_low_precision_and_rounding_cannot_change_report(self):
        inp = ledger([sample("123.45"), settled("98.76")])
        with localcontext(Context(prec=100)):
            expected = c.canonical_bytes(c.compile_ledger(inp))
        for precision in (1, 3, 7, 28):
            for rounding in (ROUND_DOWN, ROUND_UP, ROUND_HALF_EVEN):
                with self.subTest(precision=precision, rounding=rounding):
                    with localcontext(Context(prec=precision, rounding=rounding)):
                        self.assertEqual(c.canonical_bytes(c.compile_ledger(inp)), expected)

    def test_tiny_exponent_bounds_and_all_traps_do_not_leak(self):
        inp = ledger([sample(), settled("0.000000000000000001")])
        with localcontext(Context(prec=100)):
            expected = c.compile_ledger(inp)
        with localcontext(Context(prec=1, Emin=-1, Emax=1, clamp=1)) as ctx:
            for signal in ctx.traps:
                ctx.traps[signal] = True
            before = context_snapshot(ctx)
            self.assertEqual(c.compile_ledger(inp), expected)
            self.assertEqual(context_snapshot(ctx), before)

    def test_existing_caller_flags_are_preserved(self):
        with localcontext(Context(prec=3, rounding=ROUND_UP)) as ctx:
            ctx.flags[Inexact] = True
            ctx.flags[Rounded] = True
            before = context_snapshot(ctx)
            c.compile_ledger(ledger([sample(), settled()]))
            self.assertEqual(context_snapshot(ctx), before)

    def test_clean_caller_flags_are_not_set(self):
        with localcontext(Context(prec=3)) as ctx:
            ctx.clear_flags()
            before = context_snapshot(ctx)
            c.compile_ledger(ledger([sample(), settled()]))
            self.assertEqual(context_snapshot(ctx), before)

    def test_cross_context_verification_accepts_unchanged_receipt(self):
        inp = ledger([sample(), settled()])
        with localcontext(Context(prec=100)):
            report = c.compile_ledger(inp)
        with localcontext(Context(prec=3)):
            self.assertTrue(c.verify_ledger(inp, report))
            self.assertTrue(c.verify_json(json.dumps(inp), json.dumps(report)))

    def test_cross_context_verification_still_rejects_tampering(self):
        inp = ledger([sample()])
        report = c.compile_ledger(inp)
        report["totals_by_instrument"]["USD"]["accepted_unconfirmed"] = "1"
        with localcontext(Context(prec=3)):
            self.assertFalse(c.verify_ledger(inp, report))

    def test_input_strings_and_economics_evidence_are_not_rewritten(self):
        inp = ledger([sample("123.4500", "accepted_outstanding")])
        before = copy.deepcopy(inp)
        with localcontext(Context(prec=1)):
            report = c.compile_ledger(inp)
        self.assertEqual(inp, before)
        self.assertEqual(report["claims"][0]["amount"], "123.4500")
        self.assertEqual(report["claims"][0]["entitlement_evidence"]["amount"], "123.4500")
        self.assertEqual(report["totals_by_instrument"]["USD"]["accepted_outstanding"], "123.45")

    def test_separate_buckets_instruments_and_settlement_domains(self):
        rows = [sample(LARGE, bucket, f"usd{i}") for i, bucket in enumerate(BUCKETS)]
        rows += [sample("0.000000000000000001", bucket, f"rtc{i}", "RTC") for i, bucket in enumerate(BUCKETS)]
        rows += [settled("0.07", "settled-usd"), sample("999", "closed", "closed")]
        with localcontext(Context(prec=1)):
            report = c.compile_ledger(ledger(rows))
        for bucket in BUCKETS:
            self.assertEqual(report["totals_by_instrument"]["USD"][bucket], LARGE)
            self.assertEqual(report["totals_by_instrument"]["RTC"][bucket], "0.000000000000000001")
        self.assertEqual(report["settled_cash_by_currency"], {"USD": "0.07"})
        self.assertTrue(all(x is False for x in report["authority"].values()))

    def test_reference_value_never_enters_totals(self):
        row = sample("0.01", instrument="RTC")
        row["reference_valuation"] = {
            "currency": "USD", "amount": LARGE, "source_ref": "fictional-rate",
            "source_digest": "a" * 64,
        }
        with localcontext(Context(prec=1)):
            report = c.compile_ledger(ledger([row]))
        self.assertEqual(set(report["totals_by_instrument"]), {"RTC"})
        self.assertEqual(report["settled_cash_by_currency"], {})
        self.assertFalse(report["reference_valuations_recognized_as_cash"])

    def test_exact_total_is_invariant_to_claim_order_and_identifiers(self):
        rows = [sample(LARGE, cid="a"), sample("0.09", cid="b"), sample("0.000000000000000001", cid="c")]
        for ordered in (rows, list(reversed(rows)), rows[1:] + rows[:1]):
            with localcontext(Context(prec=3)):
                result = c.compile_ledger(ledger(ordered))
            self.assertEqual(result, c.compile_ledger(ledger(rows)))
            self.assertEqual(result["totals_by_instrument"]["USD"]["accepted_unconfirmed"], fraction_total([x["amount"] for x in rows]))

    def test_seeded_rational_oracle_all_domains(self):
        rng = random.Random(16070)
        for index in range(240):
            values = []
            for _ in range(rng.randint(1, 9)):
                whole = str(rng.randrange(1, 10**rng.randint(1, 90)))
                places = rng.randint(0, 18)
                tail = "".join(str(rng.randrange(10)) for _ in range(places))
                values.append(whole + ("." + tail if places else ""))
            bucket = BUCKETS[index % len(BUCKETS)]
            rows = [sample(x, bucket, f"c{i}") for i, x in enumerate(values)]
            rows += [settled(x, f"s{i}", "EUR") for i, x in enumerate(values)]
            expected = fraction_total(values)
            with self.subTest(index=index, bucket=bucket):
                with localcontext(Context(prec=1 + index % 7)):
                    report = c.compile_ledger(ledger(rows))
                self.assertEqual(report["totals_by_instrument"]["USD"][bucket], expected)
                self.assertEqual(report["settled_cash_by_currency"], {"EUR": expected})

    def test_invalid_economics_still_raise_contract_error_under_traps(self):
        for value in (True, 1.5, "NaN", "1e3", "-1", "0", "0.0000000000000000001"):
            with self.subTest(value=value):
                with localcontext(Context(prec=1)) as ctx:
                    for signal in ctx.traps:
                        ctx.traps[signal] = True
                    with self.assertRaises(c.ContractError):
                        c.compile_ledger(ledger([sample(value)]))


if __name__ == "__main__":
    unittest.main()
