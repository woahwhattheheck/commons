"""Fail-closed pressure ordering guarded by exact receipt-delay certificates.

This module is an additive candidate carrier. It does not mutate the canonical
TITAN runtime. The central rule is deliberately narrow: a pressure-positive
SELL lot may cross an earlier non-positive lot only when the earlier lot's own
receipt is proven invariant across the complete bounded stock-delay window.

The certificate uses the canonical quote callback supplied by the caller. It
first validates that every quote in the window is an integer, at least one, and
nonincreasing. Under that validated monotonicity, equality of the sale receipt
at the two endpoints is equivalent to equality at every integer delay.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

PRODUCTS: Final[tuple[str, ...]] = (
    "WHEAT",
    "CORN",
    "CARROT",
    "TOMATO",
    "MELON",
    "EGG",
    "MILK",
    "WOOL",
)

PriceByStock = Callable[[str, int], int]
_MISSING = object()


@dataclass(frozen=True)
class DelayCertificate:
    """Receipt-invariance verdict for one SELL lot."""

    safe: bool
    reason: str
    product: str | None
    quantity: int | None
    stock: int | None
    max_delay: int | None
    baseline_receipt: int | None
    endpoint_receipt: int | None
    checked_quotes: int


@dataclass(frozen=True)
class LotDecision:
    """Ordering decision for one original action row."""

    index: int
    kind: str
    product: str | None
    quantity: int | None
    pressure: float | None
    crossed_same_product_units: int
    certificate: DelayCertificate | None


@dataclass(frozen=True)
class PartitionResult:
    """Immutable result plus enough evidence to audit every crossing."""

    actions: tuple[object, ...]
    decisions: tuple[LotDecision, ...]
    changed: bool


def _safe_get(mapping: Mapping[object, object], key: object) -> object:
    try:
        return mapping.get(key, _MISSING)
    except Exception:
        return _MISSING


def _strict_nonnegative_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _strict_positive_int(value: object) -> int | None:
    parsed = _strict_nonnegative_int(value)
    if parsed is None or parsed == 0:
        return None
    return parsed


def _parse_sell(row: object) -> tuple[str, int] | None:
    if not isinstance(row, Mapping):
        return None
    action = _safe_get(row, "action")
    product = _safe_get(row, "type")
    quantity = _strict_positive_int(_safe_get(row, "quantity"))
    if action != "SELL" or not isinstance(product, str):
        return None
    if product not in PRODUCTS or quantity is None:
        return None
    return product, quantity


def _pressure_value(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        parsed = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _bound_for_product(max_rival_units: object, product: str) -> int | None:
    raw = (
        _safe_get(max_rival_units, product)
        if isinstance(max_rival_units, Mapping)
        else max_rival_units
    )
    return _strict_nonnegative_int(raw)


def _checked_quote(
    price_by_stock: PriceByStock,
    product: str,
    stock: int,
) -> int | None:
    try:
        quote = price_by_stock(product, stock)
    except Exception:
        return None
    if isinstance(quote, bool) or not isinstance(quote, int) or quote < 1:
        return None
    return quote


def exact_sale_receipt(
    product: object,
    stock: object,
    quantity: object,
    price_by_stock: PriceByStock,
) -> int | None:
    """Return the exact per-unit sale receipt, or ``None`` on invalid input."""

    if not isinstance(product, str) or product not in PRODUCTS:
        return None
    parsed_stock = _strict_nonnegative_int(stock)
    parsed_quantity = _strict_positive_int(quantity)
    if parsed_stock is None or parsed_quantity is None:
        return None

    total = 0
    for offset in range(parsed_quantity):
        quote = _checked_quote(price_by_stock, product, parsed_stock + offset)
        if quote is None:
            return None
        total += quote
    return total


def exhaustive_delay_invariant(
    product: object,
    stock: object,
    quantity: object,
    max_delay: object,
    price_by_stock: PriceByStock,
) -> bool:
    """Reference oracle: compare the exact receipt at every integer delay."""

    parsed_stock = _strict_nonnegative_int(stock)
    parsed_quantity = _strict_positive_int(quantity)
    parsed_delay = _strict_nonnegative_int(max_delay)
    if (
        not isinstance(product, str)
        or product not in PRODUCTS
        or parsed_stock is None
        or parsed_quantity is None
        or parsed_delay is None
    ):
        return False

    baseline = exact_sale_receipt(
        product,
        parsed_stock,
        parsed_quantity,
        price_by_stock,
    )
    if baseline is None:
        return False
    for delay in range(1, parsed_delay + 1):
        receipt = exact_sale_receipt(
            product,
            parsed_stock + delay,
            parsed_quantity,
            price_by_stock,
        )
        if receipt is None or receipt != baseline:
            return False
    return True


def certify_delay_invariance(
    product: object,
    stock: object,
    quantity: object,
    max_delay: object,
    price_by_stock: PriceByStock,
) -> DelayCertificate:
    """Certify exact own-receipt invariance through a bounded stock delay.

    A nonincreasing quote window is checked explicitly. Let ``R(d)`` be the
    receipt for this lot after ``d`` earlier same-product units. The validated
    quote monotonicity implies ``R(0) >= R(d) >= R(max_delay)``. Therefore
    endpoint equality proves equality for every integer delay in the window.
    """

    parsed_product = (
        product if isinstance(product, str) and product in PRODUCTS else None
    )
    parsed_stock = _strict_nonnegative_int(stock)
    parsed_quantity = _strict_positive_int(quantity)
    parsed_delay = _strict_nonnegative_int(max_delay)
    if (
        parsed_product is None
        or parsed_stock is None
        or parsed_quantity is None
        or parsed_delay is None
    ):
        return DelayCertificate(
            False,
            "invalid_input",
            parsed_product,
            parsed_quantity,
            parsed_stock,
            parsed_delay,
            None,
            None,
            0,
        )

    quotes: list[int] = []
    previous: int | None = None
    window_length = parsed_quantity + parsed_delay
    for offset in range(window_length):
        quote = _checked_quote(
            price_by_stock,
            parsed_product,
            parsed_stock + offset,
        )
        if quote is None:
            return DelayCertificate(
                False,
                "invalid_quote",
                parsed_product,
                parsed_quantity,
                parsed_stock,
                parsed_delay,
                None,
                None,
                len(quotes),
            )
        if previous is not None and quote > previous:
            return DelayCertificate(
                False,
                "nonmonotone_quote_window",
                parsed_product,
                parsed_quantity,
                parsed_stock,
                parsed_delay,
                None,
                None,
                len(quotes) + 1,
            )
        quotes.append(quote)
        previous = quote

    baseline = sum(quotes[:parsed_quantity])
    endpoint = sum(quotes[parsed_delay : parsed_delay + parsed_quantity])
    safe = baseline == endpoint
    return DelayCertificate(
        safe,
        "invariant" if safe else "receipt_changes_with_delay",
        parsed_product,
        parsed_quantity,
        parsed_stock,
        parsed_delay,
        baseline,
        endpoint,
        len(quotes),
    )


def _known_parent_stocks(
    actions: Sequence[object],
    inventory: Mapping[str, object],
) -> list[int | None]:
    """Stock before each parent lot, excluding all hidden rival supply."""

    running: dict[str, int | None] = {}
    for product in PRODUCTS:
        running[product] = _strict_nonnegative_int(_safe_get(inventory, product))

    result: list[int | None] = []
    for row in actions:
        parsed = _parse_sell(row)
        if parsed is None:
            result.append(None)
            continue
        product, quantity = parsed
        before = running[product]
        result.append(before)
        if before is not None:
            running[product] = before + quantity
    return result


def _rightward_promoted_units(
    actions: Sequence[object],
    pressure_by_product: Mapping[str, object],
) -> list[int]:
    """Conservative own-stock delay from promoted same-product lots to the right."""

    promoted_suffix = {product: 0 for product in PRODUCTS}
    result = [0] * len(actions)
    for index in range(len(actions) - 1, -1, -1):
        parsed = _parse_sell(actions[index])
        if parsed is None:
            promoted_suffix = {product: 0 for product in PRODUCTS}
            continue
        product, quantity = parsed
        result[index] = promoted_suffix[product]
        pressure = _pressure_value(_safe_get(pressure_by_product, product))
        if pressure is not None and pressure > 0:
            promoted_suffix[product] += quantity
    return result


def certified_pressure_partition(
    actions: Sequence[object],
    *,
    pressure_by_product: Mapping[str, object],
    inventory: Mapping[str, object],
    max_rival_units: object,
    price_by_stock: PriceByStock,
) -> PartitionResult:
    """Stable-partition pressure-positive lots across certified-safe lots only.

    Every malformed row, malformed pressure, invalid inventory/bound, or failed
    certificate is a hard ordering barrier. Within each barrier-free segment,
    pressure-positive lots are stably promoted and certified non-positive lots
    are stably demoted. No row object is mutated.
    """

    try:
        original = list(actions)
    except Exception:
        return PartitionResult((), (), False)
    if not isinstance(pressure_by_product, Mapping) or not isinstance(
        inventory, Mapping
    ):
        decisions = tuple(
            LotDecision(index, "barrier", None, None, None, 0, None)
            for index in range(len(original))
        )
        return PartitionResult(tuple(original), decisions, False)

    known_stocks = _known_parent_stocks(original, inventory)
    crossed_units = _rightward_promoted_units(original, pressure_by_product)

    kinds: list[str] = []
    decisions: list[LotDecision] = []
    for index, row in enumerate(original):
        parsed = _parse_sell(row)
        if parsed is None:
            kinds.append("barrier")
            decisions.append(
                LotDecision(index, "barrier", None, None, None, 0, None)
            )
            continue

        product, quantity = parsed
        pressure = _pressure_value(_safe_get(pressure_by_product, product))
        if pressure is None:
            kinds.append("barrier")
            decisions.append(
                LotDecision(
                    index,
                    "barrier",
                    product,
                    quantity,
                    None,
                    crossed_units[index],
                    None,
                )
            )
            continue

        if pressure > 0:
            kinds.append("promoted")
            decisions.append(
                LotDecision(
                    index,
                    "promoted",
                    product,
                    quantity,
                    pressure,
                    crossed_units[index],
                    None,
                )
            )
            continue

        bound = _bound_for_product(max_rival_units, product)
        stock = known_stocks[index]
        if bound is None or stock is None:
            certificate = DelayCertificate(
                False,
                "invalid_bound_or_inventory",
                product,
                quantity,
                stock,
                bound,
                None,
                None,
                0,
            )
        else:
            certificate = certify_delay_invariance(
                product,
                stock,
                quantity,
                bound + crossed_units[index],
                price_by_stock,
            )

        kind = "demotable" if certificate.safe else "barrier"
        kinds.append(kind)
        decisions.append(
            LotDecision(
                index,
                kind,
                product,
                quantity,
                pressure,
                crossed_units[index],
                certificate,
            )
        )

    entries = [(index, row, kinds[index]) for index, row in enumerate(original)]
    output = list(entries)
    start = 0
    while start < len(output):
        if output[start][2] == "barrier":
            start += 1
            continue
        stop = start + 1
        while stop < len(output) and output[stop][2] != "barrier":
            stop += 1
        segment = output[start:stop]
        promoted = [entry for entry in segment if entry[2] == "promoted"]
        demotable = [entry for entry in segment if entry[2] == "demotable"]
        output[start:stop] = promoted + demotable
        start = stop

    order = [index for index, _row, _kind in output]
    return PartitionResult(
        tuple(row for _index, row, _kind in output),
        tuple(decisions),
        order != list(range(len(original))),
    )


__all__ = [
    "DelayCertificate",
    "LotDecision",
    "PartitionResult",
    "PRODUCTS",
    "certified_pressure_partition",
    "certify_delay_invariance",
    "exact_sale_receipt",
    "exhaustive_delay_invariant",
]
