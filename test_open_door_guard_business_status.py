#!/usr/bin/env python3
"""Regression coverage for business-status denial text in the open-door guard."""

from open_door_guard import AddedLine, scan_added


def _rules(path: str, text: str) -> set[str]:
    return {item.rule for item in scan_added([AddedLine(path, 29, text)])}


def _denial() -> str:
    # Assemble the phrase at runtime so this regression source does not become
    # scanner input containing the exact phrase it is intended to exercise.
    return "NOT " + "AUTHORIZED"


def _not_permitted() -> str:
    return "not " + "permitted"


def _access_denied() -> str:
    return "access " + "denied"


def test_markdown_owner_controlled_procurement_status_is_exempt() -> None:
    row = (
        "| Submission by Oct 12 4:30 p.m. | "
        "Owner-controlled final send only after evidence/readiness review | "
        f"**{_denial()}** |"
    )
    assert "explicit-denial" not in _rules(
        "revenue/example-procurement/REQUIREMENTS.md", row
    )


def test_generic_submission_status_fails_closed_without_owner_control() -> None:
    row = f"| Submission | **{_denial()}** |"
    assert "explicit-denial" in _rules(
        "revenue/example-procurement/STATUS.md", row
    )


def test_owner_controlled_business_status_outside_revenue_fails_closed() -> None:
    row = f"| Submission | Owner-controlled final send | **{_denial()}** |"
    assert "explicit-denial" in _rules("ground/new-policy.md", row)


def test_markdown_commons_denial_still_fails_closed() -> None:
    commons = "Com" + "mons"
    row = f"| {commons} posting action | **{_denial()}** |"
    assert "explicit-denial" in _rules("ground/new-policy.md", row)


def test_code_denial_still_fails_closed() -> None:
    source = f"raise RuntimeError({_denial()!r})"
    assert "explicit-denial" in _rules("host/new_gate.py", source)


def test_single_cell_admission_subjects_fail_closed() -> None:
    cases = (
        ("External contributors", _not_permitted()),
        ("Anonymous users", _denial()),
        ("automated agents", _not_permitted()),
        ("service bots", _denial()),
        ("remote models", _not_permitted()),
        ("Access permissions", _not_permitted()),
    )
    for subject, denial in cases:
        row = f"| {subject} | **{denial}** |"
        assert "explicit-denial" in _rules(
            "revenue/example-procurement/STATUS.md", row
        ), subject


def test_business_words_do_not_override_admission_subject() -> None:
    row = (
        "| Proposal contributors | Owner-controlled submission | "
        f"**{_not_permitted()}** |"
    )
    assert "explicit-denial" in _rules(
        "revenue/example-procurement/STATUS.md", row
    )


def test_business_status_cell_cannot_mask_second_not_permitted_denial() -> None:
    row = (
        "| Submission | Owner-controlled final send | "
        f"**{_denial()}** | Contributors are {_not_permitted()} to edit files |"
    )
    assert "explicit-denial" in _rules(
        "revenue/example-procurement/STATUS.md", row
    )


def test_business_status_cell_cannot_mask_second_access_denied_phrase() -> None:
    row = (
        "| Submission | Owner-controlled final send | "
        f"**{_denial()}** | {_access_denied().title()} to contributors |"
    )
    assert "explicit-denial" in _rules(
        "revenue/example-procurement/STATUS.md", row
    )
