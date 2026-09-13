from __future__ import annotations

import unittest
from datetime import date, timedelta
from decimal import Decimal as D

from buywait.forecast import build_base_cashflows, change_options, infer_recurrences
from buywait.models import FinancialEvent, Profile, PurchaseRequest
from buywait.money import ExchangeBook

BASE = date(2026, 1, 1)


def event(event_id: str, days_ago: int, amount: str, category: str, *, flexibility="fixed", minimum=None):
    dt = BASE - timedelta(days=days_ago)
    return FinancialEvent(
        event_id, "u", "expense", category, category, "debit", D(amount), "USD",
        dt, dt, "settled", None, flexibility, D(minimum) if minimum else None,
    )


def profile():
    return Profile(
        "u", "USD", D("1000"), D("100"), frozenset(), frozenset(),
        frozenset({"streaming"}), frozenset({"streaming"}), frozenset({"full_payment"}), None,
    )


def request():
    return PurchaseRequest("r", "u", BASE, "purchase", D("100"), BASE + timedelta(days=60), False, "")


class RecurrenceTests(unittest.TestCase):
    def test_preserves_ten_day_cadence(self):
        events = [event(f"g{i}", d, "20", "groceries") for i, d in enumerate([50, 40, 30, 20, 10])]
        recs = infer_recurrences(events, profile(), BASE, ExchangeBook([]))
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].period_days, 10)

    def test_preserves_twenty_one_day_cadence(self):
        events = [event(f"d{i}", d, "20", "dining") for i, d in enumerate([105, 84, 63, 42, 21])]
        recs = infer_recurrences(events, profile(), BASE, ExchangeBook([]))
        self.assertEqual(recs[0].period_days, 21)

    def test_reducible_or_stoppable_exposes_both_legal_actions(self):
        events = [event(f"s{i}", d, "30", "streaming", flexibility="reducible_or_stoppable", minimum="10")
                  for i, d in enumerate([90, 60, 30])]
        flows = build_base_cashflows(events, profile(), request(), ExchangeBook([]))
        changes = change_options(profile(), flows)
        self.assertEqual({c.kind for c in changes}, {"stop", "reduce_to"})


if __name__ == "__main__":
    unittest.main()

class EvidenceDirectiveForecastTests(unittest.TestCase):
    def _salary(self, event_id, desc, dt, amount, status="settled", event_type="income"):
        return FinancialEvent(event_id, "u", event_type, desc, "salary", "credit", D(amount), "USD", dt, dt, status, None, "fixed", None)

    def test_sparse_salary_history_bootstraps_from_confirmed_next_salary(self):
        events = [
            self._salary("old", "Prorated first salary", date(2025, 12, 15), "500"),
            self._salary("next", "Next confirmed salary", date(2026, 1, 15), "1000", "scheduled"),
        ]
        recs = infer_recurrences(events, profile(), BASE, ExchangeBook([]))
        salary = [r for r in recs if r.category == "salary"]
        self.assertEqual(len(salary), 1)
        self.assertEqual(salary[0].anchor_date, date(2026, 1, 15))
        self.assertEqual(salary[0].amount, D("1000"))

    def test_stop_directive_ends_all_salary_recurrence(self):
        events = []
        for month in [10, 11, 12]:
            dt = date(2025, month, 15)
            events.append(self._salary(f"p{month}", "Primary", dt, "700"))
        stop = FinancialEvent("evidence:r:stop", "u", "recurrence_stop", "*", "salary", "credit", D("0"), "USD", BASE, BASE, "directive", None, "fixed", None)
        events.append(stop)
        flows = build_base_cashflows(events, profile(), request(), ExchangeBook([]))
        self.assertFalse(any(cf.category == "salary" and cf.date > BASE for cf in flows))

    def test_replace_directive_collapses_household_salary_to_new_total(self):
        events = []
        for month in [10, 11, 12]:
            dt1 = date(2025, month, 15)
            dt2 = date(2025, month, 20)
            events += [self._salary(f"a{month}", "Primary", dt1, "700"), self._salary(f"b{month}", "Second", dt2, "300")]
        repl = FinancialEvent("evidence:r:replace", "u", "recurrence_replace", "*", "salary", "credit", D("800"), "USD", BASE + timedelta(days=14), BASE + timedelta(days=14), "directive", None, "fixed", None)
        events.append(repl)
        flows = build_base_cashflows(events, profile(), request(), ExchangeBook([]))
        salary = [cf for cf in flows if cf.category == "salary" and cf.generated]
        self.assertTrue(salary)
        self.assertTrue(all(cf.amount == D("800") for cf in salary))

    def test_confirmed_one_off_income_is_counted_but_not_repeated(self):
        dt = BASE + timedelta(days=10)
        one = FinancialEvent("invoice", "u", "income", "Confirmed invoice", "invoice", "credit", D("250"), "USD", dt, dt, "scheduled", None, "fixed", None)
        flows = build_base_cashflows([one], profile(), request(), ExchangeBook([]))
        credits = [cf for cf in flows if cf.amount > 0]
        self.assertEqual([(cf.date, cf.amount) for cf in credits], [(dt, D("250"))])
