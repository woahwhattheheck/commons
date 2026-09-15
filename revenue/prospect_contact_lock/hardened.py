"""Compatibility import surface for the canonical prospect contact lock.

Hardening now lives in :mod:`revenue.prospect_contact_lock.lock` so direct
submodule imports and package/CLI imports share one production implementation.
This module remains only to preserve existing ``hardened`` import paths.
"""
from .lock import (
    AUTHORITY_MARKER_PATH,
    AUTHORITY_MARKER_SCHEMA,
    EXPECTED_AUTHORITY_MARKER,
    ProspectContactLock,
    _strict_compensation_category,
)

__all__ = [
    "AUTHORITY_MARKER_PATH",
    "AUTHORITY_MARKER_SCHEMA",
    "EXPECTED_AUTHORITY_MARKER",
    "ProspectContactLock",
]
