#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed companion checker for historical Gemini V4 convergence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import check_ledger as current

SCHEMA = "titan-v4-gemini-historical-convergence/v1"
ORIGIN_BUCKET = "historical_gemini_lineage"
REQUIRED_IDS = frozenset({
    "gemini.flash-market-goop",
    "gemini.idle-service",
    "gemini.legacy-g01-e11",
    "gemini.legacy-g01-e20",
    "gemini.legacy-g01-o01",
    "gemini.legacy-g01-shop",
    "gemini.pro-capital",
    "gemini.s33-stratum",
})
ALLOWED_DISPOSITIONS = frozenset({"CORRECTED_DESCENDANT", "FIELD_BLOCKED"})
ALLOWED_ACTIVATIONS = frozenset({"RESEARCH_ONLY", "BLOCKED"})
CERTIFICATE_PATH = (
    "revenue/kaggriculture/cloud-execution-lab/candidates/v4/"
    "research/market-baseline/gemini_market_certificate.py"
)
DEMAND_VELOCITY_PATH = (
    "revenue/kaggriculture/cloud-execution-lab/candidates/v4/"
    "research/market-baseline/demand_velocity.py"
)
ROW_SHED_GUARD_PATH = (
    "revenue/kaggriculture/cloud-execution-lab/candidates/v4/"
    "repairs/gameplay/row-shed-sell-order/novel_rank_guard.py"
)


def validate_historical_document(doc: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    if doc.get("schema") != SCHEMA:
        raise current.ConvergenceError(f"historical schema must be {SCHEMA}")
    if doc.get("canonical_workspace") != current.V4_PREFIX.rstrip("/"):
        raise current.ConvergenceError("historical canonical_workspace drift")
    current._plain_nonempty(doc.get("purpose"), "purpose")
    if doc.get("origin_bucket") != ORIGIN_BUCKET:
        raise current.ConvergenceError(f"origin_bucket must be {ORIGIN_BUCKET}")
    if doc.get("runtime_activation_implied") is not False:
        raise current.ConvergenceError("historical ledger must not imply runtime activation")

    items = doc.get("entries")
    if not isinstance(items, list):
        raise current.ConvergenceError("historical entries must be a list")
    if doc.get("entry_count") != len(items):
        raise current.ConvergenceError("historical entry_count mismatch")

    ids: list[str] = []
    by_id: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(items):
        if not isinstance(entry, dict):
            raise current.ConvergenceError(f"historical entries[{index}] must be an object")
        entry_id = current._plain_nonempty(entry.get("id"), f"historical entries[{index}].id")
        ids.append(entry_id)
        by_id[entry_id] = entry
        for field in ("gemini_label", "source_lineage", "literal_claim", "best_form", "next_gate"):
            current._plain_nonempty(entry.get(field), f"{entry_id}.{field}")

        disposition = entry.get("disposition")
        if disposition not in ALLOWED_DISPOSITIONS:
            raise current.ConvergenceError(f"{entry_id} invalid historical disposition {disposition!r}")
        activation = entry.get("activation")
        if activation not in ALLOWED_ACTIVATIONS:
            raise current.ConvergenceError(f"{entry_id} invalid historical activation {activation!r}")
        if disposition == "FIELD_BLOCKED" and activation != "BLOCKED":
            raise current.ConvergenceError(f"{entry_id} FIELD_BLOCKED must use BLOCKED activation")
        if disposition == "CORRECTED_DESCENDANT" and activation != "RESEARCH_ONLY":
            raise current.ConvergenceError(f"{entry_id} corrected descendant must remain RESEARCH_ONLY")
        if entry.get("do_not_repeat_without_new_evidence") is not True:
            raise current.ConvergenceError(f"{entry_id} historical heuristic must remain durably fenced")

        evidence = entry.get("canonical_evidence")
        if not isinstance(evidence, list) or not evidence:
            raise current.ConvergenceError(f"{entry_id} must have canonical_evidence")
        if len(evidence) != len(set(evidence)):
            raise current.ConvergenceError(f"{entry_id} has duplicate canonical evidence")
        for rel in evidence:
            current._regular_file_under_v4(repo_root, rel, entry_id)

        pulls = entry.get("provenance_pull_numbers")
        if not isinstance(pulls, list) or not pulls:
            raise current.ConvergenceError(f"{entry_id} must retain PR provenance")
        if any(type(n) is not int or n <= 0 for n in pulls):
            raise current.ConvergenceError(f"{entry_id} has invalid PR provenance")
        if pulls != sorted(set(pulls)):
            raise current.ConvergenceError(f"{entry_id} PR provenance must be sorted and unique")

    if len(ids) != len(set(ids)):
        raise current.ConvergenceError("historical duplicate entry id")
    actual = set(ids)
    missing = sorted(REQUIRED_IDS - actual)
    extra = sorted(actual - REQUIRED_IDS)
    if missing or extra:
        raise current.ConvergenceError(f"historical coverage mismatch missing={missing} extra={extra}")
    if ids != sorted(ids):
        raise current.ConvergenceError("historical entries must be sorted by id")

    for entry_id in ("gemini.legacy-g01-e11", "gemini.legacy-g01-o01"):
        if CERTIFICATE_PATH not in by_id[entry_id]["canonical_evidence"]:
            raise current.ConvergenceError(f"{entry_id} must consume the public market certificate")
    if DEMAND_VELOCITY_PATH not in by_id["gemini.legacy-g01-shop"]["canonical_evidence"]:
        raise current.ConvergenceError("legacy G01 shop must consume current demand_velocity.py")

    s33 = by_id["gemini.s33-stratum"]
    if s33["disposition"] != "FIELD_BLOCKED" or s33["activation"] != "BLOCKED":
        raise current.ConvergenceError("S33 must remain blocked pending final-action evidence")
    if ROW_SHED_GUARD_PATH not in s33["canonical_evidence"]:
        raise current.ConvergenceError("S33 must point at the existing row-shed authority")
    if "downstream canonical market-pressure" not in s33["best_form"]:
        raise current.ConvergenceError("S33 must require downstream pressure novelty")
    if "returned to the engine" not in s33["next_gate"]:
        raise current.ConvergenceError("S33 must require returned-action evidence")

    return {
        "status": "PASS",
        "schema": SCHEMA,
        "entry_count": len(ids),
        "ids": sorted(ids),
    }


def validate_historical_path(path: Path, repo_root: Path | None = None) -> dict[str, Any]:
    path = path.resolve()
    root = repo_root.resolve() if repo_root is not None else current.find_repo_root(path.parent)
    return validate_historical_document(current.load_strict_json(path), root)


def validate_bundle(directory: Path, repo_root: Path | None = None) -> dict[str, Any]:
    directory = directory.resolve()
    root = repo_root.resolve() if repo_root is not None else current.find_repo_root(directory)
    recent = current.validate_path(directory / "GEMINI-ANTIGRAVITY.json", root)
    historical = validate_historical_path(directory / "GEMINI-HISTORICAL.json", root)
    return {
        "status": "PASS",
        "recent_entry_count": recent["entry_count"],
        "historical_entry_count": historical["entry_count"],
        "combined_entry_count": recent["entry_count"] + historical["entry_count"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args()
    try:
        result = validate_bundle(Path(__file__).resolve().parent, args.repo_root)
    except current.ConvergenceError as exc:
        print(f"FAIL: {exc}")
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
