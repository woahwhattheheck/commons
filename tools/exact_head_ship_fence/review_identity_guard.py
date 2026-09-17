"""Reject replayed reviewer identities before evidence classification.

The core schema already validates review rows.  This guard wraps the validated
snapshot boundary so one reviewer cannot satisfy a multi-pass policy by
submitting multiple review IDs.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from . import fence as _fence

_ORIGINAL_SNAPSHOT = _fence._snapshot


def _snapshot_with_unique_reviewers(snapshot: Any, now: datetime):
    normalized = _ORIGINAL_SNAPSHOT(snapshot, now)
    reviewers = [row["reviewer"] for row in snapshot["reviews"]]
    if len(reviewers) != len(set(reviewers)):
        raise _fence.EvidenceError("reviews: duplicate reviewer identity")
    return normalized


_fence._snapshot = _snapshot_with_unique_reviewers
