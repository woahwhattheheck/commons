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
EXPECTED_PACK_SUPPORT = {
    "official.py": "83e53481e3f71be30062a87a15439aa06380f6a917d066e8c1807b1eaefb6b23",
    "upstream/manifest.json": "040ed98ca34d47ff56a9fcced2bdde28799a5a3b4a1957baae11406c87320740",
    "upstream/LICENSE": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
    "upstream/agent.py": "9b7682ce9921c8f34080a8be0f7b41598cc12ac7eb14d24e4b707883f25213b6",
    "upstream/errors.py": "957836cef36d5a37f02f53c62081435e24cc08d67be832989e3a01ef2347c4a8",
    "upstream/status_codes.json": "e9af07b92fd5b61f795b47f67e8bf6d502dd45f03729b8b352f8ca989858b417",
    "upstream/utils.py": "537b627b11784d424147ef57ebb0369b039bf83c9f891e81f10486b1f552334b",
}

EXPECTED_APEX_RUNTIME = {
    "agent.so": "d132de713c1ae77ee1498c055deb864d942b101b670c35125636cc66e4e6deae",
    "main.py": "1f7cd5fb8a16585936d2562a3667f85bb6661688718ef58f73006de66148354a",
    "source/include/policy_plugin_abi.hpp": "4eb7647da3660688685a8ff032bd1ada6558605a27ae6b86fc338a91f8b45476",
    "source/include/runtime_types.hpp": "0010c15079e2114e36b5de8b281375db83f202e769e30b27cc437fc0e3ad11f1",
    "source/include/six_day_budget_guard.hpp": "6835d614131c6ca6c57d86e941891d1fea3fa44237f61fd1ab9ac876dd4ebc25",
    "source/policy.cpp": "74b5d7e778c0f4a6e2f0e0725077943dbc319b7d0f5ace4c9070a4ae69db51b3",
    "source/tape.inc": "30b724c3c905d0c03e4ef38d36f96fb7acbd6abef5371abbedee36ea3717e09f",
    "submission_bridge.cpp": "a92ca5b78cae850987a7262122eb83ec9f9a313430e906e1ac08bfe1fd887ff1",
}


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


def _require_subset(manifest: dict[str, str], expected: dict[str, str], field: str) -> None:
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
    _require_subset(contract, EXPECTED_PACK_SUPPORT, f"execution_snapshot.{side}.contract_files")

    # The generated entry must be the deterministic relative-path adapter used by
    # the immutable recorder; no temporary path is allowed to affect its bytes.
    expected_snapshot_entry = immutable._sha_bytes(
        immutable._deterministic_adapter("official.py", "main.py")
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
        _require_subset(candidate, EXPECTED_APEX_RUNTIME, "execution_snapshot.opponent.candidate_files")


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
    _require_subset(engine_files, base.EXPECTED["engine"], "execution_snapshot.control.engine_files")
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
