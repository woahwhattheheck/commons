"""Ground-truth fixture: a lane whose suite does prove something."""


class RuleError(ValueError):
    pass


def validate_rate(value):
    if value < 0:
        raise RuleError("rate must not be negative")
    return value


def double(value):
    return value * 2
