"""UNKNOWN as a first-class value that cannot be silently turned into a number.

Work order UIOWA-080. The rule from the engagement brief is that missing evidence
stays UNKNOWN -- it never becomes a zero, a pass, or a maturity score. The cheap way
to honor that is a convention ("remember not to add None"). Conventions decay.

So UNKNOWN here is an object that has no arithmetic at all. Any attempt to add,
multiply, compare or coerce it raises UnknownArithmeticError. Aggregation code is
therefore forced to call partition() and deal with the unknown bucket explicitly
before it can produce a total. A total that silently swallowed a missing input is
not possible to write by accident; it is only possible to write on purpose.
"""


class UnknownArithmeticError(TypeError):
    """Raised when code tries to do arithmetic on a missing input."""


class _Unknown:
    """Singleton sentinel for 'this input was not supplied / not yet evidenced'."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "UNKNOWN"

    def __str__(self):
        return "UNKNOWN"

    # Deliberately NOT falsy-by-accident: bool(UNKNOWN) raising would break dict
    # lookups and `x is UNKNOWN` checks, so truthiness is allowed and is True.
    # What is blocked is anything that could produce a NUMBER.
    def __bool__(self):
        return True

    def _blocked(self, *_args, **_kwargs):
        raise UnknownArithmeticError(
            "arithmetic attempted on UNKNOWN: a missing input must be partitioned "
            "out and reported, not folded into a total"
        )

    __add__ = __radd__ = _blocked
    __sub__ = __rsub__ = _blocked
    __mul__ = __rmul__ = _blocked
    __truediv__ = __rtruediv__ = _blocked
    __floordiv__ = __rfloordiv__ = _blocked
    __lt__ = __le__ = __gt__ = __ge__ = _blocked
    __int__ = __float__ = __index__ = _blocked


UNKNOWN = _Unknown()

# Any of these spellings in a fixture or an operator-filled worksheet means
# "not evidenced yet". They are normalized to the sentinel on load.
UNKNOWN_TOKENS = frozenset({"unknown", "UNKNOWN", "unk", "tbd", "TBD", "n/a", "N/A", "", None})


def coerce(value):
    """Normalize a raw fixture/worksheet value into UNKNOWN or the value itself."""
    if value is UNKNOWN:
        return UNKNOWN
    if isinstance(value, str):
        if value.strip().lower() in {"unknown", "unk", "tbd", "n/a", ""}:
            return UNKNOWN
        return value
    if value is None:
        return UNKNOWN
    return value


def is_unknown(value):
    return value is UNKNOWN


def partition(mapping):
    """Split {key: value} into (known, unknown_keys).

    Callers cannot get a total without seeing the unknown_keys list, because this
    is the only supported way to get the known values out.
    """
    known = {}
    unknown_keys = []
    for key, value in mapping.items():
        if is_unknown(coerce(value)):
            unknown_keys.append(key)
        else:
            known[key] = value
    return known, sorted(unknown_keys)


def render(value):
    """Display form for reports. UNKNOWN renders as the literal word, never '0'."""
    if is_unknown(coerce(value)):
        return "UNKNOWN"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)
