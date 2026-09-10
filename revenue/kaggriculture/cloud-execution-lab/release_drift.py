# SPDX-License-Identifier: Apache-2.0
"""Explain and gate drift in the single canonical TITAN release.

The canonical builder intentionally fails closed when source, archive, manifest,
or release pointer diverge.  This companion reports the exact member and field
responsible before the opaque byte-level gate runs; it never publishes files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import build_integrated as b

SCHEMA = "titan-canonical-release-drift/v1"
_MISSING = object()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _read_json_object(path: Path, label: str) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid UTF-8 JSON: {exc}") from exc
    return raw, _object(value, label)


def _summary(value: Any) -> Any:
    """Keep scalar diffs readable and bind larger values without dumping them."""
    if value is _MISSING:
        return {"missing": True}
    if value is None or type(value) in (bool, int, float, str):
        return value
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "json_type": "array" if isinstance(value, list) else "object",
        "bytes": len(encoded),
        "sha256": _sha256(encoded),
    }


def field_deltas(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return deterministic, missing-aware field differences."""
    rows: list[dict[str, Any]] = []
    for field in sorted(set(actual) | set(expected)):
        av = actual[field] if field in actual else _MISSING
        ev = expected[field] if field in expected else _MISSING
        if av != ev:
            rows.append({"field": field, "actual": _summary(av), "expected": _summary(ev)})
    return rows


def compare_manifests(
    actual: Mapping[str, Any], expected: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Compare runtime members separately from release-level metadata."""
    actual_runtime = actual.get("runtime")
    expected_runtime = expected.get("runtime")
    if not isinstance(actual_runtime, dict):
        raise ValueError("actual manifest runtime must be a JSON object")
    if not isinstance(expected_runtime, dict):
        raise ValueError("expected manifest runtime must be a JSON object")

    members: list[dict[str, Any]] = []
    for member in sorted(set(actual_runtime) | set(expected_runtime)):
        ar = actual_runtime.get(member, _MISSING)
        er = expected_runtime.get(member, _MISSING)
        if ar is _MISSING or er is _MISSING:
            members.append(
                {
                    "member": member,
                    "fields": [
                        {
                            "field": "__member__",
                            "actual": _summary(ar),
                            "expected": _summary(er),
                        }
                    ],
                }
            )
            continue
        if not isinstance(ar, dict) or not isinstance(er, dict):
            raise ValueError(f"runtime member {member!r} must be a JSON object")
        changed = field_deltas(ar, er)
        if changed:
            members.append(
                {
                    "member": member,
                    "source_path": er.get("source_path", ar.get("source_path")),
                    "fields": changed,
                }
            )

    actual_meta = {k: v for k, v in actual.items() if k != "runtime"}
    expected_meta = {k: v for k, v in expected.items() if k != "runtime"}
    return members, field_deltas(actual_meta, expected_meta)


def analyze(root: Path | None = None) -> dict[str, Any]:
    """Return a complete, deterministic release/source drift report."""
    root = Path(root) if root is not None else b.ROOT
    expected_archive, expected_manifest_raw, expected_receipt = b.render()
    expected_manifest = _object(
        json.loads(expected_manifest_raw.decode("utf-8")), "expected manifest"
    )
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "clean": False,
        "errors": [],
        "runtime_files_expected": len(expected_manifest.get("runtime", {})),
        "runtime_member_drift": [],
        "manifest_metadata_drift": [],
        "receipt_drift": [],
    }

    try:
        actual_receipt_raw, actual_receipt = _read_json_object(
            root / (b.RECORD + "CURRENT-ARCHIVE.json"), "current release pointer"
        )
        actual_manifest_raw, actual_manifest = _read_json_object(
            root / (b.RECORD + "CURRENT-SOURCE.json"), "current source manifest"
        )
        actual_archive = (root / b.ARCHIVE).read_bytes()

        member_drift, metadata_drift = compare_manifests(actual_manifest, expected_manifest)
        receipt_drift = field_deltas(actual_receipt, expected_receipt)
        report.update(
            runtime_member_drift=member_drift,
            manifest_metadata_drift=metadata_drift,
            receipt_drift=receipt_drift,
            artifacts={
                "archive": {
                    "path": b.ARCHIVE,
                    "actual_bytes": len(actual_archive),
                    "expected_bytes": len(expected_archive),
                    "actual_sha256": _sha256(actual_archive),
                    "expected_sha256": _sha256(expected_archive),
                    "byte_equal": actual_archive == expected_archive,
                },
                "source_manifest": {
                    "path": b.RECORD + "CURRENT-SOURCE.json",
                    "actual_bytes": len(actual_manifest_raw),
                    "expected_bytes": len(expected_manifest_raw),
                    "actual_sha256": _sha256(actual_manifest_raw),
                    "expected_sha256": _sha256(expected_manifest_raw),
                    "byte_equal": actual_manifest_raw == expected_manifest_raw,
                },
                "release_pointer": {
                    "path": b.RECORD + "CURRENT-ARCHIVE.json",
                    "actual_bytes": len(actual_receipt_raw),
                    "actual_sha256": _sha256(actual_receipt_raw),
                    "semantic_equal": actual_receipt == expected_receipt,
                },
            },
        )
        report["clean"] = (
            not member_drift
            and not metadata_drift
            and not receipt_drift
            and actual_archive == expected_archive
            and actual_manifest_raw == expected_manifest_raw
            and actual_receipt == expected_receipt
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report["errors"].append(f"{type(exc).__name__}: {exc}")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="return nonzero when the canonical release is not source-exact",
    )
    args = parser.parse_args(argv)
    report = analyze()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.check and not report["clean"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
