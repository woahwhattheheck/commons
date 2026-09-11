"""Conservative hygiene checks for labels intended to name a human actor.

This module does *not* authenticate a person and does not grant authorization. A
passing label is only syntactically free of obvious automation/service markers;
callers must enforce identity, role, approval, and permission separately.
"""
from __future__ import annotations

from typing import Any


RESERVED_IDENTITY_TOKENS = frozenset(
    {
        "ai",
        "agent",
        "auto",
        "automated",
        "automation",
        "bot",
        "robot",
        "service",
        "system",
    }
)


def _alphabetic_runs(label: str) -> tuple[str, ...]:
    """Split a label into case-folded Unicode alphabetic runs."""

    runs: list[str] = []
    current: list[str] = []
    for char in label.casefold():
        if char.isalpha():
            current.append(char)
            continue
        if current:
            runs.append("".join(current))
            current.clear()
    if current:
        runs.append("".join(current))
    return tuple(runs)


def _has_segmented_reserved_token(runs: tuple[str, ...]) -> bool:
    """Catch reserved words split into consecutive one-letter runs."""

    for start, token in enumerate(runs):
        if len(token) != 1:
            continue
        joined = ""
        for candidate in runs[start:]:
            if len(candidate) != 1:
                break
            joined += candidate
            if joined in RESERVED_IDENTITY_TOKENS:
                return True
            if len(joined) > max(map(len, RESERVED_IDENTITY_TOKENS)):
                break
    return False


def is_named_human_label(label: Any, *, min_parts: int = 1) -> bool:
    """Return whether ``label`` is a plausible human-name *label*.

    The result is a presentation-layer hygiene signal only. It is not evidence that
    a real person supplied the label and must never substitute for authentication or
    an authorization/approval check.
    """

    if isinstance(min_parts, bool) or not isinstance(min_parts, int) or min_parts < 1:
        raise ValueError("min_parts must be a positive integer")
    if not isinstance(label, str):
        return False

    runs = _alphabetic_runs(label)
    if len(runs) < min_parts:
        return False
    if any(token in RESERVED_IDENTITY_TOKENS for token in runs):
        return False
    if _has_segmented_reserved_token(runs):
        return False
    return True
