"""Fail-closed current authority for outbound email deduplication."""

from .guard import GuardError
from .current import (
    CurrentGuardError,
    compile_current,
    compile_current_bytes,
    compile_historical_at,
    verify_current,
    verify_current_bytes,
)

# The package-level evaluation API is the process-clock current boundary.
evaluate = compile_current

__all__ = [
    "GuardError",
    "CurrentGuardError",
    "compile_current",
    "compile_current_bytes",
    "compile_historical_at",
    "evaluate",
    "verify_current",
    "verify_current_bytes",
]
