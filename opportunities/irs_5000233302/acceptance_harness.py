#!/usr/bin/env python3
"""Synthetic-only deterministic pipeline reconciliation proof.

The harness is a demonstration primitive for the bounded workshare described in
this opportunity packet. It never performs a network call or production action,
and its receipt deliberately excludes row values.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA = "irs.5000233302.pipeline_acceptance_fixture/v1"
RECEIPT_SCHEMA = "irs.5000233302.pipeline_acceptance_receipt/v1"
MAX_BYTES = 2_000_000
KEY_RE = re.compile(r"SYN-[A-Z0-9][A-Z0-9._-]{0,63}")


class AcceptanceError(ValueError):
    pass


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise AcceptanceError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _bad_constant(value: str):
    raise AcceptanceError(f"non-finite JSON value: {value}")


def _safe(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if type(value) is int:
        if abs(value) > 9_007_199_254_740_991:
            raise AcceptanceError(f"unsafe integer at {path}")
        return
    if isinstance(value, float):
        raise AcceptanceError(f"floats forbidden at {path}")
    if isinstance(value, list):
        if len(value) > 10_000:
            raise AcceptanceError(f"array too large at {path}")
        for i, item in enumerate(value):
            _safe(item, f"{path}[{i}]")
        return
    if isinstance(value, dict):
        if len(value) > 1_000:
            raise AcceptanceError(f"object too large at {path}")
        for key, item in value.items():
            if not isinstance(key, str):
                raise AcceptanceError(f"non-string key at {path}")
            _safe(item, f"{path}.{key}")
        return
    raise AcceptanceError(f"unsupported value at {path}")


def canonical_bytes(value: Any) -> bytes:
    _safe(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical_bytes(value)
    return hashlib.sha256(raw).hexdigest()


def loads(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise AcceptanceError("fixture bytes invalid or too large")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=_bad_constant,
        )
    except UnicodeDecodeError as exc:
        raise AcceptanceError("fixture must be UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise AcceptanceError("fixture is invalid JSON") from exc
    if not isinstance(value, dict):
        raise AcceptanceError("fixture root must be object")
    _safe(value)
    return value


def load(path: Path) -> dict:
    if path.is_symlink():
        raise AcceptanceError("symlink fixture refused")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise AcceptanceError(f"fixture read failed: {exc}") from exc
    return loads(raw)


def _rows(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, list):
        raise AcceptanceError(f"{label} must be a list")
    out: dict[str, Any] = {}
    for i, row in enumerate(value):
        if not isinstance(row, dict) or set(row) != {"key", "value"}:
            raise AcceptanceError(f"{label}[{i}] must have exactly key,value")
        key = row["key"]
        if not isinstance(key, str) or not KEY_RE.fullmatch(key):
            raise AcceptanceError(f"{label}[{i}] key must be synthetic")
        if key in out:
            raise AcceptanceError(f"duplicate record key in {label}: {key}")
        _safe(row["value"], f"{label}[{i}].value")
        out[key] = row["value"]
    return out


def evaluate(fixture: dict) -> dict:
    expected_keys = {
        "schema",
        "classification",
        "pipeline_id",
        "source",
        "expected_target",
        "actual_target",
    }
    if set(fixture) != expected_keys:
        raise AcceptanceError(
            f"fixture keys mismatch missing={sorted(expected_keys-set(fixture))} "
            f"extra={sorted(set(fixture)-expected_keys)}"
        )
    if fixture["schema"] != SCHEMA:
        raise AcceptanceError("fixture schema mismatch")
    if fixture["classification"] != "SYNTHETIC_ONLY":
        raise AcceptanceError("only SYNTHETIC_ONLY fixtures are accepted")
    pipeline_id = fixture["pipeline_id"]
    if (
        not isinstance(pipeline_id, str)
        or not pipeline_id.startswith("synthetic/")
        or len(pipeline_id) > 200
    ):
        raise AcceptanceError("pipeline_id must be synthetic/*")
    source = _rows(fixture["source"], "source")
    expected = _rows(fixture["expected_target"], "expected_target")
    actual = _rows(fixture["actual_target"], "actual_target")

    source_keys = set(source)
    expected_keys_set = set(expected)
    actual_keys = set(actual)

    source_lineage_missing = sorted(expected_keys_set - source_keys)
    source_lineage_extra = sorted(source_keys - expected_keys_set)
    missing = sorted(expected_keys_set - actual_keys)
    extra = sorted(actual_keys - expected_keys_set)
    common = sorted(expected_keys_set & actual_keys)
    mismatched = [
        key for key in common
        if canonical_bytes(expected[key]) != canonical_bytes(actual[key])
    ]

    checks = {
        "source_lineage_exact": not source_lineage_missing
        and not source_lineage_extra,
        "target_keyset_exact": not missing and not extra,
        "target_values_exact": not mismatched,
    }
    state = "PASS" if all(checks.values()) else "FAIL"

    return {
        "schema": RECEIPT_SCHEMA,
        "pipeline_id": pipeline_id,
        "classification": "SYNTHETIC_ONLY",
        "state": state,
        "checks": checks,
        "counts": {
            "source": len(source),
            "expected_target": len(expected),
            "actual_target": len(actual),
        },
        "source_lineage_missing_keys": source_lineage_missing,
        "source_lineage_extra_keys": source_lineage_extra,
        "missing_target_keys": missing,
        "extra_target_keys": extra,
        "mismatched_target_keys": mismatched,
        "digests": {
            "source_sha256": digest(fixture["source"]),
            "expected_target_sha256": digest(fixture["expected_target"]),
            "actual_target_sha256": digest(fixture["actual_target"]),
        },
        "authority": {
            "production_data_access_authorized": False,
            "production_deployment_authorized": False,
            "irs_system_access_authorized": False,
            "acceptance_on_behalf_of_prime_or_government_authorized": False,
            "payment_or_revenue_claim_authorized": False,
        },
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: acceptance_harness.py FIXTURE.json", file=sys.stderr)
        return 2
    try:
        receipt = evaluate(load(Path(argv[1])))
    except AcceptanceError as exc:
        print(json.dumps({"state": "ERROR", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(receipt, sort_keys=True, indent=2))
    return 0 if receipt["state"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
