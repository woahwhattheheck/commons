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


def test_markdown_procurement_status_cell_is_not_an_admission_lock() -> None:
    row = (
        "| Submission by Oct 12 4:30 p.m. | "
        "Owner-controlled final send only after evidence/readiness review | "
        f"**{_denial()}** |"
    )
    assert "explicit-denial" not in _rules(
        "revenue/example-procurement/REQUIREMENTS.md", row
    )


def test_markdown_commons_denial_still_fails_closed() -> None:
    commons = "Com" + "mons"
    row = f"| {commons} posting action | **{_denial()}** |"
    assert "explicit-denial" in _rules("ground/new-policy.md", row)


def test_code_denial_still_fails_closed() -> None:
    source = f"raise RuntimeError({_denial()!r})"
    assert "explicit-denial" in _rules("host/new_gate.py", source)


def test_business_status_cell_cannot_mask_second_not_permitted_denial() -> None:
    row = (
        f"| Procurement readiness | **{_denial()}** | "
        f"Contributors are {_not_permitted()} to edit files |"
    )
    assert "explicit-denial" in _rules("revenue/example-procurement/STATUS.md", row)


def test_business_status_cell_cannot_mask_second_access_denied_phrase() -> None:
    row = (
        f"| Procurement readiness | **{_denial()}** | "
        f"{_access_denied().title()} to contributors |"
    )
    assert "explicit-denial" in _rules("revenue/example-procurement/STATUS.md", row)


def test_contributor_procurement_row_is_not_exempted() -> None:
    row = f"| Contributor procurement role | **{_denial()}** |"
    assert "explicit-denial" in _rules("revenue/example-procurement/STATUS.md", row)


def test_automated_agent_readiness_row_is_not_exempted() -> None:
    row = f"| Automated agents readiness | **{_not_permitted().upper()}** |"
    assert "explicit-denial" in _rules("revenue/example-procurement/STATUS.md", row)


def test_plural_permissions_row_is_not_exempted() -> None:
    row = f"| Procurement access permissions | **{_not_permitted().upper()}** |"
    assert "explicit-denial" in _rules("revenue/example-procurement/STATUS.md", row)


def test_generic_revenue_status_without_business_evidence_is_not_exempted() -> None:
    row = f"| Submission status | **{_denial()}** |"
    assert "explicit-denial" in _rules("revenue/example-procurement/STATUS.md", row)


def test_non_revenue_readiness_status_is_not_exempted() -> None:
    row = f"| Procurement readiness | **{_denial()}** |"
    assert "explicit-denial" in _rules("ground/procurement-status.md", row)
