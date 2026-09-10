# SPDX-License-Identifier: Apache-2.0
"""Fail-closed zero-exposure certificates for stable SELL-lot ordering.

A one-point pressure proxy can report zero on a rounded price plateau even though
additional hidden same-slot rival units reduce the tested lot's receipt.  This
module certifies a lot as safe to demote only when its own receipt is invariant
for every rival delay from zero through an externally justified public bound.

The helper is deliberately independent of TITAN policy state.  Callers must
supply the exact pinned public quote function and a sound bound on executable
same-slot rival units.  Invalid or non-monotone evidence is a barrier, never a
zero-exposure certificate.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any


PriceFunction = Callable[[str, int, Mapping[str, Any] | None], int | float]
PRODUCTS = frozenset(
    (
        "WHEAT",
        "CARROT",
        "TOMATO",
        "STRAWBERRY",
        "MELON",
        "EGG",
        "MILK",
        "WOOL",
        "FERTILIZER",
    )
)
MAX_CERTIFIED_UNITS = 256

CERTIFIED_ZERO = "CERTIFIED_ZERO"
EXPOSED = "EXPOSED"
BARRIER = "BARRIER"


@dataclass(frozen=True)
class ZeroExposureCertificate:
    """Machine-readable disposition for one inherited SELL lot."""

    status: str
    reason: str
    item: str | None = None
    own_quantity: int | None = None
    rival_bound: int | None = None
    public_inventory: int | None = None
    baseline_receipt: float | None = None
    bound_receipt: float | None = None
    first_exposed_delay: int | None = None
    quote_calls: int = 0

    @property
    def certified(self) -> bool:
        return self.status == CERTIFIED_ZERO

    @property
    def barrier(self) -> bool:
        return self.status == BARRIER

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _certificate(
    status: str,
    reason: str,
    *,
    item: str | None = None,
    own_quantity: int | None = None,
    rival_bound: int | None = None,
    public_inventory: int | None = None,
    baseline_receipt: float | None = None,
    bound_receipt: float | None = None,
    first_exposed_delay: int | None = None,
    quote_calls: int = 0,
) -> ZeroExposureCertificate:
    return ZeroExposureCertificate(
        status=status,
        reason=reason,
        item=item,
        own_quantity=own_quantity,
        rival_bound=rival_bound,
        public_inventory=public_inventory,
        baseline_receipt=baseline_receipt,
        bound_receipt=bound_receipt,
        first_exposed_delay=first_exposed_delay,
        quote_calls=quote_calls,
    )


def _checked_price(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("quote must return a real number")
    result = float(value)
    if not math.isfinite(result) or result < 1:
        raise ValueError("quote must be finite and at least the market floor")
    return result


def certify_zero_exposure(
    order: Any,
    market: Mapping[str, Any],
    quote: PriceFunction,
    rival_bound: Any,
    *,
    max_units: int = MAX_CERTIFIED_UNITS,
) -> ZeroExposureCertificate:
    """Certify receipt invariance for every rival delay in ``[0, rival_bound]``.

    A valid certificate requires an exact three-field positive SELL order, a
    current public quote matching the supplied pinned curve, a finite
    nonincreasing quote curve, and a sound nonnegative integer rival bound.

    For own quantity ``n`` and quote sequence ``p[k] = quote(I + k)``, shifting
    the lot from delay ``q`` to ``q + 1`` changes its receipt by
    ``p[q+n] - p[q]``.  On a nonincreasing curve the receipt is invariant at
    every shift exactly when ``p[q] == p[q+n]`` for every
    ``q < rival_bound``.  The check therefore needs only ``n + rival_bound``
    quote calls rather than a quadratic scan.

    Returns ``BARRIER`` for malformed or unverifiable evidence, ``EXPOSED`` when
    any feasible delay lowers receipt, and ``CERTIFIED_ZERO`` only for complete
    bounded invariance.
    """

    if isinstance(max_units, bool) or not isinstance(max_units, int) or max_units < 1:
        return _certificate(BARRIER, "invalid_max_units")
    if not callable(quote):
        return _certificate(BARRIER, "quote_not_callable")
    if not isinstance(order, list) or len(order) != 3 or order[0] != "SELL":
        return _certificate(BARRIER, "not_exact_sell_order")

    item = order[1]
    quantity = order[2]
    if not isinstance(item, str) or item not in PRODUCTS:
        return _certificate(BARRIER, "unknown_product")
    if (
        isinstance(quantity, bool)
        or not isinstance(quantity, int)
        or quantity < 1
        or quantity > max_units
    ):
        return _certificate(
            BARRIER,
            "invalid_own_quantity",
            item=item,
            own_quantity=quantity if isinstance(quantity, int) and not isinstance(quantity, bool) else None,
        )
    if (
        isinstance(rival_bound, bool)
        or not isinstance(rival_bound, int)
        or rival_bound < 0
        or rival_bound > max_units
    ):
        return _certificate(
            BARRIER,
            "invalid_rival_bound",
            item=item,
            own_quantity=quantity,
            rival_bound=rival_bound if isinstance(rival_bound, int) and not isinstance(rival_bound, bool) else None,
        )
    if not isinstance(market, Mapping):
        return _certificate(
            BARRIER,
            "market_not_mapping",
            item=item,
            own_quantity=quantity,
            rival_bound=rival_bound,
        )

    prices = market.get("prices", {})
    inventories = market.get("inventory", {})
    params = market.get("params")
    if not isinstance(prices, Mapping) or not isinstance(inventories, Mapping):
        return _certificate(
            BARRIER,
            "market_tables_not_mappings",
            item=item,
            own_quantity=quantity,
            rival_bound=rival_bound,
        )
    if params is not None and not isinstance(params, Mapping):
        return _certificate(
            BARRIER,
            "market_params_not_mapping",
            item=item,
            own_quantity=quantity,
            rival_bound=rival_bound,
        )

    inventory = inventories.get(item)
    visible = prices.get(item)
    if isinstance(inventory, bool) or not isinstance(inventory, int) or inventory < 0:
        return _certificate(
            BARRIER,
            "invalid_public_inventory",
            item=item,
            own_quantity=quantity,
            rival_bound=rival_bound,
        )
    try:
        visible_price = _checked_price(visible)
    except (TypeError, ValueError, OverflowError):
        return _certificate(
            BARRIER,
            "invalid_visible_price",
            item=item,
            own_quantity=quantity,
            rival_bound=rival_bound,
            public_inventory=inventory,
        )

    curve: list[float] = []
    try:
        for offset in range(quantity + rival_bound):
            curve.append(_checked_price(quote(item, inventory + offset, params)))
    except (ArithmeticError, LookupError, TypeError, ValueError, OverflowError):
        return _certificate(
            BARRIER,
            "quote_failure",
            item=item,
            own_quantity=quantity,
            rival_bound=rival_bound,
            public_inventory=inventory,
            quote_calls=len(curve),
        )

    common = {
        "item": item,
        "own_quantity": quantity,
        "rival_bound": rival_bound,
        "public_inventory": inventory,
        "quote_calls": len(curve),
    }
    if not curve or curve[0] != visible_price:
        return _certificate(BARRIER, "visible_quote_mismatch", **common)
    if any(left < right for left, right in zip(curve, curve[1:])):
        return _certificate(BARRIER, "quote_curve_not_nonincreasing", **common)

    try:
        baseline = math.fsum(curve[:quantity])
        bound_receipt = math.fsum(curve[rival_bound : rival_bound + quantity])
    except OverflowError:
        return _certificate(BARRIER, "receipt_overflow", **common)
    if not math.isfinite(baseline) or not math.isfinite(bound_receipt):
        return _certificate(BARRIER, "receipt_overflow", **common)

    first_exposed_delay = None
    for delay in range(rival_bound):
        # Sliding one position removes p[delay] and adds p[delay + quantity].
        # Since the curve is nonincreasing, strict inequality is exactly the
        # first bounded delay that lowers the inherited lot's own receipt.
        if curve[delay] > curve[delay + quantity]:
            first_exposed_delay = delay + 1
            break

    if first_exposed_delay is not None:
        return _certificate(
            EXPOSED,
            "receipt_changes_within_bound",
            baseline_receipt=baseline,
            bound_receipt=bound_receipt,
            first_exposed_delay=first_exposed_delay,
            **common,
        )
    return _certificate(
        CERTIFIED_ZERO,
        "receipt_invariant_through_bound",
        baseline_receipt=baseline,
        bound_receipt=bound_receipt,
        **common,
    )


def stable_certified_partition(
    orders: Sequence[Any],
    market: Mapping[str, Any],
    quote: PriceFunction,
    rival_bound: Any,
    *,
    max_units: int = MAX_CERTIFIED_UNITS,
) -> tuple[list[Any], tuple[ZeroExposureCertificate, ...]]:
    """Stably move only certified-zero lots behind exposed lots.

    ``BARRIER`` rows split the list and never move.  Inside each contiguous
    certifiable block, all ``EXPOSED`` lots retain their parent relative order,
    all ``CERTIFIED_ZERO`` lots retain theirs, and only crossings from a
    certified-zero lot to an exposed lot are permitted.  The caller's objects
    are never mutated.
    """

    if isinstance(orders, (str, bytes, bytearray)) or not isinstance(orders, Sequence):
        raise ValueError("orders must be a sequence")
    try:
        result = deepcopy(list(orders))
    except Exception as exc:  # pragma: no cover - exotic caller containers
        raise ValueError("orders cannot be copied") from exc

    certificates = tuple(
        certify_zero_exposure(
            order,
            market,
            quote,
            rival_bound,
            max_units=max_units,
        )
        for order in orders
    )
    start = 0
    while start < len(result):
        if certificates[start].barrier:
            start += 1
            continue
        stop = start + 1
        while stop < len(result) and not certificates[stop].barrier:
            stop += 1
        pairs = list(zip(result[start:stop], certificates[start:stop]))
        ranked = [row for row, cert in pairs if not cert.certified]
        ranked += [row for row, cert in pairs if cert.certified]
        result[start:stop] = ranked
        start = stop
    return result, certificates
