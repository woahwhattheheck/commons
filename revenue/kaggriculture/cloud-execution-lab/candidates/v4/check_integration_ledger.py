#!/usr/bin/env python3
"""Fail closed on stale or contradictory TITAN V4 integration custody.

This is coordination/tooling only.  It does not import candidate gameplay, execute
legacy materializers, promote defaults, or decide economic gates.  It verifies
that CANONICAL.json, INTEGRATION.json, and raw-payload blocker manifests describe
one coherent main-line workspace.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent


class LedgerError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LedgerError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LedgerError(f"{path} must contain a JSON object")
    return value


def _rows(ledger: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = ledger.get(key)
    if not isinstance(value, list):
        raise LedgerError(f"INTEGRATION.json {key!r} must be a list")
    out: list[dict[str, Any]] = []
    for index, row in enumerate(value):
        if not isinstance(row, dict):
            raise LedgerError(f"INTEGRATION.json {key}[{index}] must be an object")
        lane = row.get("lane")
        if not isinstance(lane, str) or not lane.strip():
            raise LedgerError(f"INTEGRATION.json {key}[{index}] has invalid lane")
        out.append(row)
    return out


def _lane_set(rows: list[dict[str, Any]]) -> set[str]:
    return {str(row["lane"]) for row in rows}


def _require_nonempty_text(
    row: dict[str, Any],
    lane: str,
    field: str,
    errors: list[str],
    *,
    label: str,
) -> None:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} lane {lane!r} lacks {field}")


def validate(root: Path = HERE) -> list[str]:
    canonical = _load(root / "CANONICAL.json")
    ledger = _load(root / "INTEGRATION.json")
    errors: list[str] = []

    branch = ledger.get("canonical_branch")
    workspace = ledger.get("workspace")
    if branch != "main":
        errors.append(f"canonical_branch must be 'main', got {branch!r}")
    if canonical.get("canonical_branch") != branch:
        errors.append("CANONICAL canonical_branch disagrees with INTEGRATION canonical_branch")
    if canonical.get("workspace") != workspace:
        errors.append("CANONICAL workspace disagrees with INTEGRATION workspace")

    landed = _rows(ledger, "landed")
    recovered = _rows(ledger, "recovered_not_yet_composed")
    blocked = _rows(ledger, "custody_blocked")
    negative = _rows(ledger, "negative_or_parked")

    landed_lanes = _lane_set(landed)
    recovered_lanes = _lane_set(recovered)
    blocked_lanes = _lane_set(blocked)
    negative_lanes = _lane_set(negative)

    for label, overlap in (
        ("landed/recovered", landed_lanes & recovered_lanes),
        ("recovered/blocked", recovered_lanes & blocked_lanes),
        ("recovered/negative", recovered_lanes & negative_lanes),
        ("blocked/negative", blocked_lanes & negative_lanes),
    ):
        if overlap:
            errors.append(f"contradictory {label} lanes: {sorted(overlap)!r}")

    # A negative/parked lane may have historical custody elsewhere, but it must
    # never be represented as a newly recovered or raw-custody work item above.
    for row in negative:
        disposition = row.get("disposition")
        if not isinstance(disposition, str) or not disposition:
            errors.append(f"negative/parked lane {row['lane']!r} lacks disposition")

    # Custody rows have two deliberately distinct contracts:
    #
    # * awaiting_raw_payload is a live source blocker.  The blocker directory and
    #   MANIFEST must exist and independently say that exact raw bytes are owed.
    # * historical_evidence_gap_not_source_blocker records missing archival
    #   receipts for a component whose exact current source/test custody already
    #   exists.  It must name what is available, what is missing, and what may be
    #   done if the history resurfaces, but it must NOT require an "awaiting"
    #   manifest or masquerade as a live source blocker.
    #
    # Any other status is rejected rather than being silently treated as either.
    for row in blocked:
        lane = str(row["lane"])
        custody_path = row.get("custody_path")
        status = row.get("status")

        if not isinstance(custody_path, str) or not custody_path.strip():
            errors.append(f"custody lane {lane!r} lacks custody_path")
            continue
        path = root / custody_path
        if not path.is_dir():
            errors.append(f"custody lane {lane!r} missing custody directory {custody_path!r}")
            continue

        if status == "historical_evidence_gap_not_source_blocker":
            for field in ("available", "missing", "required"):
                _require_nonempty_text(
                    row,
                    lane,
                    field,
                    errors,
                    label="historical evidence gap",
                )
            continue

        if status != "awaiting_raw_payload":
            errors.append(f"custody lane {lane!r} has unsupported status {status!r}")
            continue

        manifest_path = path / "MANIFEST.json"
        try:
            manifest = _load(manifest_path)
        except LedgerError as exc:
            errors.append(str(exc))
            continue
        if manifest.get("lane") != lane:
            errors.append(
                f"blocked lane {lane!r} disagrees with {custody_path}/MANIFEST.json lane "
                f"{manifest.get('lane')!r}"
            )
        if manifest.get("status") != "awaiting_raw_payload":
            errors.append(
                f"blocked lane {lane!r} manifest status is {manifest.get('status')!r}, "
                "expected 'awaiting_raw_payload'"
            )
        required = manifest.get("required_next_step")
        if not isinstance(required, str) or not required.strip():
            errors.append(f"blocked lane {lane!r} manifest lacks required_next_step")

    # Prevent the most dangerous stale-ledger regression: a lane explicitly
    # retired/NO_BUILD must not simultaneously masquerade as active landed work.
    active_status_tokens = ("default_off", "promoted", "active", "enabled")
    active_landed = {
        str(row["lane"])
        for row in landed
        if any(token in str(row.get("status", "")).lower() for token in active_status_tokens)
    }
    for lane in sorted(active_landed & negative_lanes):
        disposition = next(
            str(row.get("disposition", "")) for row in negative if row["lane"] == lane
        ).lower()
        if "no_build" in disposition or "rejected" in disposition or "do_not_promote" in disposition:
            errors.append(f"retired/NO_BUILD lane {lane!r} is also represented as active landed work")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"TITAN V4 integration ledger INVALID ({len(errors)} error(s))", file=sys.stderr)
        return 1
    print("TITAN V4 integration ledger OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
