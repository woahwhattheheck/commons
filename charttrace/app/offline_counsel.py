"""Offline-only counsel review bundle import."""

import json
from pathlib import Path
from typing import Any, Dict

from .paths import PathBoundaryError, validate_local_file


class CounselImportError(ValueError):
    pass


REQUIRED_KEYS = {"mode", "case_id", "reviewed_by", "decision"}


def import_counsel_review(path: Path, expected_case_id: str) -> Dict[str, Any]:
    """Import an unsigned record without granting counsel approval authority."""
    try:
        path = validate_local_file(path)
    except PathBoundaryError as error:
        raise CounselImportError(str(error)) from error
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise CounselImportError("Counsel review bundle must be a JSON object.")
    missing = REQUIRED_KEYS - set(value)
    if missing:
        raise CounselImportError(
            f"Counsel review bundle is missing: {', '.join(sorted(missing))}."
        )
    if value["mode"] != "offline_counsel_review":
        raise CounselImportError("Bundle mode must be offline_counsel_review.")
    if value["case_id"] != expected_case_id:
        raise CounselImportError("Counsel review bundle case does not match.")
    if value["decision"] not in {"approve", "return_for_qa", "hold"}:
        raise CounselImportError("Unknown counsel review decision.")
    if (
        value.get("authoritative") is True
        or value.get("approved") is True
        or value.get("signature_state") not in {None, "unsigned"}
    ):
        raise CounselImportError(
            "Unsigned imports may not self-assert approval or authority."
        )
    reviewed_by = str(value["reviewed_by"]).strip()
    if not reviewed_by:
        raise CounselImportError("A reported reviewer name is required.")
    return {
        "mode": "offline_counsel_review",
        "case_id": expected_case_id,
        "reviewed_by": reviewed_by,
        "reported_decision": value["decision"],
        "notes": str(value.get("notes", "")).strip(),
        "authoritative": False,
        "signature_state": "unsigned",
        "status": "NON_AUTHORITATIVE_RECORD_ONLY",
    }
