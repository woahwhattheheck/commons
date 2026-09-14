"""Test-only deterministic root/time injection.

This module is not imported or re-exported by supported production APIs.
"""

from .compiler import _compile_at as compile_at
from .verifier import (
    _verify_receipt_current_at as verify_receipt_current_at,
    _verify_receipt_integrity_at as verify_receipt_integrity_at,
)

__all__: list[str] = []
