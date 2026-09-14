"""Supported receipt compilation and verification surface.

Caller-selected roots and clocks are deliberately absent.  Deterministic injected
variants live only in the package's explicit ``_test_api`` module.
"""

from .compiler import compile_current
from .verifier import verify_receipt_current, verify_receipt_integrity

__all__ = [
    "compile_current",
    "verify_receipt_current",
    "verify_receipt_integrity",
]
