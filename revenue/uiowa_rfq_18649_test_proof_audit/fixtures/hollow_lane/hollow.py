"""Ground-truth fixture: a deliberately hollow lane. NOT a real component.

This file exists so the auditor can be shown to detect what it claims to
detect. Nothing here is part of the engagement.
"""


class RuleError(ValueError):
    pass


def validate_rate(value):
    if value < 0:
        raise RuleError("rate must not be negative")
    return value


def double(value):
    return value * 2
