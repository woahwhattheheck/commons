from __future__ import annotations

import itertools
from datetime import date, timedelta
from decimal import Decimal

from .forecast import (
    amount_safe_on_date,
    apply_spending_changes,
    build_base_cashflows,
    change_options,
    earliest_full_payment_date,
    trajectory,
)
from .models import (
    Candidate,
    Decision,
    FinancialEvent,
    Payment,
    PaymentOption,
    Profile,
    PurchaseRequest,
    SpendingChange,
    format_decimal,
    render_plan,
)
from .money import ExchangeBook

D = Decimal


class DecisionEngine:
    def __init__(self, exchange: ExchangeBook, horizon_days: int = 90):
        self.exchange = exchange
        self.horizon_days = horizon_days

    def decide(
        self,
        *,
        profile: Profile,
        request: PurchaseRequest,
        events: list[FinancialEvent],
        options: list[PaymentOption],
    ) -> Decision:
        horizon_end = request.request_date + timedelta(days=self.horizon_days)
        base_cashflows = build_base_cashflows(events, profile, request, self.exchange, self.horizon_days)
        base_rows = trajectory(profile, request.request_date, base_cashflows, horizon_end)
        safe_today = amount_safe_on_date(profile, base_rows, request.request_date, request.requested_amount)
        earliest = earliest_full_payment_date(profile, base_rows, request, horizon_end)

        candidates = self._candidates(
            profile=profile,
            request=request,
            options=options,
            cashflows=base_cashflows,
            base_safe_today=safe_today,
            base_earliest=earliest,
            horizon_end=horizon_end,
        )

        if candidates:
            chosen = min(candidates, key=self._rank_key)
            status = self._status(chosen, request)
            changes_text = "none" if not chosen.changes else "|".join(c.render() for c in chosen.changes)
            return Decision(
                request_id=request.request_id,
                amount_safe_to_pay=safe_today,
                affordability_status=status,
                recommended_payment_method=chosen.method,
                payment_plan=render_plan(chosen.payments),
                earliest_date_for_full_payment=earliest,
                spending_changes_needed=changes_text,
                decision_explanation=self._explain(profile, request, chosen, status, safe_today, earliest),
            )

        return Decision(
            request_id=request.request_id,
            amount_safe_to_pay=safe_today,
            affordability_status="not_affordable",
            recommended_payment_method="not_recommended",
            payment_plan="none",
            earliest_date_for_full_payment=earliest,
            spending_changes_needed="none",
            decision_explanation=self._not_affordable_explain(profile, request, safe_today, earliest),
        )

    def _candidates(
        self,
        *,
        profile: Profile,
        request: PurchaseRequest,
        options: list[PaymentOption],
        cashflows,
        base_safe_today: Decimal,
        base_earliest: date | None,
        horizon_end: date,
    ) -> list[Candidate]:
        out: list[Candidate] = []

        # No-change plans always outrank equivalent plans requiring lifestyle changes.
        out.extend(self._plans_for_changes(
            profile, request, options, cashflows, (), base_safe_today, base_earliest, horizon_end
        ))

        change_pool = change_options(profile, cashflows)
        # Search at most three changes as required by the challenge. The pool is normally
        # tiny; cap it defensively so pathological inputs cannot explode combinations.
        change_pool = change_pool[:10]
        for n in range(1, min(3, len(change_pool)) + 1):
            for combo in itertools.combinations(change_pool, n):
                if self._valid_change_combo(combo):
                    out.extend(self._plans_for_changes(
                        profile, request, options, cashflows, combo,
                        base_safe_today, base_earliest, horizon_end,
                    ))
        return out

    @staticmethod
    def _valid_change_combo(changes: tuple[SpendingChange, ...]) -> bool:
        ids = [c.event_id for c in changes]
        if len(ids) != len(set(ids)):
            return False
        # stop/reduce of the same category can be legitimate if they are distinct recurring
        # commitments, but the exact same source event is already ruled out above.
        return True

    def _plans_for_changes(
        self,
        profile: Profile,
        request: PurchaseRequest,
        options: list[PaymentOption],
        cashflows,
        changes: tuple[SpendingChange, ...],
        base_safe_today: Decimal,
        base_earliest: date | None,
        horizon_end: date,
    ) -> list[Candidate]:
        flows = apply_spending_changes(cashflows, changes)
        rows = trajectory(profile, request.request_date, flows, horizon_end)
        out: list[Candidate] = []

        def add_if_safe(candidate: Candidate) -> None:
            if candidate.completion_date > request.desired_completion_date:
                return
            if candidate.start_date < request.request_date:
                return
            safe, min_seen = self._simulate_candidate(profile, flows, request, candidate, horizon_end)
            candidate.safe = safe
            candidate.min_balance_seen = min_seen
            if safe:
                out.append(candidate)

        if "full_payment" in profile.accepted_payment_methods:
            add_if_safe(Candidate(
                method="full_payment",
                payments=[Payment(request.request_date, request.requested_amount)],
                total_paid=request.requested_amount,
                changes=changes,
            ))

            # Waiting is a separate recommended method. Spending-change-assisted waits are
            # intentionally not generated: if changes are necessary, the result is a plan,
            # not a pure "affordable later" recommendation.
            if not changes:
                earliest = base_earliest
                if earliest and earliest > request.request_date and earliest <= request.desired_completion_date:
                    add_if_safe(Candidate(
                        method="wait",
                        payments=[Payment(earliest, request.requested_amount)],
                        total_paid=request.requested_amount,
                    ))

        if (
            request.allows_partial_payment
            and "partial_payment" in profile.accepted_payment_methods
            and D(0) < base_safe_today < request.requested_amount
            and base_earliest is not None
            and base_earliest <= request.desired_completion_date
        ):
            add_if_safe(Candidate(
                method="partial_payment",
                payments=[
                    Payment(request.request_date, base_safe_today),
                    Payment(base_earliest, request.requested_amount - base_safe_today),
                ],
                total_paid=request.requested_amount,
                changes=changes,
            ))

        if "installments" in profile.accepted_payment_methods:
            for option in options:
                if option.payment_method != "installments":
                    continue
                if profile.max_installment_months is not None and option.number_of_payments > profile.max_installment_months:
                    continue
                if not option.payment_frequency_days or option.number_of_payments < 1:
                    continue
                payments = [
                    Payment(option.first_payment_date + timedelta(days=option.payment_frequency_days * i), option.payment_amount)
                    for i in range(option.number_of_payments)
                ]
                add_if_safe(Candidate(
                    method="installments", payments=payments,
                    total_paid=option.total_payable_amount,
                    changes=changes, payment_option_id=option.payment_option_id,
                ))

        return out

    @staticmethod
    def _simulate_candidate(profile: Profile, flows, request: PurchaseRequest, candidate: Candidate, horizon_end: date) -> tuple[bool, Decimal]:
        end = max(horizon_end, candidate.completion_date)
        daily: dict[date, Decimal] = {}
        for cf in flows:
            if request.request_date <= cf.date <= end:
                daily[cf.date] = daily.get(cf.date, D(0)) + cf.amount
        for p in candidate.payments:
            daily[p.date] = daily.get(p.date, D(0)) - p.amount
        balance = profile.current_available_balance
        min_seen = balance
        for dt in sorted(daily):
            balance += daily[dt]
            min_seen = min(min_seen, balance)
            if balance < profile.minimum_balance_to_keep:
                return False, min_seen
        return True, min_seen

    @staticmethod
    def _rank_key(c: Candidate):
        option_num = 10**9
        if c.payment_option_id:
            try:
                option_num = int(c.payment_option_id.rsplit("_", 1)[-1])
            except ValueError:
                option_num = 10**9
        return (
            1 if c.changes else 0,
            c.total_paid,
            c.start_date,
            len(c.payments),
            option_num,
            c.method,
        )

    @staticmethod
    def _status(c: Candidate, request: PurchaseRequest) -> str:
        if c.method == "full_payment" and c.start_date == request.request_date and not c.changes:
            return "affordable_now"
        if c.method == "wait" and not c.changes:
            return "affordable_later"
        return "affordable_with_plan"

    @staticmethod
    def _explain(
        profile: Profile,
        request: PurchaseRequest,
        c: Candidate,
        status: str,
        safe_today: Decimal,
        earliest: date | None,
    ) -> str:
        cur = profile.home_currency
        floor = format_decimal(profile.minimum_balance_to_keep)
        req = format_decimal(request.requested_amount)
        min_seen = format_decimal(c.min_balance_seen or profile.minimum_balance_to_keep)
        change_prefix = ""
        if c.changes:
            rendered = []
            for ch in c.changes:
                if ch.kind == "stop":
                    rendered.append(f"stop {ch.category}")
                else:
                    rendered.append(f"reduce {ch.category} to {cur} {format_decimal(ch.new_amount or D(0))}")
            change_prefix = "; ".join(rendered).capitalize() + ", then "

        if c.method == "full_payment":
            return f"{change_prefix}pay {cur} {req} in full on {c.start_date.isoformat()}. The 90-day projection stays at or above the {cur} {floor} minimum (lowest {cur} {min_seen})."
        if c.method == "wait":
            return f"Wait until {c.start_date.isoformat()}, then pay {cur} {req} in full. Paying the full amount earlier is not safe while preserving the {cur} {floor} minimum."
        if c.method == "partial_payment":
            first, second = c.payments
            return f"{change_prefix}pay {cur} {format_decimal(first.amount)} now and {cur} {format_decimal(second.amount)} on {second.date.isoformat()}. This completes the request by the deadline while protecting the {cur} {floor} minimum."
        if c.method == "installments":
            first = c.payments[0]
            return f"{change_prefix}use {len(c.payments)} installments of {cur} {format_decimal(first.amount)}, starting {first.date.isoformat()}. The plan completes by the deadline and keeps at least the {cur} {floor} minimum protected."
        return "A safe eligible plan is available."

    @staticmethod
    def _not_affordable_explain(profile: Profile, request: PurchaseRequest, safe_today: Decimal, earliest: date | None) -> str:
        cur = profile.home_currency
        req = format_decimal(request.requested_amount)
        safe = format_decimal(safe_today)
        floor = format_decimal(profile.minimum_balance_to_keep)
        if safe_today > D(0):
            return f"Do not proceed with the {cur} {req} request. Although {cur} {safe} is safe today, no eligible plan completes the full amount by {request.desired_completion_date.isoformat()} while protecting the {cur} {floor} minimum."
        return f"Do not proceed with the {cur} {req} request by {request.desired_completion_date.isoformat()}. No eligible plan keeps the {cur} {floor} minimum protected."
