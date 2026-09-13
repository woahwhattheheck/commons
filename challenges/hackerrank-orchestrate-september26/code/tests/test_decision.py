from __future__ import annotations

import unittest
from datetime import date, timedelta
from decimal import Decimal as D

from buywait.decision import DecisionEngine
from buywait.models import FinancialEvent, PaymentOption, Profile, PurchaseRequest
from buywait.money import ExchangeBook

BASE = date(2026, 1, 1)


def profile(**kw):
    values = dict(
        user_id="u", home_currency="USD", current_available_balance=D("1000"),
        minimum_balance_to_keep=D("200"), financial_priorities=frozenset(),
        protected_categories=frozenset({"rent"}), reducible_categories=frozenset(),
        stoppable_categories=frozenset(), accepted_payment_methods=frozenset({"full_payment"}),
        max_installment_months=None,
    )
    values.update(kw)
    return Profile(**values)


def request(amount="600", *, partial=False, deadline_days=60):
    return PurchaseRequest(
        request_id="r", user_id="u", request_date=BASE, request_type="purchase",
        requested_amount=D(amount), desired_completion_date=BASE + timedelta(days=deadline_days),
        allows_partial_payment=partial, request_text="test",
    )


def event(event_id, *, days, amount, direction="debit", status="pending", category="other", desc="event", event_type="expense", flexibility="fixed", min_allowed=None):
    return FinancialEvent(
        event_id=event_id, user_id="u", event_type=event_type, description=desc,
        category=category, direction=direction, amount=D(amount), currency="USD",
        event_date=BASE + timedelta(days=days), settlement_date=BASE + timedelta(days=days),
        status=status, linked_event_id=None, flexibility=flexibility,
        minimum_allowed_amount=D(min_allowed) if min_allowed is not None else None,
    )


