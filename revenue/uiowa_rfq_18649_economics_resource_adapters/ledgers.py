#!/usr/bin/env python3
"""Typed ledgers for UIOWA-105.

The work order asks for "effort, recurring cost, cash cost, and released staff
capacity" to be kept separate. That is four names for five quantities:
"recurring cost" is BOTH a recurring staff load and a recurring cash amount,
and merging those two is precisely how a resourcing table misleads a reader --
one is capacity drawn from named roles, the other is money.

So there are five ledgers, each carrying its unit as a string. The unit string
is what arithmetic is checked against, NOT the underlying dimension: one-time
effort hours and released-capacity hours are both hours and would otherwise add
cleanly and silently into a number that means nothing.
"""

ONE_TIME_EFFORT = "hours (one-time implementation)"
RECURRING_EFFORT = "FTE-fraction per year (recurring staff load)"
ONE_TIME_CASH = "currency (one-time)"
RECURRING_CASH = "currency per year (recurring)"
RELEASED_CAPACITY = "staff-hours released per year (recurring)"

ALL_LEDGERS = (ONE_TIME_EFFORT, RECURRING_EFFORT, ONE_TIME_CASH,
               RECURRING_CASH, RELEASED_CAPACITY)

UNKNOWN = "UNKNOWN"

# Strings an upstream component may use to say "not assessed". Anything here
# stays UNKNOWN. Nothing here becomes zero.
UNKNOWN_TOKENS = frozenset(
    ["", "unknown", "n/a", "na", "tbd", "none", "null", "?", "-"]
)


class LedgerUnitError(TypeError):
    """Raised when code tries to combine amounts from different ledgers."""


class AdapterError(ValueError):
    """Raised for malformed upstream records. Names the record it came from."""


class Amount(object):
    """A low/likely/high range in one ledger, with its provenance attached.

    Provenance travels with the number because the work order requires that
    "original assumptions and ranges remain visible". An adapter that returned
    a bare float would have destroyed exactly what it was asked to transport.
    """

    __slots__ = ("low", "likely", "high", "ledger", "basis", "source_component",
                 "source_record_id")

    def __init__(self, low, likely, high, ledger, basis="",
                 source_component="", source_record_id=""):
        if ledger not in ALL_LEDGERS:
            raise AdapterError("unknown ledger %r" % (ledger,))
        self.low, self.likely, self.high = float(low), float(likely), float(high)
        self.ledger = ledger
        self.basis = basis
        self.source_component = source_component
        self.source_record_id = source_record_id
        if not (self.low <= self.likely <= self.high):
            raise AdapterError(
                "range must satisfy low <= likely <= high; got %r/%r/%r in %s "
                "from %s" % (low, likely, high, ledger, source_record_id or "?")
            )

    def __add__(self, other):
        if not isinstance(other, Amount):
            raise LedgerUnitError("cannot add Amount to %r" % type(other).__name__)
        if other.ledger != self.ledger:
            raise LedgerUnitError(
                "refusing to add across ledgers: %r + %r. A combined number "
                "would not mean anything." % (self.ledger, other.ledger)
            )
        return Amount(self.low + other.low, self.likely + other.likely,
                      self.high + other.high, self.ledger,
                      basis="sum", source_component="rollup",
                      source_record_id="+".join(sorted(
                          {self.source_record_id, other.source_record_id})))

    __radd__ = __add__

    def as_dict(self):
        return {
            "low": round(self.low, 4),
            "likely": round(self.likely, 4),
            "high": round(self.high, 4),
            "ledger": self.ledger,
            "basis": self.basis,
            "source_component": self.source_component,
            "source_record_id": self.source_record_id,
        }

    def __repr__(self):
        return "Amount(%g/%g/%g %s)" % (self.low, self.likely, self.high, self.ledger)


def read_amount(raw, ledger, source_component, source_record_id, field):
    """Normalise an upstream value into an Amount, or UNKNOWN.

    Accepts the range forms upstream components actually emit:
      {"low":..,"likely":..,"high":..}   the canonical shape
      {"low":..,"mid":..,"high":..}      'mid' is the same slot under another name
      {"value": n}                       a point estimate, widened to n/n/n and
                                         marked as such in the basis
      a bare number                      likewise

    Returns UNKNOWN for an absent, null, or explicitly-unknown value. It never
    returns a zero Amount: "nobody estimated this" and "this costs nothing" are
    different claims and the roll-up treats them differently.
    """
    if raw is None:
        return UNKNOWN
    if isinstance(raw, str):
        if raw.strip().lower() in UNKNOWN_TOKENS:
            return UNKNOWN
        raise AdapterError(
            "%s.%s is the text %r. An estimate written in words is not an "
            "absence, and guessing the number is not this adapter's job."
            % (source_record_id, field, raw)
        )
    if isinstance(raw, bool):
        raise AdapterError("%s.%s is a boolean; refusing to read it as 1/0"
                           % (source_record_id, field))
    if isinstance(raw, (int, float)):
        return Amount(raw, raw, raw, ledger,
                      basis="point estimate from upstream, widened to a "
                            "zero-width range; upstream stated no bounds",
                      source_component=source_component,
                      source_record_id=source_record_id)
    if not isinstance(raw, dict):
        raise AdapterError("%s.%s has unsupported type %s"
                           % (source_record_id, field, type(raw).__name__))

    basis = raw.get("basis") or raw.get("assumption") or ""
    if "value" in raw and "low" not in raw:
        v = raw["value"]
        if v is None or (isinstance(v, str) and v.strip().lower() in UNKNOWN_TOKENS):
            # The useful UNKNOWN form: a basis recorded with no number.
            return UNKNOWN
        return Amount(v, v, v, ledger,
                      basis=basis or "point estimate from upstream",
                      source_component=source_component,
                      source_record_id=source_record_id)

    mid_key = "likely" if "likely" in raw else ("mid" if "mid" in raw else None)
    if "low" not in raw or "high" not in raw or mid_key is None:
        present = ", ".join(sorted(raw))
        raise AdapterError(
            "%s.%s is a partial range (has: %s). A missing bound is not filled "
            "in with a default." % (source_record_id, field, present or "nothing")
        )
    for key in ("low", mid_key, "high"):
        if not isinstance(raw[key], (int, float)) or isinstance(raw[key], bool):
            raise AdapterError("%s.%s.%s is not a number" % (source_record_id, field, key))
    return Amount(raw["low"], raw[mid_key], raw["high"], ledger, basis=basis,
                  source_component=source_component,
                  source_record_id=source_record_id)
