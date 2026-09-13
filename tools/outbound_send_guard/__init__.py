"""Fail-closed offline authority for outbound email deduplication."""

from .guard import GuardError, evaluate

__all__ = ["GuardError", "evaluate"]
