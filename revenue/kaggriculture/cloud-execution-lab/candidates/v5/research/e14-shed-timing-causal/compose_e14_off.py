# SPDX-License-Identifier: Apache-2.0
"""Materialize one exact submitted-V4-minus-E14 causal treatment.

This tool is evidence plumbing only.  It authenticates the submitted V4 archive,
replaces exactly the V4 scheduler blob introduced by E14 with its immediate
pre-E14 parent blob, and writes an auditable treatment tree.  It does not claim
that the predecessor scheduler is mechanically preferable: E14 fixed real
unit-stage-before-market shed timing.  A winning rollback therefore identifies a
seller-planning regression to repair while retaining correct engine physics.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile
from typing import Mapping

V31_SOURCE = "a90d888f03987ef0b35cfd20ec3519c6144db08a"
V4_SOURCE = "4af1113154e78c662780e6658cd920daac7902e3"
V4_ARCHIVE_SHA256 = "4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b"

E14_COMMIT = "0cd11d4f66fb7df078d7a0b3487220749db5ec25"
PRE_E14_COMMIT = "e4e0fe6a5207c986a165e0db8b1671a5fa034779"
CONTROL_SCHEDULER_BLOB = "a483b24dd72b580d7d8811636b54d2d44f391575"
TREATMENT_SCHEDULER_BLOB = "d68ae8bbeb0d6efb437770c08fbcc3e2da4f54ff"
ACTIVE_ARLENE_BLOB = "bdb9cf58148a3c7961c085f4902759537decabf6"

SCHEDULER_REPO_PATH = "revenue/kaggriculture/cloud-execution-lab/scheduler.py"
ARLENE_REPO_PATH = (
    "revenue/kaggriculture/cloud-execution-lab/reference/next-panel/vendor/arlene.py"
)
RECEIPT_NAME = "E14-CAUSAL.json"
RECEIPT_SCHEMA = "titan-v5-e14-shed-timing-causal/v1"


@dataclass(frozen=True)
class ArchiveFile:
    data: bytes
    mode: int


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _run_git(repo_root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def git_path_blob(repo_root: Path, revision: str, path: str) -> str:
    return _run_git(repo_root, "rev-parse", f"{revision}:{path}").decode("ascii").strip()


def git_read_blob(repo_root: Path, blob: str) -> bytes:
    raw = _run_git(repo_root, "cat-file", "blob", blob)
    if git_blob_sha1(raw) != blob:
        raise ValueError(f"git returned bytes that do not match requested blob {blob}")
    return raw


def validate_git_ancestry(repo_root: Path) -> dict[str, object]:
    """Authenticate the exact causal edge and its membership in submitted V4."""
    row = _run_git(repo_root, "rev-list", "--parents", "-n", "1", E14_COMMIT)
    parts = row.decode("ascii").strip().split()
    if len(parts) != 2 or parts[0] != E14_COMMIT or parts[1] != PRE_E14_COMMIT:
        raise ValueError(
            "E14 causal identity mismatch: expected exact commit with sole parent "
            f"{PRE_E14_COMMIT}, got {parts}"
        )
    try:
        _run_git(repo_root, "merge-base", "--is-ancestor", E14_COMMIT, V4_SOURCE)
    except subprocess.CalledProcessError as exc:
        raise ValueError(
            f"E14 commit {E14_COMMIT} is not an ancestor of submitted V4 {V4_SOURCE}"
        ) from exc

    expected = {
        (V4_SOURCE, SCHEDULER_REPO_PATH): CONTROL_SCHEDULER_BLOB,
        (E14_COMMIT, SCHEDULER_REPO_PATH): CONTROL_SCHEDULER_BLOB,
        (PRE_E14_COMMIT, SCHEDULER_REPO_PATH): TREATMENT_SCHEDULER_BLOB,
        (V31_SOURCE, ARLENE_REPO_PATH): ACTIVE_ARLENE_BLOB,
        (V4_SOURCE, ARLENE_REPO_PATH): ACTIVE_ARLENE_BLOB,
    }
    for (revision, path), blob in expected.items():
        actual = git_path_blob(repo_root, revision, path)
        if actual != blob:
            raise ValueError(
                f"source identity mismatch for {revision}:{path}: {actual} != {blob}"
            )
    return {
        "e14_commit": E14_COMMIT,
        "immediate_parent": PRE_E14_COMMIT,
        "parent_count": 1,
        "submitted_v4_source": V4_SOURCE,
        "e14_ancestor_of_submitted_v4": True,
    }


def _safe_member_name(raw_name: str) -> str:
    if not raw_name or "\\" in raw_name:
        raise ValueError(f"unsafe archive member name: {raw_name!r}")
    path = PurePosixPath(raw_name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe archive member path: {raw_name!r}")
    normalized = str(path)
    if normalized in ("", "."):
        raise ValueError(f"empty archive member path: {raw_name!r}")
    return normalized


def read_authenticated_archive(
    archive_bytes: bytes,
    *,
    expected_sha256: str = V4_ARCHIVE_SHA256,
) -> dict[str, ArchiveFile]:
    actual = sha256_bytes(archive_bytes)
    if actual != expected_sha256:
        raise ValueError(f"V4 archive SHA256 mismatch: {actual} != {expected_sha256}")

    files: dict[str, ArchiveFile] = {}
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:*") as archive:
        for member in archive.getmembers():
            name = _safe_member_name(member.name)
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError(
                    f"archive member must be a regular file, got {member.type!r}: {name}"
                )
            if name in files:
                raise ValueError(f"duplicate archive member: {name}")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"unable to read archive member: {name}")
            files[name] = ArchiveFile(stream.read(), member.mode & 0o777)
    if not files:
        raise ValueError("authenticated archive contained no regular files")
    return files


def _find_unique_blob(files: Mapping[str, ArchiveFile], blob: str) -> str:
    matches = [name for name, item in files.items() if git_blob_sha1(item.data) == blob]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one archive member with blob {blob}, got {matches}")
    return matches[0]


def build_treatment_files(
    control_files: Mapping[str, ArchiveFile],
    donor_scheduler: bytes,
    *,
    control_scheduler_blob: str = CONTROL_SCHEDULER_BLOB,
    treatment_scheduler_blob: str = TREATMENT_SCHEDULER_BLOB,
    arlene_blob: str = ACTIVE_ARLENE_BLOB,
) -> tuple[dict[str, ArchiveFile], str, str]:
    if git_blob_sha1(donor_scheduler) != treatment_scheduler_blob:
        raise ValueError("treatment scheduler bytes do not match authenticated donor blob")

    scheduler_member = _find_unique_blob(control_files, control_scheduler_blob)
    arlene_member = _find_unique_blob(control_files, arlene_blob)
    if PurePosixPath(scheduler_member).name != "scheduler.py":
        raise ValueError(f"control scheduler blob is at unexpected member {scheduler_member!r}")
    if PurePosixPath(arlene_member).name != "arlene.py":
        raise ValueError(f"Arlene producer blob is at unexpected member {arlene_member!r}")

    treatment = dict(control_files)
    treatment[scheduler_member] = ArchiveFile(
        donor_scheduler,
        control_files[scheduler_member].mode,
    )

    changed = [
        name
        for name in sorted(control_files)
        if treatment[name].data != control_files[name].data
        or treatment[name].mode != control_files[name].mode
    ]
    if changed != [scheduler_member]:
        raise ValueError(f"causal treatment must change only scheduler.py, got {changed}")
    if git_blob_sha1(treatment[arlene_member].data) != arlene_blob:
        raise ValueError("treatment changed the held-constant Arlene producer")
    return treatment, scheduler_member, arlene_member


def tree_sha256(files: Mapping[str, ArchiveFile]) -> str:
    digest = hashlib.sha256()
    for name in sorted(files):
        item = files[name]
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(f"{item.mode:03o}".encode("ascii"))
        digest.update(b"\0")
        digest.update(sha256_bytes(item.data).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _write_tree(output: Path, files: Mapping[str, ArchiveFile], receipt: dict) -> None:
    if RECEIPT_NAME in files:
        raise ValueError(f"archive member collides with receipt path: {RECEIPT_NAME}")
    if output.exists():
        raise FileExistsError(f"refusing to replace existing output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp.", dir=output.parent))
    try:
        for name, item in sorted(files.items()):
            target = temp.joinpath(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(item.data)
            os.chmod(target, item.mode or 0o644)
        (temp / RECEIPT_NAME).write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        temp.rename(output)
    except BaseException:
        shutil.rmtree(temp, ignore_errors=True)
        raise


def materialize_exact_v4_e14_off(archive: Path, output: Path, repo_root: Path) -> dict:
    # Single caller-path read is the sole archive authority.
    archive_bytes = archive.read_bytes()
    control_files = read_authenticated_archive(archive_bytes)

    # Authenticate every historical Git identity and capture donor bytes before
    # creating any treatment output directory.
    lineage = validate_git_ancestry(repo_root)
    donor_scheduler = git_read_blob(repo_root, TREATMENT_SCHEDULER_BLOB)
    treatment, scheduler_member, arlene_member = build_treatment_files(
        control_files, donor_scheduler
    )

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "causal_question": "submitted V4 with E14 scheduler timing vs immediate pre-E14 scheduler",
        "mechanical_caveat": (
            "E14 fixes real unit-stage-before-market shed timing; a positive rollback result "
            "is diagnostic and does not authorize restoring incorrect overflow physics"
        ),
        "lineage": lineage,
        "control": {
            "source_commit": V4_SOURCE,
            "archive_sha256": V4_ARCHIVE_SHA256,
            "scheduler_git_blob": CONTROL_SCHEDULER_BLOB,
            "member_tree_sha256": tree_sha256(control_files),
        },
        "treatment": {
            "scheduler_git_blob": TREATMENT_SCHEDULER_BLOB,
            "scheduler_source_commit": PRE_E14_COMMIT,
            "member_tree_sha256": tree_sha256(treatment),
        },
        "e14_commit": E14_COMMIT,
        "held_constant_producer": {
            "git_blob": ACTIVE_ARLENE_BLOB,
            "v31_source_commit": V31_SOURCE,
            "v4_source_commit": V4_SOURCE,
            "archive_member": arlene_member,
        },
        "changed_members": [
            {
                "path": scheduler_member,
                "control_git_blob": CONTROL_SCHEDULER_BLOB,
                "treatment_git_blob": TREATMENT_SCHEDULER_BLOB,
            }
        ],
        "member_count": len(control_files),
    }
    _write_tree(output, treatment, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True, help="exact submitted V4 tar archive")
    parser.add_argument("--output", type=Path, required=True, help="fresh treatment directory")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="full commons checkout")
    args = parser.parse_args()
    receipt = materialize_exact_v4_e14_off(
        args.archive.resolve(), args.output.resolve(), args.repo_root.resolve()
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
