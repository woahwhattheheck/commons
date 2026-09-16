"""Fail-closed paid-proof compiler with descriptor-bound output custody."""
from __future__ import annotations

from . import _compiler_impl as _impl
from ._compiler_impl import (
    CANDIDATE_WARNING,
    PROVENANCE_BLOCKER,
    PUBLIC_RELEASE_STATE,
    SCHEMA_VERSION,
    compile_proof,
    compile_text,
    public_json,
    public_payload,
)
from .custody import write_outputs

__all__ = [
    "CANDIDATE_WARNING",
    "PROVENANCE_BLOCKER",
    "PUBLIC_RELEASE_STATE",
    "SCHEMA_VERSION",
    "compile_proof",
    "compile_text",
    "public_json",
    "public_payload",
    "write_outputs",
]


def __getattr__(name: str):
    """Preserve read compatibility for legacy implementation attributes."""

    return getattr(_impl, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_impl)))
