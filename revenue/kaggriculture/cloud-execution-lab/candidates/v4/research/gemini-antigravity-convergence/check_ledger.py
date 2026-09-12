#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed convergence checker for the Gemini/Antigravity V4 ledger."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any

SCHEMA = "titan-v4-gemini-antigravity-convergence/v1"
V4_PREFIX = "revenue/kaggriculture/cloud-execution-lab/candidates/v4/"
ALLOWED_DISPOSITIONS = frozenset({
    "SOURCE_REAL_CANDIDATE",
    "CORRECTED_DESCENDANT",
    "FALSIFIED",
    "FIELD_BLOCKED",
})
ALLOWED_ACTIVATIONS = frozenset({
    "RESEARCH_ONLY",
    "DEFAULT_OFF",
    "SOURCE_COMPONENT",
    "BLOCKED",
    "FALSIFIED",
})
ALLOWED_ORIGINS = frozenset({
    "pre_manifest_antigravity",
    "master_manifest",
    "claim_board",
    "metagame_warning",
    "metagame_offensive",
})
REQUIRED_IDS = frozenset([
    "gemini.alternate-water",
    "gemini.apex-clone-radar",
    "gemini.apex-counter-ambush",
    "gemini.demand-velocity",
    "gemini.dynamic-floor-front-run",
    "gemini.egg-singularity",
    "gemini.expansion-tax",
    "gemini.fert-floor-warehouse",
    "gemini.fert-revenue-liquidate",
    "gemini.flash-market",
    "gemini.goose-printer",
    "gemini.idle-hands",
    "gemini.intermittent-starvation",
    "gemini.intraday-hoist",
    "gemini.melon-lifetime-cap",
    "gemini.meridian-adaptive-recourse",
    "gemini.meridian-public-state-maximin",
    "gemini.npc-market-baseline",
    "gemini.plant-decay-timing",
    "gemini.plantguard-same-eod-water",
    "gemini.pro-capital",
    "gemini.rng-frame-advance",
    "gemini.seed-crack-turn1",
    "gemini.seed-overshoot",
    "gemini.short-squeeze",
    "gemini.terminal-mass-hire",
    "gemini.weedbank-action-bank",
    "gemini.wheat-market-denial",
    "gemini.zero-cost-structure-carpet",
])


class ConvergenceError(ValueError):
    """Ledger failed a convergence invariant."""


def _reject_constant(token: str) -> None:
    raise ConvergenceError(f"non-finite JSON token: {token}")


