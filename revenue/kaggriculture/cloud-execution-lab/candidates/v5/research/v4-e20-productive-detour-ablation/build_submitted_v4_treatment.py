# SPDX-License-Identifier: Apache-2.0
"""Build an authenticated one-semantic-member E20 treatment from submitted V4.

The retained competition archive is the authority.  Do not substitute the
repository's contemporaneous CURRENT archive: those are different artifacts.
The treatment changes only the redundant-hire helper's semantics; SOURCE.json
is regenerated as package metadata so it truthfully binds the changed helper.
Every other archive member must remain byte-identical to control.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
from typing import Any

import ablate_e20_productive_detour as ablation

SUBMITTED_V4_ARCHIVE_SHA256 = (
    "4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b"
)
TARGET_MEMBER = ablation.HELPER_PATH
SOURCE_MEMBER = "SOURCE.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_regular_members(archive_bytes: bytes) -> list[tuple[tarfile.TarInfo, bytes]]:
    rows: list[tuple[tarfile.TarInfo, bytes]] = []
    names: set[str] = set()
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
        for info in archive.getmembers():
            if info.name in names:
                raise ValueError(f"duplicate archive member: {info.name}")
            names.add(info.name)
            if not info.isfile():
                raise ValueError(f"non-regular archive member: {info.name}")
            stream = archive.extractfile(info)
            if stream is None:
                raise ValueError(f"unreadable archive member: {info.name}")
            rows.append((copy.copy(info), stream.read()))
    return rows


def _rewrite_source_manifest(
    source_bytes: bytes,
    *,
    control_helper: bytes,
    treatment_helper: bytes,
    control_archive_sha256: str,
) -> bytes:
    try:
        manifest = json.loads(source_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("SOURCE.json is not strict UTF-8 JSON") from error
    if not isinstance(manifest, dict) or not isinstance(manifest.get("runtime"), dict):
        raise ValueError("SOURCE.json missing runtime map")
    entry = manifest["runtime"].get(TARGET_MEMBER)
    if not isinstance(entry, dict):
        raise ValueError("SOURCE.json missing redundant-hire runtime entry")
    if entry.get("sha256") != sha256(control_helper) or entry.get("bytes") != len(control_helper):
        raise ValueError("SOURCE.json redundant-hire identity does not match archive member")

    entry["sha256"] = sha256(treatment_helper)
    entry["bytes"] = len(treatment_helper)
    manifest["experiment"] = {
        "kind": "submitted-v4-e20-productive-detour-off",
        "control_archive_sha256": control_archive_sha256,
        "semantic_member": TARGET_MEMBER,
        "control_helper_git_blob": ablation.V4_HELPER_GIT_BLOB,
        "treatment_helper_git_blob": ablation.git_blob(treatment_helper),
        "source_authority": {
            "submitted_v4_commit": ablation.V4_COMMIT,
            "submitted_v31_commit": ablation.V31_COMMIT,
        },
    }
    return (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _pack(rows: list[tuple[tarfile.TarInfo, bytes]]) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", mtime=0, filename="") as gz:
        with tarfile.open(fileobj=gz, mode="w") as archive:
            for original, data in rows:
                info = copy.copy(original)
                info.size = len(data)
                # Avoid host-specific pax side effects while retaining the
                # control member's ordinary permission/ownership metadata.
                info.pax_headers = dict(original.pax_headers or {})
                archive.addfile(info, io.BytesIO(data))
    return output.getvalue()


def build_treatment_archive(
    control_archive: bytes,
    v31_helper: bytes,
    *,
    expected_control_sha256: str = SUBMITTED_V4_ARCHIVE_SHA256,
) -> tuple[bytes, dict[str, Any]]:
    control_digest = sha256(control_archive)
    if control_digest != expected_control_sha256:
        raise ValueError("submitted V4 archive SHA256 mismatch")
    if ablation.git_blob(v31_helper) != ablation.V31_HELPER_GIT_BLOB:
        raise ValueError("submitted V3.1 redundant_hire.py drift")

    rows = _read_regular_members(control_archive)
    index = {info.name: i for i, (info, _data) in enumerate(rows)}
    if TARGET_MEMBER not in index:
        raise ValueError("submitted V4 archive missing redundant-hire helper")
    if SOURCE_MEMBER not in index:
        raise ValueError("submitted V4 archive missing SOURCE.json")

    target_i = index[TARGET_MEMBER]
    source_i = index[SOURCE_MEMBER]
    control_helper = rows[target_i][1]
    if ablation.git_blob(control_helper) != ablation.V4_HELPER_GIT_BLOB:
        raise ValueError("submitted V4 archive helper does not match source authority")

    treatment_helper = ablation.ablate_productive_detour(control_helper, v31_helper)
    treatment_source = _rewrite_source_manifest(
        rows[source_i][1],
        control_helper=control_helper,
        treatment_helper=treatment_helper,
        control_archive_sha256=control_digest,
    )
    rows[target_i] = (rows[target_i][0], treatment_helper)
    rows[source_i] = (rows[source_i][0], treatment_source)
    treatment_archive = _pack(rows)

    control_rows = {info.name: data for info, data in _read_regular_members(control_archive)}
    treatment_rows = {info.name: data for info, data in _read_regular_members(treatment_archive)}
    if set(control_rows) != set(treatment_rows):
        raise ValueError("treatment changed archive member set")
    changed = sorted(
        name for name in control_rows if control_rows[name] != treatment_rows[name]
    )
    expected_changed = sorted([SOURCE_MEMBER, TARGET_MEMBER])
    if changed != expected_changed:
        raise ValueError(f"unexpected treatment member diff: {changed}")

    receipt = {
        "schema": 1,
        "control_archive_sha256": control_digest,
        "treatment_archive_sha256": sha256(treatment_archive),
        "member_count": len(control_rows),
        "changed_members": changed,
        "semantic_changed_members": [TARGET_MEMBER],
        "metadata_changed_members": [SOURCE_MEMBER],
        "control_helper_git_blob": ablation.git_blob(control_helper),
        "treatment_helper_git_blob": ablation.git_blob(treatment_helper),
        "v31_deletion_tail_authority_git_blob": ablation.V31_HELPER_GIT_BLOB,
    }
    return treatment_archive, receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-archive", required=True, type=Path)
    parser.add_argument("--v31-helper", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()

    control = args.control_archive.read_bytes()
    v31 = args.v31_helper.read_bytes()
    treatment, receipt = build_treatment_archive(control, v31)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(treatment)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
