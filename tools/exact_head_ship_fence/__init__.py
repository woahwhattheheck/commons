"""Exact-head ship fence public API."""
# Install validated reviewer-identity replay protection before exporting API.
from . import review_identity_guard as _review_identity_guard  # noqa: F401
from .fence import (
    AUTHORITY,
    EvidenceError,
    SCHEMA_VERSION,
    TOOL_ID,
    canonical_json_bytes,
    compile_current,
    parse_json_bytes,
    render_markdown,
    verify_current,
)

__all__ = [
    "AUTHORITY",
    "EvidenceError",
    "SCHEMA_VERSION",
    "TOOL_ID",
    "canonical_json_bytes",
    "compile_current",
    "parse_json_bytes",
    "render_markdown",
    "verify_current",
]
