#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed validator for cross-identity historical Gemini lineages."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import check_ledger as C

SCHEMA = "titan-v4-gemini-labeled-history/v1"
REQUIRED_IDS = frozenset({
    "gemini.endgame-calendar-skip",
    "gemini.endgame-glut-bleed",
    "gemini.flash-market-goop",
    "gemini.idle-service",
    "gemini.legacy-g01-e11",
    "gemini.legacy-g01-e20",
    "gemini.legacy-g01-o01",
    "gemini.legacy-g01-shop",
    "gemini.meridian-adaptive-recourse",
    "gemini.meridian-hidden-inventory",
    "gemini.pro-capital",
    "gemini.s33-stratum",
})
MUST_STAY_BLOCKED = frozenset({
    "gemini.endgame-calendar-skip",
    "gemini.endgame-glut-bleed",
    "gemini.idle-service",
    "gemini.meridian-adaptive-recourse",
    "gemini.pro-capital",
    "gemini.s33-stratum",
})
STALE_DONOR_BASENAMES = frozenset({"gemini_market_certificate.py"})


class LabeledHistoryError(C.ConvergenceError):
    pass


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LabeledHistoryError(f"{field} must be a non-empty string")
    return value


def validate_document(doc: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    if doc.get("schema") != SCHEMA:
        raise LabeledHistoryError(f"schema must be {SCHEMA}")
    if doc.get("runtime_activation_implied") is not False:
        raise LabeledHistoryError("runtime_activation_implied must remain false")

    entries = doc.get("entries")
    if not isinstance(entries, list):
        raise LabeledHistoryError("entries must be a list")
    if doc.get("entry_count") != len(entries):
        raise LabeledHistoryError("entry_count mismatch")

    ids: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise LabeledHistoryError(f"entries[{index}] must be an object")
        entry_id = _nonempty(entry.get("id"), f"entries[{index}].id")
        ids.append(entry_id)
        for field in ("gemini_label", "source_lineage", "literal_claim", "best_form", "next_gate"):
            _nonempty(entry.get(field), f"{entry_id}.{field}")

        disposition = entry.get("disposition")
        activation = entry.get("activation")
        if disposition not in C.ALLOWED_DISPOSITIONS:
            raise LabeledHistoryError(f"{entry_id} invalid disposition {disposition!r}")
        if activation not in C.ALLOWED_ACTIVATIONS:
            raise LabeledHistoryError(f"{entry_id} invalid activation {activation!r}")
        if entry_id in MUST_STAY_BLOCKED:
            if disposition != "FIELD_BLOCKED" or activation != "BLOCKED":
                raise LabeledHistoryError(f"{entry_id} must remain FIELD_BLOCKED/BLOCKED")
            if entry.get("do_not_repeat_without_new_evidence") is not True:
                raise LabeledHistoryError(f"{entry_id} must remain durably fenced")

        evidence = entry.get("canonical_evidence")
        if not isinstance(evidence, list) or not evidence:
            raise LabeledHistoryError(f"{entry_id} must have canonical_evidence")
        if len(evidence) != len(set(evidence)):
            raise LabeledHistoryError(f"{entry_id} has duplicate canonical evidence")
        for rel in evidence:
            if Path(str(rel)).name in STALE_DONOR_BASENAMES:
                raise LabeledHistoryError(f"{entry_id} points at stale donor-only evidence: {rel}")
            C._regular_file_under_v4(repo_root, rel, entry_id)

        pulls = entry.get("provenance_pull_numbers")
        if not isinstance(pulls, list) or not pulls:
            raise LabeledHistoryError(f"{entry_id} must retain provenance_pull_numbers")
        if any(type(value) is not int or value <= 0 for value in pulls):
            raise LabeledHistoryError(f"{entry_id} has invalid PR provenance")
        if pulls != sorted(set(pulls)):
            raise LabeledHistoryError(f"{entry_id} PR provenance must be sorted and unique")

    if len(ids) != len(set(ids)):
        raise LabeledHistoryError("duplicate entry id")
    actual = set(ids)
    if actual != REQUIRED_IDS:
        raise LabeledHistoryError(
            f"coverage mismatch missing={sorted(REQUIRED_IDS - actual)} extra={sorted(actual - REQUIRED_IDS)}"
        )
    if ids != sorted(ids):
        raise LabeledHistoryError("entries must be sorted by id")

    return {
        "status": "PASS",
        "schema": SCHEMA,
        "entry_count": len(ids),
        "blocked_count": sum(1 for e in entries if e["disposition"] == "FIELD_BLOCKED"),
        "corrected_count": sum(1 for e in entries if e["disposition"] == "CORRECTED_DESCENDANT"),
    }


def validate_path(path: Path, repo_root: Path | None = None) -> dict[str, Any]:
    path = path.resolve()
    root = repo_root if repo_root is not None else C.find_repo_root(path.parent)
    return validate_document(C.load_strict_json(path), root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "history",
        nargs="?",
        type=Path,
        default=Path(__file__).with_name("HISTORICAL-LABELED.json"),
    )
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args()
    try:
        result = validate_path(args.history, args.repo_root)
    except C.ConvergenceError as exc:
        print(f"FAIL: {exc}")
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