def historical(event_id, d, amount, *, category, desc, flexibility="fixed", min_allowed=None):
    dt = BASE - timedelta(days=d)
    return FinancialEvent(
        event_id=event_id, user_id="u", event_type="subscription" if flexibility == "stoppable" else "expense",
        description=desc, category=category, direction="debit", amount=D(amount), currency="USD",
        event_date=dt, settlement_date=dt, status="settled", linked_event_id=None,
        flexibility=flexibility, minimum_allowed_amount=D(min_allowed) if min_allowed is not None else None,
    )


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.engine = DecisionEngine(ExchangeBook([]))

    def test_pending_debit_reduces_safe_today(self):
        d = self.engine.decide(
            profile=profile(), request=request("600"),
            events=[event("p", days=10, amount="300")], options=[],
        )
        self.assertEqual(d.amount_safe_to_pay, D("500"))
        self.assertEqual(d.affordability_status, "not_affordable")

    def test_wait_until_confirmed_salary(self):
        events = [
            event("p", days=5, amount="300"),
            event("s", days=10, amount="600", direction="credit", status="scheduled", category="salary", event_type="income"),
        ]
        d = self.engine.decide(profile=profile(), request=request("900"), events=events, options=[])
        self.assertEqual(d.amount_safe_to_pay, D("500"))
        self.assertEqual(d.recommended_payment_method, "wait")
        self.assertEqual(d.earliest_date_for_full_payment, BASE + timedelta(days=10))

    def test_partial_beats_wait_when_equal_cost_and_starts_earlier(self):
        p = profile(accepted_payment_methods=frozenset({"full_payment", "partial_payment"}))
        r = request("900", partial=True)
        events = [
            event("p", days=5, amount="300"),
            event("s", days=10, amount="600", direction="credit", status="scheduled", category="salary", event_type="income"),
        ]
        d = self.engine.decide(profile=p, request=r, events=events, options=[])
        self.assertEqual(d.recommended_payment_method, "partial_payment")
        self.assertTrue(d.payment_plan.startswith(f"{BASE.isoformat()}:500|"))

    def test_installment_option_selected_when_only_accepted_method(self):
        p = profile(
            current_available_balance=D("1500"), minimum_balance_to_keep=D("300"),
            accepted_payment_methods=frozenset({"installments"}), max_installment_months=6,
        )
        opt = PaymentOption(
            payment_option_id="payment_option_10", request_id="r", payment_method="installments",
            payment_amount=D("300"), number_of_payments=3,
            first_payment_date=BASE + timedelta(days=1), payment_frequency_days=20,
            financing_fee=D("0"), total_payable_amount=D("900"),
        )
        d = self.engine.decide(profile=p, request=request("900"), events=[], options=[opt])
        self.assertEqual(d.recommended_payment_method, "installments")
        self.assertEqual(d.affordability_status, "affordable_with_plan")

    def test_spending_change_can_unlock_full_payment(self):
        p = profile(
            stoppable_categories=frozenset({"streaming"}),
            accepted_payment_methods=frozenset({"full_payment"}),
        )
        hist = [
            historical("e1", 91, "150", category="streaming", desc="Family streaming", flexibility="stoppable"),
            historical("e2", 61, "150", category="streaming", desc="Family streaming", flexibility="stoppable"),
            historical("e3", 31, "150", category="streaming", desc="Family streaming", flexibility="stoppable"),
        ]
        d = self.engine.decide(profile=p, request=request("500"), events=hist, options=[])
        self.assertEqual(d.amount_safe_to_pay, D("350"))
        self.assertEqual(d.recommended_payment_method, "full_payment")
        self.assertEqual(d.affordability_status, "affordable_with_plan")
        self.assertTrue(d.spending_changes_needed.startswith("stop:e3"))


    def test_cancelled_debit_is_ignored(self):
        events = [event("cancelled", days=2, amount="700", status="cancelled")]
        d = self.engine.decide(profile=profile(), request=request("800"), events=events, options=[])
        self.assertEqual(d.amount_safe_to_pay, D("800"))
        self.assertEqual(d.recommended_payment_method, "full_payment")

    def test_failed_debit_is_ignored(self):
        events = [event("failed", days=2, amount="700", status="failed")]
        d = self.engine.decide(profile=profile(), request=request("800"), events=events, options=[])
        self.assertEqual(d.amount_safe_to_pay, D("800"))

    def test_cheapest_safe_installment_wins(self):
        p = profile(current_available_balance=D("1300"), minimum_balance_to_keep=D("200"),
                    accepted_payment_methods=frozenset({"installments"}), max_installment_months=12)
        opts = [
            PaymentOption("payment_option_20", "r", "installments", D("250"), 4, BASE, 20, D("100"), D("1000")),
            PaymentOption("payment_option_21", "r", "installments", D("225"), 4, BASE, 20, D("0"), D("900")),
        ]
        d = self.engine.decide(profile=p, request=request("900"), events=[], options=opts)
        self.assertIn(":225", d.payment_plan)

    def test_installment_over_user_month_limit_is_rejected(self):
        p = profile(current_available_balance=D("2000"), minimum_balance_to_keep=D("200"),
                    accepted_payment_methods=frozenset({"installments"}), max_installment_months=2)
        opt = PaymentOption("payment_option_30", "r", "installments", D("300"), 3, BASE, 30, D("0"), D("900"))
        d = self.engine.decide(profile=p, request=request("900"), events=[], options=[opt])
        self.assertEqual(d.recommended_payment_method, "not_recommended")

    def test_reduce_to_minimum_can_unlock_request(self):
        p = profile(reducible_categories=frozenset({"dining"}), accepted_payment_methods=frozenset({"full_payment"}))
        hist = [
            historical("d1", 70, "200", category="dining", desc="Food", flexibility="reducible", min_allowed="50"),
            historical("d2", 56, "200", category="dining", desc="Food", flexibility="reducible", min_allowed="50"),
            historical("d3", 42, "200", category="dining", desc="Food", flexibility="reducible", min_allowed="50"),
            historical("d4", 28, "200", category="dining", desc="Food", flexibility="reducible", min_allowed="50"),
            historical("d5", 14, "200", category="dining", desc="Food", flexibility="reducible", min_allowed="50"),
        ]
        d = self.engine.decide(profile=p, request=request("500"), events=hist, options=[])
        self.assertEqual(d.affordability_status, "affordable_with_plan")
        self.assertTrue(d.spending_changes_needed.startswith("reduce_to:d5:50"))

    def test_protected_flexible_category_cannot_be_changed(self):
        p = profile(protected_categories=frozenset({"streaming"}), stoppable_categories=frozenset({"streaming"}))
        hist = [
            historical("e1", 91, "150", category="streaming", desc="Family streaming", flexibility="stoppable"),
            historical("e2", 61, "150", category="streaming", desc="Family streaming", flexibility="stoppable"),
            historical("e3", 31, "150", category="streaming", desc="Family streaming", flexibility="stoppable"),
        ]
        d = self.engine.decide(profile=p, request=request("500"), events=hist, options=[])
        self.assertEqual(d.recommended_payment_method, "not_recommended")
        self.assertEqual(d.spending_changes_needed, "none")
    def test_pending_credit_is_not_counted(self):
        events = [event("refund", days=2, amount="1000", direction="credit", status="pending", category="refund", event_type="refund")]
        d = self.engine.decide(profile=profile(), request=request("900"), events=events, options=[])
        self.assertEqual(d.amount_safe_to_pay, D("800"))
        self.assertEqual(d.recommended_payment_method, "not_recommended")


class ExchangeTests(unittest.TestCase):
    def test_dated_direct_rate(self):
        b = ExchangeBook([{"rate_date": "2026-01-01", "from_currency": "EUR", "to_currency": "USD", "rate": "1.2"}])
        self.assertEqual(b.convert(D("10"), "EUR", "USD", BASE), D("12.0"))


if __name__ == "__main__":
    unittest.main()