def load_strict_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_constant)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConvergenceError(f"cannot load strict JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConvergenceError("ledger root must be an object")
    return data


def _plain_nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConvergenceError(f"{field} must be a non-empty string")
    return value


def _regular_file_under_v4(repo_root: Path, rel: Any, entry_id: str) -> None:
    rel = _plain_nonempty(rel, f"{entry_id}.canonical_evidence[]")
    posix = PurePosixPath(rel)
    if posix.is_absolute() or ".." in posix.parts:
        raise ConvergenceError(f"{entry_id} evidence escapes repository: {rel}")
    if not rel.startswith(V4_PREFIX):
        raise ConvergenceError(f"{entry_id} evidence is outside canonical V4: {rel}")
    lowered = "/" + rel.lower().strip("/") + "/"
    if "/legacy/" in lowered or "/superseded/" in lowered:
        raise ConvergenceError(f"{entry_id} evidence points at noncanonical ancestry: {rel}")

    root = repo_root.resolve()
    target = root.joinpath(*posix.parts)
    try:
        st = os.lstat(target)
    except OSError as exc:
        raise ConvergenceError(f"{entry_id} missing canonical evidence: {rel}") from exc
    if not stat.S_ISREG(st.st_mode):
        raise ConvergenceError(f"{entry_id} evidence is not a regular file: {rel}")
    resolved_parent = target.parent.resolve()
    try:
        resolved_parent.relative_to(root)
    except ValueError as exc:
        raise ConvergenceError(f"{entry_id} evidence parent escapes repository: {rel}") from exc


def validate_document(doc: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    if doc.get("schema") != SCHEMA:
        raise ConvergenceError(f"schema must be {SCHEMA}")
    if doc.get("canonical_branch") != "main":
        raise ConvergenceError("canonical_branch must be main")
    if doc.get("canonical_workspace") != V4_PREFIX.rstrip("/"):
        raise ConvergenceError("canonical_workspace drift")

    source = doc.get("source_stream")
    if not isinstance(source, dict):
        raise ConvergenceError("source_stream must be an object")
    if source.get("slack_channel_id") != "C0C0Z8AHGP2":
        raise ConvergenceError("unexpected Gemini source channel")
    if source.get("gemini_author_id") != "U0C17K9ALP7":
        raise ConvergenceError("unexpected Gemini author id")
    for key in ("master_manifest_ts", "claim_board_ts", "coverage_claim_ts"):
        _plain_nonempty(source.get(key), f"source_stream.{key}")
    buckets = source.get("included_buckets")
    if not isinstance(buckets, list) or set(buckets) != ALLOWED_ORIGINS:
        raise ConvergenceError("included_buckets must cover every declared Gemini source bucket exactly")

    allowed = doc.get("allowed_dispositions")
    if not isinstance(allowed, list) or set(allowed) != ALLOWED_DISPOSITIONS:
        raise ConvergenceError("allowed_dispositions drift")

    rules = doc.get("convergence_rules")
    if not isinstance(rules, list) or len(rules) < 5 or any(not isinstance(x, str) or not x.strip() for x in rules):
        raise ConvergenceError("convergence_rules must retain the fail-closed policy")

    items = doc.get("entries")
    if not isinstance(items, list):
        raise ConvergenceError("entries must be a list")
    if doc.get("entry_count") != len(items):
        raise ConvergenceError("entry_count mismatch")

    ids: list[str] = []
    for index, entry in enumerate(items):
        if not isinstance(entry, dict):
            raise ConvergenceError(f"entries[{index}] must be an object")
        entry_id = _plain_nonempty(entry.get("id"), f"entries[{index}].id")
        ids.append(entry_id)
        _plain_nonempty(entry.get("gemini_label"), f"{entry_id}.gemini_label")
        _plain_nonempty(entry.get("literal_claim"), f"{entry_id}.literal_claim")
        _plain_nonempty(entry.get("best_form"), f"{entry_id}.best_form")
        _plain_nonempty(entry.get("next_gate"), f"{entry_id}.next_gate")

        origins = entry.get("origin_buckets")
        if not isinstance(origins, list) or not origins:
            raise ConvergenceError(f"{entry_id} must have origin_buckets")
        if len(origins) != len(set(origins)) or not set(origins).issubset(ALLOWED_ORIGINS):
            raise ConvergenceError(f"{entry_id} has invalid/duplicate origin_buckets")

        disposition = entry.get("disposition")
        if disposition not in ALLOWED_DISPOSITIONS:
            raise ConvergenceError(f"{entry_id} has invalid disposition {disposition!r}")
        activation = entry.get("activation")
        if activation not in ALLOWED_ACTIVATIONS:
            raise ConvergenceError(f"{entry_id} has invalid activation {activation!r}")
        if disposition == "FALSIFIED":
            if activation != "FALSIFIED":
                raise ConvergenceError(f"{entry_id} falsified claim must use FALSIFIED activation")
            if entry.get("do_not_repeat_without_new_evidence") is not True:
                raise ConvergenceError(f"{entry_id} falsified claim must be durably fenced")
        if disposition == "FIELD_BLOCKED":
            if activation != "BLOCKED":
                raise ConvergenceError(f"{entry_id} field-blocked claim must use BLOCKED activation")
            if entry.get("do_not_repeat_without_new_evidence") is not True:
                raise ConvergenceError(f"{entry_id} field-blocked claim must be durably fenced")

        evidence = entry.get("canonical_evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ConvergenceError(f"{entry_id} must have canonical_evidence")
        if len(evidence) != len(set(evidence)):
            raise ConvergenceError(f"{entry_id} has duplicate canonical evidence")
        for rel in evidence:
            _regular_file_under_v4(repo_root, rel, entry_id)

        pulls = entry.get("provenance_pull_numbers")
        if not isinstance(pulls, list) or not pulls:
            raise ConvergenceError(f"{entry_id} must retain provenance_pull_numbers")
        if any(type(n) is not int or n <= 0 for n in pulls):
            raise ConvergenceError(f"{entry_id} has invalid PR provenance")
        if pulls != sorted(set(pulls)):
            raise ConvergenceError(f"{entry_id} PR provenance must be sorted and unique")

    if len(ids) != len(set(ids)):
        raise ConvergenceError("duplicate entry id")
    actual = set(ids)
    missing = sorted(REQUIRED_IDS - actual)
    extra = sorted(actual - REQUIRED_IDS)
    if missing or extra:
        raise ConvergenceError(f"coverage mismatch missing={missing} extra={extra}")
    if ids != sorted(ids):
        raise ConvergenceError("entries must be sorted by id for stable review")

    return {
        "status": "PASS",
        "schema": SCHEMA,
        "entry_count": len(ids),
        "dispositions": {name: sum(1 for e in items if e["disposition"] == name)
                         for name in sorted(ALLOWED_DISPOSITIONS)},
    }


def find_repo_root(start: Path) -> Path:
    start = start.resolve()
    for parent in (start, *start.parents):
        if (parent / V4_PREFIX.rstrip("/")).is_dir():
            return parent
    raise ConvergenceError("could not locate repository root containing candidates/v4")


def validate_path(ledger_path: Path, repo_root: Path | None = None) -> dict[str, Any]:
    ledger_path = ledger_path.resolve()
    root = repo_root.resolve() if repo_root is not None else find_repo_root(ledger_path.parent)
    return validate_document(load_strict_json(ledger_path), root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "ledger",
        nargs="?",
        type=Path,
        default=Path(__file__).with_name("GEMINI-ANTIGRAVITY.json"),
    )
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args()
    try:
        result = validate_path(args.ledger, args.repo_root)
    except ConvergenceError as exc:
        print(f"FAIL: {exc}")
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
