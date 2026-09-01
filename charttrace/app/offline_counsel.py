"""Offline counsel review import.

Unsigned JSON is a non-authoritative review record only. It never approves
release, never clears a legal or authority hold, and never self-attests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .paths import PathEgressError, assert_local_filesystem_path


class CounselImportError(ValueError):
    pass


REQUIRED_KEYS = {"mode", "case_id", "reviewed_by", "decision"}
FORBIDDEN_AUTHORITY_KEYS = {
    "approval_authoritative",
    "authoritative",
    "clears_legal_hold",
    "legal_hold_cleared",
    "clears_authority_hold",
    "approved",
    "signature",
    "signed",
    "certificate",
}
ALLOWED_DECISIONS = {"approve", "return_for_qa", "hold"}
RECORD_KIND = "NON_AUTHORITATIVE_REVIEW_RECORD"


def import_counsel_review(path: Path, expected_case_id: str) -> Dict[str, Any]:
    """Read a local review claim. Never treat it as approval or hold-clear."""
    try:
        path = assert_local_filesystem_path(path)
    except PathEgressError as error:
        raise CounselImportError(str(error)) from error
    if not path.is_file() or path.is_symlink():
        raise CounselImportError("Counsel review bundle must be a local regular file.")
    with path.open("r", encoding="utf-8") as handle:
        try:
            value = json.load(handle)
        except json.JSONDecodeError as error:
            raise CounselImportError("Counsel review bundle must be JSON.") from error
    if not isinstance(value, dict):
        raise CounselImportError("Counsel review bundle must be a JSON object.")
    for key in value:
        lowered = str(key).lower()
        if lowered in FORBIDDEN_AUTHORITY_KEYS or value.get(key) is True and lowered in {
            "approval_authoritative",
            "authoritative",
            "clears_legal_hold",
            "legal_hold_cleared",
        }:
            raise CounselImportError(
                "Forged or self-attested approval fields are rejected."
            )
        if lowered in FORBIDDEN_AUTHORITY_KEYS:
            raise CounselImportError(
                "Forged or self-attested approval fields are rejected."
            )
    if value.get("approval_authoritative") or value.get("clears_legal_hold"):
        raise CounselImportError(
            "Forged or self-attested approval fields are rejected."
        )
    missing = REQUIRED_KEYS - set(value)
    if missing:
        raise CounselImportError(
            f"Counsel review bundle is missing: {', '.join(sorted(missing))}."
        )
    if value["mode"] != "offline_counsel_review":
        raise CounselImportError("Bundle mode must be offline_counsel_review.")
    if value["case_id"] != expected_case_id:
        raise CounselImportError("Counsel review bundle case does not match.")
    if value["decision"] not in ALLOWED_DECISIONS:
        raise CounselImportError("Unknown counsel review decision.")
    reviewed_by = str(value["reviewed_by"]).strip()
    if not reviewed_by:
        raise CounselImportError("reviewed_by is required.")
    return {
        "kind": RECORD_KIND,
        "mode": "offline_counsel_review",
        "case_id": expected_case_id,
        "reviewed_by": reviewed_by,
        "claimed_decision": value["decision"],
        "notes": str(value.get("notes", "")).strip(),
        "authoritative": False,
        "clears_legal_hold": False,
        "applies_human_approval": False,
    }
