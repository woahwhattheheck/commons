"""Connector capability preflight compiler."""

from .latest import (
    PreflightError,
    compile_at,
    compile_current,
    strict_loads,
    verify_current,
    verify_integrity,
)
from . import core as _core
from .publication import write_json_exclusive as _secure_write_json_exclusive

# Keep the legacy internal name safe for normal package and direct-submodule imports.
_core.write_json_exclusive = _secure_write_json_exclusive

__all__ = [
    "PreflightError",
    "compile_at",
    "compile_current",
    "strict_loads",
    "verify_current",
    "verify_integrity",
]
