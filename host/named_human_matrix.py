#!/usr/bin/env python3
"""Reusable adversarial case matrix for named-human boolean validators."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


class NamedHumanMatrixFailure(AssertionError):
    """Raised when a validator disagrees with one or more frozen matrix cases."""


@dataclass(frozen=True)
class NamedHumanCase:
    case_id: str
    value: Any
    expected: bool
    family: str


NAMED_HUMAN_CASES: tuple[NamedHumanCase, ...] = (
    # Shape / blank / one-token denials.
    NamedHumanCase("deny-none", None, False, "non_string"),
    NamedHumanCase("deny-number", 17, False, "non_string"),
    NamedHumanCase("deny-bool", True, False, "non_string"),
    NamedHumanCase("deny-empty", "", False, "blank"),
    NamedHumanCase("deny-whitespace", "  \t\n ", False, "blank"),
    NamedHumanCase("deny-one-token", "Alice", False, "one_token"),
    # Exact reserved automation/service tokens.
    NamedHumanCase("deny-exact-ai", "AI Reviewer", False, "reserved_token"),
    NamedHumanCase("deny-exact-agent", "Agent Reviewer", False, "reserved_token"),
    NamedHumanCase("deny-exact-auto", "Auto Reviewer", False, "reserved_token"),
    NamedHumanCase("deny-exact-automation", "Automation Reviewer", False, "reserved_token"),
    NamedHumanCase("deny-exact-bot", "Bot Operator", False, "reserved_token"),
    NamedHumanCase("deny-exact-robot", "Robot Reviewer", False, "reserved_token"),
    NamedHumanCase("deny-exact-service", "Service Account", False, "reserved_token"),
    NamedHumanCase("deny-exact-system", "System Reviewer", False, "reserved_token"),
    # Reserved terms after ordinary human-looking prefixes/suffixes.
    NamedHumanCase("deny-embedded-system", "Jordan System", False, "reserved_token"),
    NamedHumanCase("deny-embedded-bot", "Taylor Bot", False, "reserved_token"),
    NamedHumanCase("deny-embedded-service", "Morgan Service", False, "reserved_token"),
    # Punctuation/whitespace segmented reserved terms.
    NamedHumanCase("deny-punct-system", "S.Y.S.T.E.M Reviewer", False, "segmented_reserved"),
    NamedHumanCase("deny-punct-auto", "A-U-T-O Reviewer", False, "segmented_reserved"),
    NamedHumanCase("deny-punct-bot", "b.o.t operator", False, "segmented_reserved"),
    NamedHumanCase("deny-space-system", "S Y S T E M Reviewer", False, "segmented_reserved"),
    NamedHumanCase("deny-space-ai", "A I Reviewer", False, "segmented_reserved"),
    # Digits must behave as separators, not a bypass suffix.
    NamedHumanCase("deny-digit-system", "System2 Operator", False, "digit_reserved"),
    NamedHumanCase("deny-digit-ai", "AI2 Reviewer", False, "digit_reserved"),
    NamedHumanCase("deny-digit-bot", "bot123 user", False, "digit_reserved"),
    NamedHumanCase("deny-digit-agent", "agent007 reviewer", False, "digit_reserved"),
    NamedHumanCase("deny-digit-service", "service2 account", False, "digit_reserved"),
    # Case folding must not weaken reserved-token checks.
    NamedHumanCase("deny-mixed-case-system", "SyStEm Reviewer", False, "mixed_case_reserved"),
    NamedHumanCase("deny-mixed-case-robot", "rObOt Operator", False, "mixed_case_reserved"),
    # Legitimate controls. Reserved *substrings* are intentionally allowed.
    NamedHumanCase("allow-basic", "Aisha Rahman", True, "legitimate"),
    NamedHumanCase("allow-hyphen-apostrophe", "Mary-Jane O'Neil", True, "legitimate"),
    NamedHumanCase("allow-unicode", "José Álvarez", True, "legitimate"),
    NamedHumanCase("allow-hyphen", "Jean-Luc Picard", True, "legitimate"),
    NamedHumanCase("allow-agent-substring", "Agentson Rivera", True, "substring_control"),
    NamedHumanCase("allow-service-substring", "Serviceman Ortiz", True, "substring_control"),
    NamedHumanCase("allow-system-substring", "Systemson Lee", True, "substring_control"),
    NamedHumanCase("allow-bot-substring", "Botter James", True, "substring_control"),
)


def assert_named_human_matrix(validator: Callable[[Any], bool]) -> None:
    """Assert exact boolean results for every frozen named-human matrix case."""
    if not callable(validator):
        raise TypeError("validator must be callable")

    failures: list[str] = []
    for case in NAMED_HUMAN_CASES:
        try:
            result = validator(case.value)
        except Exception as exc:
            failures.append(f"{case.case_id}: raised {type(exc).__name__}: {exc}")
            continue
        if type(result) is not bool:
            failures.append(
                f"{case.case_id}: returned non-bool {type(result).__name__} {result!r}"
            )
            continue
        if result is not case.expected:
            failures.append(
                f"{case.case_id}: expected {case.expected}, got {result} (value={case.value!r})"
            )

    if failures:
        raise NamedHumanMatrixFailure("named-human matrix failed: " + "; ".join(failures))
