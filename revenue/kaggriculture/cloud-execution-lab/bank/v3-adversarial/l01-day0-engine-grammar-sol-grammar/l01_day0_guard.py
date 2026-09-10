# SPDX-License-Identifier: Apache-2.0
"""Fail-closed admission for the L01 static day-zero product basket.

This module is intentionally narrower than the game's complete market parser.  The
L01 feature is documented as a static BUY_PRODUCT basket, so admission requires
canonical BUY_PRODUCT rows, products that the pinned interpreter actually supports,
and (when a budget is asserted) explicit per-unit price ceilings.  Anything not
proved is rejected without touching the route tape.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping, MutableSequence, Sequence

MAX_MARKET_ORDERS = 10
STARTING_MONEY = 3000
BUY_PRODUCT_ITEMS = frozenset(("WHEAT", "FERTILIZER"))

DAY0_BASKET = (
    ("CARROT", 14),
    ("MELON", 20),
    ("MILK", 40),
    ("STRAWBERRY", 8),
    ("TOMATO", 12),
    ("WHEAT", 2),
)
DAY0_ORDERS = tuple(("BUY_PRODUCT", item, quantity) for item, quantity in DAY0_BASKET)
REJECT_PREFIX = "L01_noop:day0buy_rejected"


@dataclass(frozen=True, order=True)
class Issue:
    """One deterministic reason a proposed static basket is not admissible."""

    index: int
    code: str
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {"index": self.index, "code": self.code, "detail": self.detail}


@dataclass(frozen=True)
class Certificate:
    """Admission result for a candidate day-zero BUY_PRODUCT basket."""

    accepted: bool
    issues: tuple[Issue, ...]
    rows: int
    executable_prefix_rows: int
    worst_case_cost: int | None
    starting_money: int | None

    @property
    def issue_codes(self) -> tuple[str, ...]:
        return tuple(sorted({issue.code for issue in self.issues}))

    @property
    def rejection_reason(self) -> str:
        if self.accepted:
            return ""
        codes = ",".join(self.issue_codes) or "unproved"
        return f"{REJECT_PREFIX}[{codes}]"

    def as_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "issues": [issue.as_dict() for issue in self.issues],
            "rows": self.rows,
            "executable_prefix_rows": self.executable_prefix_rows,
            "worst_case_cost": self.worst_case_cost,
            "starting_money": self.starting_money,
            "rejection_reason": self.rejection_reason,
        }


def _strict_positive_int(value: Any) -> int | None:
    # The official parser calls int(), but policy-generated package data is held to
    # a narrower canonical form so bools, floats, strings, and lossy coercions cannot
    # masquerade as a source-proved quantity.
    if isinstance(value, bool) or type(value) is not int or value <= 0:
        return None
    return value


def _strict_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or type(value) is not int or value < 0:
        return None
    return value


def _row_list(raw: Sequence[Any]) -> list[list[Any]]:
    return [list(row) if isinstance(row, (list, tuple)) else row for row in raw]


def certify_buy_product_basket(
    orders: Sequence[Sequence[Any]] | Any,
    *,
    max_orders: int = MAX_MARKET_ORDERS,
    starting_money: int | None = None,
    unit_price_ceilings: Mapping[str, int] | None = None,
) -> Certificate:
    """Certify a static L01 BUY_PRODUCT basket without executing it.

    ``starting_money`` is optional.  Supplying it asserts a solvency theorem and
    therefore also requires an explicit nonnegative integer ceiling for every
    purchased product.  Missing ceilings fail closed; no current market price is
    guessed from a replay, a label, or a prose claim.
    """

    issues: list[Issue] = []
    if isinstance(max_orders, bool) or type(max_orders) is not int or max_orders < 1:
        issues.append(Issue(-1, "invalid_max_orders", repr(max_orders)))
        max_orders = 1

    if not isinstance(orders, (list, tuple)):
        return Certificate(
            accepted=False,
            issues=(Issue(-1, "orders_not_sequence", type(orders).__name__), *issues),
            rows=0,
            executable_prefix_rows=0,
            worst_case_cost=None,
            starting_money=starting_money,
        )

    rows = len(orders)
    if rows > max_orders:
        issues.append(Issue(max_orders, "prefix_truncation", f"rows={rows};cap={max_orders}"))

    canonical: list[tuple[str, str, int]] = []
    for index, raw in enumerate(orders[:max_orders]):
        if not isinstance(raw, (list, tuple)) or len(raw) != 3:
            issues.append(Issue(index, "malformed_row", repr(raw)))
            continue
        op, item, quantity_raw = raw
        if op != "BUY_PRODUCT":
            issues.append(Issue(index, "unsupported_op", repr(op)))
            continue
        if not isinstance(item, str) or item not in BUY_PRODUCT_ITEMS:
            issues.append(Issue(index, "unsupported_product", repr(item)))
            continue
        quantity = _strict_positive_int(quantity_raw)
        if quantity is None:
            issues.append(Issue(index, "noncanonical_quantity", repr(quantity_raw)))
            continue
        canonical.append((op, item, quantity))

    budget = None
    worst_case_cost: int | None = None
    if starting_money is not None:
        budget = _strict_nonnegative_int(starting_money)
        if budget is None:
            issues.append(Issue(-1, "invalid_starting_money", repr(starting_money)))
        ceilings = unit_price_ceilings if isinstance(unit_price_ceilings, Mapping) else {}
        cost = 0
        cost_bound = True
        for index, (_, item, quantity) in enumerate(canonical):
            ceiling = _strict_nonnegative_int(ceilings.get(item))
            if ceiling is None:
                issues.append(Issue(index, "unbound_price_ceiling", item))
                cost_bound = False
                continue
            cost += quantity * ceiling
        if cost_bound:
            worst_case_cost = cost
            if budget is not None and cost > budget:
                issues.append(Issue(-1, "worst_case_over_budget", f"cost={cost};money={budget}"))

    ordered_issues = tuple(sorted(issues))
    return Certificate(
        accepted=not ordered_issues,
        issues=ordered_issues,
        rows=rows,
        executable_prefix_rows=min(rows, max_orders),
        worst_case_cost=worst_case_cost,
        starting_money=budget if starting_money is not None else None,
    )


def guarded_replace_step0(
    route: MutableSequence[MutableMapping[str, Any]],
    *,
    wanted: Sequence[Sequence[Any]] = DAY0_ORDERS,
    activations: MutableMapping[str, int] | None = None,
    reasons: MutableSequence[str] | None = None,
    max_orders: int = MAX_MARKET_ORDERS,
    starting_money: int | None = STARTING_MONEY,
    unit_price_ceilings: Mapping[str, int] | None = None,
) -> tuple[bool, Certificate]:
    """Replace ``route[0].market`` only after a complete static certificate.

    On rejection this function is object- and byte-behavior preserving: neither the
    route nor the proposed orders are modified.  Repeating a rejected or already
    applied request is idempotent and does not duplicate diagnostics.
    """

    certificate = certify_buy_product_basket(
        wanted,
        max_orders=max_orders,
        starting_money=starting_money,
        unit_price_ceilings=unit_price_ceilings,
    )
    if not certificate.accepted:
        if reasons is not None and certificate.rejection_reason not in reasons:
            reasons.append(certificate.rejection_reason)
        return False, certificate

    if not isinstance(route, MutableSequence) or not route:
        empty = Certificate(
            accepted=False,
            issues=(Issue(-1, "missing_step0", "route has no mutable step zero"),),
            rows=certificate.rows,
            executable_prefix_rows=certificate.executable_prefix_rows,
            worst_case_cost=certificate.worst_case_cost,
            starting_money=certificate.starting_money,
        )
        if reasons is not None and empty.rejection_reason not in reasons:
            reasons.append(empty.rejection_reason)
        return False, empty
    row = route[0]
    if not isinstance(row, MutableMapping):
        bad = Certificate(
            accepted=False,
            issues=(Issue(0, "step0_not_mapping", type(row).__name__),),
            rows=certificate.rows,
            executable_prefix_rows=certificate.executable_prefix_rows,
            worst_case_cost=certificate.worst_case_cost,
            starting_money=certificate.starting_money,
        )
        if reasons is not None and bad.rejection_reason not in reasons:
            reasons.append(bad.rejection_reason)
        return False, bad

    replacement = _row_list(wanted)
    current = row.get("market")
    if current == replacement:
        return False, certificate

    # Commit only after all validation and allocation are complete.
    row["market"] = replacement
    if activations is not None:
        activations["DAY0BUY"] = int(activations.get("DAY0BUY", 0)) + 1
    return True, certificate
