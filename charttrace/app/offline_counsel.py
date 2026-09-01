"""Offline-only counsel review bundle import."""

import json
from pathlib import Path
from typing import Any, Dict


class CounselImportError(ValueError):
    pass


REQUIRED_KEYS = {"mode", "case_id", "reviewed_by", "decision"}


def import_counsel_review(path: Path, expected_case_id: str) -> Dict[str, Any]:
    """Read a local review decision; never fetch remote content."""
    path = Path(path)
    if not path.is_file():
        raise CounselImportError("Counsel review bundle must be a local file.")
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
    return {
        "mode": "offline_counsel_review",
        "case_id": expected_case_id,
        "reviewed_by": str(value["reviewed_by"]).strip(),
        "decision": value["decision"],
        "notes": str(value.get("notes", "")).strip(),
    }
