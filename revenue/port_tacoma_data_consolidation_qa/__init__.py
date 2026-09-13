"""Port Tacoma / NWSA synthetic data-consolidation QA core."""
from .core import (
    ConsolidationEvidenceError,
    batch_content_sha256,
    evaluate,
    load_strict_json,
    verify_receipt,
)

__all__ = [
    "ConsolidationEvidenceError",
    "batch_content_sha256",
    "evaluate",
    "load_strict_json",
    "verify_receipt",
]
