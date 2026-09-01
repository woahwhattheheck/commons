"""Auditable review dispositions and fail-closed rejection reasons."""

from __future__ import annotations

from enum import Enum


class Disposition(str, Enum):
    PASS = "PASS"
    REPAIR = "REPAIR"
    DOWNGRADE = "DOWNGRADE"
    WEAK_APPENDIX = "WEAK_APPENDIX"
    MERGE_DUPLICATE = "MERGE_DUPLICATE"
    REJECT_UNSUPPORTED = "REJECT_UNSUPPORTED"
    HOLD = "HOLD"


DISPOSITIONS = tuple(item.value for item in Disposition)

VAGUE_REJECTION_REASONS = (
    "not actionable",
    "unlikely",
    "too aggressive",
    "a lawyer might dislike it",
)

HARD_FAILURE_CODES = (
    "citation-does-not-entail",
    "invented-connective-tissue",
    "wrong-patient-or-page",
    "hash-mismatch",
    "authority-date-or-jurisdiction",
    "problem-list-as-confirmed-diagnosis",
    "ordered-treated-as-completed",
    "unbounded-absence-claim",
    "source-prompt-followed",
    "impossible-chronology",
    "unit-or-laterality-error",
    "ocr-guess-as-verified",
    "missing-counterevidence",
    "broken-format",
    "privacy-or-recipient-lint",
)


def require_concrete_reason(reason: str) -> str:
    text = reason.strip()
    if not text:
        raise ValueError("rejection requires a concrete audit reason")
    lowered = text.lower()
    if lowered in VAGUE_REJECTION_REASONS:
        raise ValueError(f"vague rejection is not auditable: {text}")
    return text
