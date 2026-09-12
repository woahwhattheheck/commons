#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact native-9901 validator for the immutable action-divergence witness."""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any

import action_divergence_witness as witness
import immutable_action_divergence_witness as immutable
import validate_native_9901_action_witness as base

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# These hashes come from the retained native-9901 input-custody receipt.
EXPECTED_PACK_SUPPORT = immutable.EXPECTED_PACK_SUPPORT
EXPECTED_APEX_RUNTIME = immutable.EXPECTED_APEX_RUNTIME


class SnapshotValidationError(base.ValidationError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SnapshotValidationError(message)


def _canonical_path(name: Any, field: str) -> str:
    _require(isinstance(name, str) and name, f"{field} path invalid")
    _require("\\" not in name and not name.startswith("/"), f"{field} path noncanonical")
    pieces = name.split("/")
    _require(
        all(piece not in ("", ".", "..") for piece in pieces),
        f"{field} path noncanonical",
    )
    canonical = str(PurePosixPath(name))
    _require(canonical == name, f"{field} path noncanonical")
    return canonical


def _manifest(value: Any, field: str) -> dict[str, str]:
    _require(type(value) is dict and value, f"{field} must be a nonempty object")
    result: dict[str, str] = {}
    for name, sha in value.items():
        canonical = _canonical_path(name, field)
        _require(
            isinstance(sha, str) and _SHA256_RE.fullmatch(sha) is not None,
            f"{field}.{canonical} SHA256 invalid",
        )
        result[canonical] = sha
    return result


def _require_manifest_digest(meta: dict[str, Any], key: str, field: str) -> dict[str, str]:
    manifest = _manifest(meta.get(key), f"{field}.{key}")
    digest_field = key.removesuffix("_files") + "_manifest_sha256"
    claimed = meta.get(digest_field)
    _require(
        isinstance(claimed, str) and _SHA256_RE.fullmatch(claimed) is not None,
        f"{field}.{digest_field} invalid",
    )
    _require(
        claimed == witness._digest(manifest),
        f"{field}.{digest_field} mismatch",
    )
    return manifest


def _require_exact_file_set(
    manifest: dict[str, str], expected: dict[str, str], field: str
) -> None:
    missing = sorted(set(expected) - set(manifest))
    _require(not missing, f"{field} missing required files: {missing}")
    extra = sorted(set(manifest) - set(expected))
    _require(not extra, f"{field} contains extra unauthorized files: {extra}")
    for name, sha in expected.items():
        _require(
            manifest.get(name) == sha,
            f"{field}.{name} mismatch",
        )


def _validate_side(
    authority: dict[str, Any],
    snapshot: dict[str, Any],
    side: str,
    entry_field: str,
    *,
    require_archive: bool,
) -> None:
    meta = snapshot.get(side)
    _require(type(meta) is dict, f"execution_snapshot.{side} missing")
    source_sha = meta.get("source_entry_sha256")
    snap_sha = meta.get("snapshot_entry_sha256")
    _require(
        isinstance(source_sha, str) and _SHA256_RE.fullmatch(source_sha) is not None,
        f"execution_snapshot.{side}.source_entry_sha256 invalid",
    )
    _require(
        isinstance(snap_sha, str) and _SHA256_RE.fullmatch(snap_sha) is not None,
        f"execution_snapshot.{side}.snapshot_entry_sha256 invalid",
    )
    _require(
        source_sha == authority.get(entry_field),
        f"execution_snapshot.{side} source entry differs from report authority",
    )

    candidate = _require_manifest_digest(meta, "candidate_files", f"execution_snapshot.{side}")
    contract = _require_manifest_digest(meta, "contract_files", f"execution_snapshot.{side}")
    _require_exact_file_set(contract, EXPECTED_PACK_SUPPORT, f"execution_snapshot.{side}.contract_files")

    # The generated entry must be the deterministic relative-path adapter used by
    # the immutable recorder; no temporary path is allowed to affect its bytes.
    expected_snapshot_entry = immutable._sha_bytes(
        immutable._deterministic_adapter("official.py", "main.py", contract, candidate)
    )
    _require(
        snap_sha == expected_snapshot_entry,
        f"execution_snapshot.{side}.snapshot_entry_sha256 mismatch",
    )

    archive_digest = meta.get("archive_member_manifest_sha256")
    archive_verified = meta.get("archive_members_verified")
    if require_archive:
        _require(archive_verified is True, f"execution_snapshot.{side} archive not verified")
        _require(
            isinstance(archive_digest, str) and _SHA256_RE.fullmatch(archive_digest) is not None,
            f"execution_snapshot.{side} archive manifest digest invalid",
        )
        _require(
            archive_digest == meta.get("candidate_manifest_sha256"),
            f"execution_snapshot.{side} candidate/archive manifest mismatch",
        )
    else:
        _require(
            archive_verified is False and archive_digest is None,
            "execution_snapshot.opponent must not claim candidate-archive custody",
        )
        _require_exact_file_set(candidate, EXPECTED_APEX_RUNTIME, "execution_snapshot.opponent.candidate_files")


def validate_snapshot_authority(authority: dict[str, Any]) -> dict[str, Any]:
    _require(type(authority) is dict, "authority must be an object")
    snapshot = authority.get("execution_snapshot")
    _require(type(snapshot) is dict, "authority.execution_snapshot missing")
    _require(
        snapshot.get("schema") == immutable.SNAPSHOT_SCHEMA,
        "unexpected execution snapshot schema",
    )

    control = snapshot.get("control")
    _require(type(control) is dict, "execution_snapshot.control missing")
    evaluator_files = _require_manifest_digest(
        control, "evaluator_files", "execution_snapshot.control"
    )
    loader_files = _require_manifest_digest(
        control, "loader_files", "execution_snapshot.control"
    )
    engine_files = _require_manifest_digest(
        control, "engine_files", "execution_snapshot.control"
    )
    _require(
        evaluator_files.get("evaluate.py") == base.EXPECTED["evaluator"],
        "snapshot evaluator bytes differ from native-9901 authority",
    )
    _require(
        loader_files.get("evaluate.py") == base.EXPECTED["loader"],
        "snapshot loader bytes differ from native-9901 authority",
    )
    _require_exact_file_set(engine_files, base.EXPECTED["engine"], "execution_snapshot.control.engine_files")
    _require(
        control.get("engine_sha256") == authority.get("engine_sha256") == base.EXPECTED["engine"],
        "snapshot engine authority mismatch",
    )

    _validate_side(authority, snapshot, "left", "left_entry_sha256", require_archive=True)
    _validate_side(authority, snapshot, "right", "right_entry_sha256", require_archive=True)
    _validate_side(authority, snapshot, "opponent", "opponent_entry_sha256", require_archive=False)

    return {
        "schema": snapshot["schema"],
        "execution_snapshot_sha256": witness._digest(snapshot),
        "immutable_execution_snapshot_verified": True,
    }


def validate(report: dict[str, Any], expected_report_sha256: str) -> dict[str, Any]:
    # First validate the original exact experiment, vectors, terminals and
    # out-of-band commitment. Then require the stronger execution snapshot.
    result = base.validate(report, expected_report_sha256)
    snapshot = validate_snapshot_authority(report["authority"])
    return {**result, **snapshot}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--expected-report-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        result = validate(report, args.expected_report_sha256)
    except (
        OSError,
        json.JSONDecodeError,
        base.ValidationError,
        SnapshotValidationError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"validate_native_9901_action_witness_immutable: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
