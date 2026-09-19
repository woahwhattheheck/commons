"""Exact money and hours arithmetic, plus the UNKNOWN that refuses to be zero.

Why this module exists at all: a pricing model built on floats and on silent
defaults produces a confident margin, and a confident margin is what gets a
fixed-price bid signed at a loss. Two decisions follow from that:

  * Money is `Decimal` in whole cents. Binary floats cannot represent 0.1, so a
    model that adds enough of them drifts, and a total that fails to reconcile
    to the quoted fee by a cent is indistinguishable from a real error.

  * A missing estimate is `UNKNOWN`, and UNKNOWN propagates. It is never 0.
    This is not pedantry: a zero COST inflates margin, so the direction of the
    error is always toward "this bid looks profitable". Anything derived from
    an UNKNOWN is itself UNKNOWN, and the model reports what it cannot compute
    instead of printing a number that looks like an answer.

Python 3 standard library only.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


class _Unknown:
    """A value we do not have. Deliberately NOT zero, and deliberately loud.

    Arithmetic with UNKNOWN yields UNKNOWN rather than raising, so a total can
    be computed and honestly reported as incomputable. Comparisons raise,
    because "is this under budget?" has no truthy answer when the input is
    missing, and returning False there would quietly mean "yes, fine".
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "UNKNOWN"

    def __str__(self):
        return "UNKNOWN"

    def __bool__(self):
        raise TypeError(
            "UNKNOWN has no truth value. An absent estimate must be handled "
            "explicitly, not treated as absent-therefore-false."
        )

    def __add__(self, other):
        return self

    __radd__ = __sub__ = __rsub__ = __mul__ = __rmul__ = __add__

    def __truediv__(self, other):
        return self

    __rtruediv__ = __truediv__

    def __neg__(self):
        return self

    def __lt__(self, other):
        raise TypeError("cannot compare UNKNOWN; resolve the estimate first")

    __le__ = __gt__ = __ge__ = __lt__


UNKNOWN = _Unknown()

CENT = Decimal("0.01")
HOUR = Decimal("0.01")


def is_unknown(value) -> bool:
    return value is UNKNOWN


def money(value) -> Decimal:
    """Parse an amount to exact cents. Strings are preferred at the boundary."""
    if is_unknown(value):
        return UNKNOWN
    if isinstance(value, Decimal):
        d = value
    elif isinstance(value, int):
        d = Decimal(value)
    elif isinstance(value, float):
        # Route through repr so 1234.56 does not arrive as 1234.5599999999.
        d = Decimal(repr(value))
    elif isinstance(value, str):
        d = Decimal(value.replace(",", "").replace("$", "").strip())
    else:
        raise TypeError(f"cannot read {value!r} as money")
    return d.quantize(CENT, rounding=ROUND_HALF_UP)


def hours(value) -> Decimal:
    if is_unknown(value):
        return UNKNOWN
    if isinstance(value, str):
        value = value.strip()
        if not value:
            raise ValueError("blank is not an hours figure; use null for UNKNOWN")
    d = value if isinstance(value, Decimal) else Decimal(repr(value) if isinstance(value, float) else str(value))
    if d < 0:
        raise ValueError(f"hours cannot be negative: {d}")
    return d.quantize(HOUR, rounding=ROUND_HALF_UP)


def add(*values):
    """Sum, where one UNKNOWN makes the whole sum UNKNOWN."""
    total = Decimal("0")
    for v in values:
        if is_unknown(v):
            return UNKNOWN
        total += v
    return total


def mul(a, b):
    if is_unknown(a) or is_unknown(b):
        return UNKNOWN
    return a * b


def fmt_money(value) -> str:
    if is_unknown(value):
        return "UNKNOWN"
    q = value.quantize(CENT, rounding=ROUND_HALF_UP)
    sign = "-" if q < 0 else ""
    return f"{sign}${abs(q):,.2f}"


def fmt_hours(value) -> str:
    if is_unknown(value):
        return "UNKNOWN"
    q = value.normalize()
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{text} h" if text else "0 h"


def fmt_pct(value) -> str:
    if is_unknown(value):
        return "UNKNOWN"
    return f"{value.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}%"
