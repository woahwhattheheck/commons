"""Offline counsel review import.

Unsigned JSON is a non-authoritative review record only. It never approves
release, never clears a legal or authority hold, and never self-attests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

from .paths import PathEgressError, assert_local_filesystem_path


class CounselImportError(ValueError):
    pass


ALLOWED_KEYS = frozenset({"mode", "case_id", "reviewed_by", "decision", "notes"})
FORBIDDEN_AUTHORITY_KEYS = frozenset(
    {
        "approval_authoritative",
        "authoritative",
        "clears_legal_hold",
        "legal_hold_cleared",
        "clears_authority_hold",
        "approved",
        "approve_release",
        "signature",
        "signed",
        "certificate",
        "human_reviewed_by",
        "licensed_counsel",
        "counsel_approval",
    }
)
FORBIDDEN_NOTE_TOKENS = frozenset(
    {
        "approval_authoritative",
        "clears_legal_hold",
        "legal_hold_cleared",
        "counsel_approval",
    }
)
ALLOWED_DECISIONS = frozenset({"approve", "return_for_qa", "hold"})
RECORD_KIND = "NON_AUTHORITATIVE_REVIEW_RECORD"


def _reject_forbidden_keys(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            lowered = str(key).lower().replace("-", "_")
            child_path = f"{path}.{key}" if path else str(key)
            if lowered in FORBIDDEN_AUTHORITY_KEYS:
                raise CounselImportError(
                    "Forged or self-attested approval fields are rejected."
                )
            if path == "" and lowered not in ALLOWED_KEYS:
                raise CounselImportError(
                    f"Counsel review bundle has unknown field: {key}."
                )
            if path != "":
                raise CounselImportError(
                    "Nested counsel review objects are rejected."
                )
            _reject_forbidden_keys(child, child_path)
        return
    if isinstance(value, list):
        raise CounselImportError("Counsel review arrays are rejected.")


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
    _reject_forbidden_keys(value)
    missing = ALLOWED_KEYS - {"notes"} - set(value)
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
    notes = value.get("notes", "")
    if notes is None:
        notes = ""
    if not isinstance(notes, str):
        raise CounselImportError("notes must be a string.")
    lowered_notes = notes.lower()
    if any(token in lowered_notes for token in FORBIDDEN_NOTE_TOKENS):
        raise CounselImportError(
            "Forged or self-attested approval fields are rejected."
        )
    return {
        "kind": RECORD_KIND,
        "mode": "offline_counsel_review",
        "case_id": expected_case_id,
        "reviewed_by": reviewed_by,
        "claimed_decision": value["decision"],
        "notes": notes.strip(),
        "authoritative": False,
        "clears_legal_hold": False,
        "applies_human_approval": False,
        "synthetic_released": False,
    }
