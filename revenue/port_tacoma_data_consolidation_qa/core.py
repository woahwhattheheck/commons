"""Public facade for the Port Tacoma / NWSA synthetic consolidation QA core."""
from __future__ import annotations

from .evaluator import evaluate, verify_receipt
from .schema import (
    ASSESSMENT_SCHEMA,
    AssessmentResult,
    ConsolidationEvidenceError,
    RECEIPT_SCHEMA,
    batch_content_sha256,
    canonical_json,
    load_strict_json,
)

__all__ = [
    "ASSESSMENT_SCHEMA",
    "AssessmentResult",
    "ConsolidationEvidenceError",
    "RECEIPT_SCHEMA",
    "batch_content_sha256",
    "canonical_json",
    "evaluate",
    "load_strict_json",
    "verify_receipt",
]
