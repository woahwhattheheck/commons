from __future__ import annotations

import calendar
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from .models import Cashflow, FinancialEvent, Profile, PurchaseRequest, SpendingChange
from .money import ExchangeBook

D = Decimal


@dataclass(frozen=True)
class Recurrence:
    key: str
    period_kind: str  # days | month
    period_days: int | None
    amount: Decimal
    direction: str
    category: str
    description: str
    flexibility: str
    minimum_allowed_amount: Decimal | None
    source_event_id: str
    anchor_date: date

    def dates_after(self, start: date, end: date) -> list[date]:
        out: list[date] = []
        cur = self.anchor_date
        guard = 0
        while cur <= start and guard < 60:
            cur = add_month(cur) if self.period_kind == "month" else cur + timedelta(days=self.period_days or 0)
            guard += 1
        while cur <= end and guard < 80:
            out.append(cur)
            cur = add_month(cur) if self.period_kind == "month" else cur + timedelta(days=self.period_days or 0)
            guard += 1
        return out


def add_month(d: date) -> date:
    year = d.year + (d.month // 12)
    month = (d.month % 12) + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _snap_period(intervals: list[int]) -> tuple[str, int | None] | None:
    if len(intervals) < 2:
        return None
    med = statistics.median(intervals)
    # Monthly commitments vary naturally with calendar length.
    if 26 <= med <= 33 and sum(26 <= x <= 33 for x in intervals) / len(intervals) >= 0.75:
        return ("month", None)
    # Synthetic and real ledgers can contain stable 7/10/14/21-day cadences. Do not
    # force them into weekly/fortnightly buckets; preserve the observed cadence when
    # at least 75% of intervals are within one day of the median.
    if 5 <= med <= 24:
        period = max(1, int(round(med)))
        if sum(abs(x - med) <= 1 for x in intervals) / len(intervals) >= 0.75:
            return ("days", period)
    return None


def _p75(values: list[Decimal]) -> Decimal:
    if not values:
        return D(0)
    vals = sorted(values)
    idx = max(0, min(len(vals) - 1, int((len(vals) - 1) * 0.75 + 0.5)))
    return vals[idx]


def infer_recurrences(
    events: list[FinancialEvent],
    profile: Profile,
    request_date: date,
    exchange: ExchangeBook,
) -> list[Recurrence]:
    """Infer only repeated, settled historical behavior plus a confirmed salary anchor.

    Fixed descriptions are inferred independently. Variable spending is inferred at the
    category level so changing merchant text does not hide weekly groceries/transport.
    """
    usable = [
        e for e in events
        if e.amount is not None
        and e.settlement_date <= request_date
        and e.status == "settled"
        and e.event_type not in {"refund", "investment_value", "recurrence_replace", "recurrence_stop"}
        and e.category not in {"shopping"}  # noisy one-off purchases are not forecast by default
    ]

    groups: dict[str, list[FinancialEvent]] = defaultdict(list)
    for e in usable:
        if e.direction == "credit":
            # Only salary is safe to forecast as recurring income. Other historical
            # credits (invoices, prizes, reimbursements, refunds) remain one-offs unless
            # a confirmed future event explicitly schedules them. Keep household salary
            # streams separate by description so one employer can end without erasing the
            # other.
            if e.category == "salary":
                groups[f"credit:salary:{e.description.lower().strip()}"].append(e)
            continue
        # Stable commitments keep their description. High-frequency living expenses
        # deliberately pool merchant wording at the category level.
        variable = e.category in {"groceries", "transport", "dining", "healthcare", "fuel", "household"}
        key = f"debit:category:{e.category}" if variable else f"debit:item:{e.category}:{e.description.lower().strip()}"
        groups[key].append(e)

    out: list[Recurrence] = []
    for key, group in groups.items():
        group = sorted(group, key=lambda e: e.settlement_date)
        unique_dates = sorted({e.settlement_date for e in group})
        intervals = [(b - a).days for a, b in zip(unique_dates, unique_dates[1:])]
        snapped = _snap_period(intervals)
        min_count = 3 if key.startswith("credit:salary:") else (5 if ":category:" in key else 3)
        if len(group) < min_count or snapped is None:
            continue

        latest = group[-1]
        recent = group[-8:]
        converted = [exchange.convert(e.amount or D(0), e.currency, profile.home_currency, e.settlement_date) for e in recent]
        if latest.direction == "credit":
            amount = converted[-1]
        elif ":category:" in key:
            amount = _p75(converted)
        else:
            amount = converted[-1]

        min_allowed = None
        if latest.minimum_allowed_amount is not None:
            min_allowed = exchange.convert(latest.minimum_allowed_amount, latest.currency, profile.home_currency, latest.settlement_date)

        kind, days = snapped
        out.append(Recurrence(
            key=key, period_kind=kind, period_days=days, amount=amount,
            direction=latest.direction, category=latest.category,
            description=latest.description, flexibility=latest.flexibility,
            minimum_allowed_amount=min_allowed, source_event_id=latest.event_id,
            anchor_date=latest.settlement_date,
        ))

    # Sparse-history bootstrap: one settled salary plus one confirmed scheduled salary is
    # enough to establish a monthly payroll cadence. This occurs for newly started jobs in
    # the supplied data. The explicit scheduled credit is still kept separately; this
    # recurrence begins after it and extends the remaining forecast horizon.
    if not any(r.direction == "credit" and r.category == "salary" for r in out):
        settled_salary = sorted(
            [e for e in events if e.amount is not None and e.direction == "credit" and e.category == "salary" and e.status == "settled" and e.settlement_date <= request_date],
            key=lambda e: e.settlement_date,
        )
        scheduled_salary = sorted(
            [e for e in events if e.amount is not None and e.direction == "credit" and e.category == "salary" and e.status == "scheduled" and e.settlement_date > request_date],
            key=lambda e: e.settlement_date,
        )
        if settled_salary and scheduled_salary:
            nxt = scheduled_salary[0]
            prev = settled_salary[-1]
            gap = (nxt.settlement_date - prev.settlement_date).days
            if 26 <= gap <= 33:
                out.append(Recurrence(
                    key=f"credit:salary:bootstrap:{nxt.event_id}", period_kind="month", period_days=None,
                    amount=exchange.convert(nxt.amount or D(0), nxt.currency, profile.home_currency, nxt.settlement_date),
                    direction="credit", category="salary", description=nxt.description, flexibility="fixed",
                    minimum_allowed_amount=None, source_event_id=nxt.event_id, anchor_date=nxt.settlement_date,
                ))
    return out


def _apply_recurrence_directives(
    recurrences: list[Recurrence],
    events: list[FinancialEvent],
    profile: Profile,
    request_date: date,
    exchange: ExchangeBook,
) -> tuple[list[Recurrence], list[FinancialEvent]]:
    """Apply bounded synthetic directives emitted by the evidence parser.

    `recurrence_replace` means a message explicitly changed an ongoing category (for
    example a persistent salary/rent amount). `recurrence_stop` means the recurrence
    explicitly ended. Directives are data facts only; plan selection remains deterministic.
    """
    directives = [e for e in events if e.event_type in {"recurrence_replace", "recurrence_stop"} and e.status == "directive"]
    current = list(recurrences)
    for d in sorted((x for x in directives if x.event_type == "recurrence_replace"), key=lambda x: (x.settlement_date, x.event_id)):
        # Category-wide replacement is intentional for evidence such as "one household
        # employment ended; remaining confirmed monthly salary is X". A concrete
        # description narrows the replacement when the evidence identifies one item.
        wildcard = d.description.strip() in {"", "*"}
        current = [
            r for r in current
            if not (r.category == d.category and r.direction == d.direction and (wildcard or r.description.lower().strip() == d.description.lower().strip()))
        ]
        if d.amount is None:
            continue
        amount = exchange.convert(d.amount, d.currency, profile.home_currency, d.settlement_date)
        current.append(Recurrence(
            key=f"directive:{d.event_id}", period_kind="month", period_days=None, amount=amount,
            direction=d.direction, category=d.category,
            description=(d.description if not wildcard else d.category), flexibility=d.flexibility or "fixed",
            minimum_allowed_amount=(
                exchange.convert(d.minimum_allowed_amount, d.currency, profile.home_currency, d.settlement_date)
                if d.minimum_allowed_amount is not None else None
            ),
            source_event_id=d.event_id, anchor_date=d.settlement_date,
        ))
    return current, [e for e in directives if e.event_type == "recurrence_stop"]


def _stopped_on(rec: Recurrence, dt: date, stops: list[FinancialEvent]) -> bool:
    for d in stops:
        if d.direction != rec.direction or d.category != rec.category or dt < d.settlement_date:
            continue
        wildcard = d.description.strip() in {"", "*"}
        if wildcard or d.description.lower().strip() == rec.description.lower().strip():
            return True
    return False


def explicit_future_cashflows(
    events: list[FinancialEvent], profile: Profile, request: PurchaseRequest, exchange: ExchangeBook, horizon_end: date
) -> list[Cashflow]:
    out: list[Cashflow] = []
    for e in events:
        if e.amount is None or not (request.request_date <= e.settlement_date <= horizon_end):
            continue
        amount = exchange.convert(e.amount, e.currency, profile.home_currency, e.settlement_date)
        if e.direction == "debit" and e.status in {"pending", "scheduled"}:
            out.append(Cashflow(
                date=e.settlement_date, amount=-amount, event_id=e.event_id, category=e.category,
                description=e.description, flexibility=e.flexibility,
                minimum_allowed_amount=(exchange.convert(e.minimum_allowed_amount, e.currency, profile.home_currency, e.settlement_date) if e.minimum_allowed_amount is not None else None),
                generated=False, source_event_id=e.event_id,
            ))
        elif e.direction == "credit" and e.status == "scheduled" and e.event_type == "income":
            out.append(Cashflow(
                date=e.settlement_date, amount=amount, event_id=e.event_id, category=e.category,
                description=e.description, flexibility="fixed", generated=False, source_event_id=e.event_id,
            ))
    return out


def build_base_cashflows(
    events: list[FinancialEvent], profile: Profile, request: PurchaseRequest, exchange: ExchangeBook, horizon_days: int = 90
) -> list[Cashflow]:
    horizon_end = request.request_date + timedelta(days=horizon_days)
    explicit = explicit_future_cashflows(events, profile, request, exchange, horizon_end)
    recurrences = infer_recurrences(events, profile, request.request_date, exchange)
    recurrences, recurrence_stops = _apply_recurrence_directives(
        recurrences, events, profile, request.request_date, exchange
    )

    # If an explicit scheduled item lands near the projected date for the same category,
    # it replaces the generated occurrence instead of being double counted.
    explicit_by_category: dict[str, list[date]] = defaultdict(list)
    for cf in explicit:
        explicit_by_category[cf.category].append(cf.date)

    generated: list[Cashflow] = []
    recurrence_counts: dict[tuple[str, str], int] = defaultdict(int)
    for item in recurrences:
        recurrence_counts[(item.category, item.direction)] += 1
    for rec in recurrences:
        anchor = rec.anchor_date
        # A known scheduled occurrence can anchor a recurrence. With multiple household
        # salary streams, only bind an explicit event if its description or amount singles
        # out this stream; never shift every salary recurrence to one payment date.
        same_explicit = [cf for cf in explicit if cf.category == rec.category and (cf.amount > 0) == (rec.direction == "credit")]
        if recurrence_counts[(rec.category, rec.direction)] > 1:
            narrowed = [cf for cf in same_explicit if cf.description.lower().strip() == rec.description.lower().strip() or abs(abs(cf.amount) - rec.amount) <= D("0.01")]
            same_explicit = narrowed
        if same_explicit:
            anchor = max(anchor, max(cf.date for cf in same_explicit))
            rec = Recurrence(**{**rec.__dict__, "anchor_date": anchor})
        for dt in rec.dates_after(request.request_date, horizon_end):
            if _stopped_on(rec, dt, recurrence_stops):
                continue
            if any(abs((dt - x).days) <= 3 for x in explicit_by_category.get(rec.category, [])):
                continue
            signed = rec.amount if rec.direction == "credit" else -rec.amount
            generated.append(Cashflow(
                date=dt, amount=signed, event_id=f"forecast:{rec.source_event_id}:{dt.isoformat()}",
                category=rec.category, description=rec.description,
                flexibility=rec.flexibility, minimum_allowed_amount=rec.minimum_allowed_amount,
                generated=True, source_event_id=rec.source_event_id,
            ))
    return sorted(explicit + generated, key=lambda x: (x.date, x.event_id))


def apply_spending_changes(cashflows: list[Cashflow], changes: tuple[SpendingChange, ...]) -> list[Cashflow]:
    stop_ids = {c.event_id for c in changes if c.kind == "stop"}
    reduce = {c.event_id: c.new_amount for c in changes if c.kind == "reduce_to"}
    out: list[Cashflow] = []
    for cf in cashflows:
        source = cf.source_event_id or cf.event_id
        if cf.amount < 0 and source in stop_ids:
            continue
        if cf.amount < 0 and source in reduce and reduce[source] is not None:
            out.append(Cashflow(
                date=cf.date, amount=-reduce[source], event_id=cf.event_id, category=cf.category,
                description=cf.description, flexibility=cf.flexibility,
                minimum_allowed_amount=cf.minimum_allowed_amount, generated=cf.generated,
                source_event_id=cf.source_event_id,
            ))
        else:
            out.append(cf)
    return out


def trajectory(profile: Profile, request_date: date, cashflows: list[Cashflow], end_date: date) -> list[tuple[date, Decimal]]:
    balance = profile.current_available_balance
    rows: list[tuple[date, Decimal]] = [(request_date, balance)]
    daily: dict[date, Decimal] = defaultdict(Decimal)
    for cf in cashflows:
        if request_date <= cf.date <= end_date:
            daily[cf.date] += cf.amount
    for dt in sorted(daily):
        balance += daily[dt]
        rows.append((dt, balance))
    return rows


def min_balance_from_date(rows: list[tuple[date, Decimal]], from_date: date) -> Decimal:
    values = [bal for dt, bal in rows if dt >= from_date]
    if not values:
        return rows[-1][1]
    return min(values)


def amount_safe_on_date(profile: Profile, rows: list[tuple[date, Decimal]], on_date: date, cap: Decimal) -> Decimal:
    margin = min_balance_from_date(rows, on_date) - profile.minimum_balance_to_keep
    if margin <= 0:
        return D(0)
    return min(cap, margin)


def earliest_full_payment_date(
    profile: Profile, rows: list[tuple[date, Decimal]], request: PurchaseRequest, horizon_end: date
) -> date | None:
    # Capacity changes only when a cashflow settles, so testing request day plus event
    # dates is equivalent to scanning all 91 days and is less error-prone around ties.
    dates = sorted({request.request_date, horizon_end, *(dt for dt, _ in rows if request.request_date <= dt <= horizon_end)})
    for dt in dates:
        if amount_safe_on_date(profile, rows, dt, request.requested_amount) >= request.requested_amount:
            return dt
    return None


def change_options(profile: Profile, cashflows: list[Cashflow]) -> list[SpendingChange]:
    """Return one action per recurring source event, respecting user permissions."""
    reps: dict[str, Cashflow] = {}
    for cf in cashflows:
        if cf.amount >= 0 or not cf.generated or not cf.source_event_id:
            continue
        reps.setdefault(cf.source_event_id, cf)
    out: list[SpendingChange] = []
    for source_id, cf in reps.items():
        can_stop = cf.flexibility in {"stoppable", "reducible_or_stoppable"}
        can_reduce = cf.flexibility in {"reducible", "reducible_or_stoppable"}
        if can_stop and cf.category in profile.stoppable_categories and cf.category not in profile.protected_categories:
            out.append(SpendingChange("stop", source_id, cf.category))
        if (
            can_reduce and cf.category in profile.reducible_categories
            and cf.category not in profile.protected_categories and cf.minimum_allowed_amount is not None
            and cf.minimum_allowed_amount < -cf.amount
        ):
            out.append(SpendingChange("reduce_to", source_id, cf.category, cf.minimum_allowed_amount))
    # Most savings first makes bounded combination search efficient and deterministic.
    def savings(c: SpendingChange) -> Decimal:
        cf = reps[c.event_id]
        return -cf.amount if c.kind == "stop" else (-cf.amount - (c.new_amount or D(0)))
    return sorted(out, key=lambda c: (-savings(c), c.event_id))
