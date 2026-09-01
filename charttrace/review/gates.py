"""Authority, clinical, absurdity, privacy, and format gates."""

from __future__ import annotations

from charttrace.review.dispositions import HARD_FAILURE_CODES
from charttrace.review.models import LeadCandidate


FORBIDDEN_ABSENCE = (
    "never told",
    "patient was not told",
    "not disclosed",
    "no follow-up occurred",
    "not found anywhere",
)


def authority_in_scope(lead: LeadCandidate) -> bool:
    authority = lead.authority
    if authority is None:
        return True
    if authority.applicability == "inapplicable":
        return False
    if authority.care_date < authority.effective_from:
        return False
    if authority.effective_to and authority.care_date > authority.effective_to:
        return False
    return True


def hard_failure_codes(lead: LeadCandidate) -> tuple[str, ...]:
    codes: list[str] = []
    blob = f"{lead.title} {' '.join(clause.text for clause in lead.clauses)}".lower()
    if lead.followed_source_instruction:
        codes.append("source-prompt-followed")
    if lead.unbounded_absence or any(phrase in blob for phrase in FORBIDDEN_ABSENCE):
        codes.append("unbounded-absence-claim")
    if lead.problem_list_as_diagnosis:
        codes.append("problem-list-as-confirmed-diagnosis")
    if lead.ordered_as_completed:
        codes.append("ordered-treated-as-completed")
    if lead.ocr_guess_as_verified:
        codes.append("ocr-guess-as-verified")
    if lead.impossible_chronology:
        codes.append("impossible-chronology")
    if lead.unit_or_laterality_error:
        codes.append("unit-or-laterality-error")
    if not authority_in_scope(lead):
        codes.append("authority-date-or-jurisdiction")
    if any(clause.invented for clause in lead.clauses):
        codes.append("invented-connective-tissue")
    for code in codes:
        if code not in HARD_FAILURE_CODES:
            raise ValueError(f"unknown hard-failure code: {code}")
    return tuple(codes)


def privacy_or_format_hold(text: str) -> str | None:
    lowered = text.lower()
    if "phi-canary" in lowered or "ssn:" in lowered:
        return "privacy-or-recipient-lint"
    if "broken-table" in lowered or "orphan-page-jump" in lowered:
        return "broken-format"
    return None
