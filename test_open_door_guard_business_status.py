#!/usr/bin/env python3
"""Regression coverage for structurally proven business-status denial text."""

from open_door_guard import AddedLine, scan_added


def _rules(path: str, text: str) -> set[str]:
    return {item.rule for item in scan_added([AddedLine(path, 29, text)])}


def _denial() -> str:
    return "NOT " + "AUTHORIZED"


def _not_permitted() -> str:
    return "not " + "permitted"


def _access_denied() -> str:
    return "access " + "denied"


def _known_business_row(denial: str | None = None) -> str:
    return (
        "| Submission by Oct 12 4:30 p.m. | "
        "Owner-controlled final send only after evidence/readiness review | "
        f"**{denial or _denial()}** |"
    )


def test_known_dated_owner_controlled_submission_status_is_exempt() -> None:
    assert "explicit-denial" not in _rules(
        "revenue/example-procurement/REQUIREMENTS.md", _known_business_row()
    )


def test_iso_and_numeric_deadline_shapes_remain_supported() -> None:
    for label in ("Submission by 2026-10-12 16:30", "Submission by 10/12/2026"):
        row = (
            f"| {label} | "
            "Owner-controlled final send only after evidence/readiness review | "
            f"**{_denial()}** |"
        )
        assert "explicit-denial" not in _rules(
            "revenue/example-procurement/REQUIREMENTS.md", row
        )


def test_generic_business_words_do_not_create_exception() -> None:
    rows = (
        f"| Everyone | Procurement readiness | **{_denial()}** |",
        f"| Visitors | Procurement checkout | **{_denial()}** |",
        f"| Submission | Owner-controlled final send | **{_denial()}** |",
        f"| Procurement | Owner-controlled final send only after evidence/readiness review | **{_denial()}** |",
    )
    for row in rows:
        assert "explicit-denial" in _rules(
            "revenue/example-procurement/STATUS.md", row
        ), row


def test_unbounded_subject_vocabulary_cannot_launder_denial() -> None:
    rows = (
        f"| Submission by Everyone | Owner-controlled final send only after evidence/readiness review | **{_denial()}** |",
        f"| Submission by Visitors | Owner-controlled final send only after evidence/readiness review | **{_denial()}** |",
        f"| Admin submission by Oct 12 | Owner-controlled final send only after evidence/readiness review | **{_denial()}** |",
    )
    for row in rows:
        assert "explicit-denial" in _rules(
            "revenue/example-procurement/STATUS.md", row
        ), row


def test_extra_subject_or_policy_cell_invalidates_structural_exception() -> None:
    rows = (
        _known_business_row().rstrip("|") + "| Admins only |",
        _known_business_row().rstrip("|") + "| Everyone |",
        (
            "| Submission by Oct 12 4:30 p.m. | "
            "Owner-controlled final send only after evidence/readiness review | "
            f"**{_denial()}** | Contributors only |"
        ),
    )
    for row in rows:
        assert "explicit-denial" in _rules(
            "revenue/example-procurement/STATUS.md", row
        ), row


def test_admission_vocabulary_still_vetoes_exact_shape() -> None:
    row = (
        "| Submission by Oct 12 4:30 p.m. | "
        "Owner-controlled final send only after evidence/readiness review for admins | "
        f"**{_denial()}** |"
    )
    assert "explicit-denial" in _rules(
        "revenue/example-procurement/STATUS.md", row
    )


def test_non_revenue_copy_of_exact_business_shape_fails_closed() -> None:
    assert "explicit-denial" in _rules("ground/new-policy.md", _known_business_row())


def test_code_denial_still_fails_closed() -> None:
    source = f"raise RuntimeError({_denial()!r})"
    assert "explicit-denial" in _rules("host/new_gate.py", source)


def test_known_business_status_cannot_mask_second_not_permitted_denial() -> None:
    row = _known_business_row().rstrip("|") + f"| Contributors are {_not_permitted()} to edit files |"
    assert "explicit-denial" in _rules(
        "revenue/example-procurement/STATUS.md", row
    )


def test_known_business_status_cannot_mask_second_access_denied_phrase() -> None:
    row = _known_business_row().rstrip("|") + f"| {_access_denied().title()} to contributors |"
    assert "explicit-denial" in _rules(
        "revenue/example-procurement/STATUS.md", row
    )
