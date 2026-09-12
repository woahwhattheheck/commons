# SPDX-License-Identifier: Apache-2.0
"""Materialize P02 over the exact production-v3 archive."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

HERE = Path(__file__).resolve().parent
SELECTIVE_CARROT = HERE.parent / "selective-carrot"
if str(SELECTIVE_CARROT) not in sys.path:
    sys.path.insert(0, str(SELECTIVE_CARROT))

from build_delivery import archive_bytes, digest, members

BASELINE_SHA = "20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239"
MAIN_SHA256 = "b98aec64f83ea9a216def7ab1fef320a6498ae37816f506af1f891c934027035"
HELPER_GIT_BLOB = "3254eef7578e7acaf33040dbda706a7e01e52105"
MAIN = "main.py"
HELPER = "goose_capacity_economy.py"


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def compose(
    baseline,
    helper,
    *,
    expected_main_sha=MAIN_SHA256,
    expected_helper_blob=HELPER_GIT_BLOB,
):
    """Patch only the exact public production-v3 return seam and add P02."""
    if MAIN not in baseline:
        raise ValueError("production-v3 main.py missing")
    if HELPER in baseline:
        raise ValueError("P02 helper already exists in baseline")
    parent = baseline[MAIN]
    if digest(parent) != expected_main_sha:
        raise ValueError("production-v3 main.py identity drift")
    if _git_blob(helper) != expected_helper_blob:
        raise ValueError("P02 helper identity drift")

    import_anchor = b"import baseline_main as baseline\n"
    return_anchor = b"    return returned\n"
    if parent.count(import_anchor) != 1:
        raise ValueError("expected one production-v3 baseline import seam")
    if parent.count(return_anchor) != 1:
        raise ValueError("expected one production-v3 public return seam")

    patched = parent.replace(
        import_anchor,
        import_anchor + b"import goose_capacity_economy as p02\n",
        1,
    )
    patched = patched.replace(
        return_anchor,
        b"    return p02.apply_goose_capacity_economy(\n"
        b"        returned, observation, configuration, enabled=True\n"
        b"    )\n",
        1,
    )

    files = dict(baseline)
    files[MAIN] = patched
    files[HELPER] = helper
    if files.get("baseline_main.py") != baseline.get("baseline_main.py"):
        raise ValueError("embedded baseline_main.py changed")
    return files, parent, patched


def build(baseline_archive: Path):
    baseline = members(baseline_archive, BASELINE_SHA)
    if digest(archive_bytes(baseline)) != BASELINE_SHA:
        raise ValueError("production-v3 deterministic archive identity drift")
    helper = (HERE / HELPER).read_bytes()
    return compose(baseline, helper)


def _resolved(path):
    return Path(path).resolve(strict=False)


def _validate_publication_paths(tar_path, receipt_path):
    tar_resolved, receipt_resolved = map(_resolved, (tar_path, receipt_path))
    if tar_resolved == receipt_resolved:
        raise ValueError("archive and receipt paths must be distinct")


def _reserve(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o644)
    st = os.fstat(fd)
    return fd, (st.st_dev, st.st_ino)


def _write_reserved(fd, payload):
    view = memoryview(payload)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError("short write while publishing P02 artifact")
        view = view[written:]
    os.fsync(fd)


def _unlink_if_owned(path, identity):
    path = Path(path)
    try:
        st = path.stat(follow_symlinks=False)
    except FileNotFoundError:
        return
    if (st.st_dev, st.st_ino) == identity:
        path.unlink()


def _read_owned(path, identity):
    path = Path(path)
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or (before.st_dev, before.st_ino) != identity:
        raise RuntimeError("published pathname ownership drift")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != identity:
            raise RuntimeError("published file ownership drift")
        chunks = []
        while True:
            chunk = os.read(fd, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
        payload = b"".join(chunks)
    finally:
        os.close(fd)
    after = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(after.st_mode) or (after.st_dev, after.st_ino) != identity:
        raise RuntimeError("published pathname changed during verification")
    return payload


def _fsync_parent(path):
    parent = Path(path).parent
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    fd = os.open(parent, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def publish_pair(tar_path, receipt_path, packed, receipt):
    """Create-exclusive archive+receipt publication with owned rollback."""
    tar_path = Path(tar_path)
    receipt_path = Path(receipt_path)
    _validate_publication_paths(tar_path, receipt_path)
    receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
    tar_fd = receipt_fd = None
    owned = []
    try:
        tar_fd, tar_identity = _reserve(tar_path)
        owned.append((tar_path, tar_identity))
        receipt_fd, receipt_identity = _reserve(receipt_path)
        owned.append((receipt_path, receipt_identity))
        _write_reserved(tar_fd, packed)
        _write_reserved(receipt_fd, receipt_bytes)

        # Keep both reservation descriptors open through pathname verification.
        # This prevents unlink/recreate interposition from reusing an owned
        # inode number before the final names are authenticated.
        if _read_owned(tar_path, tar_identity) != packed:
            raise RuntimeError("published archive payload drift")
        if _read_owned(receipt_path, receipt_identity) != receipt_bytes:
            raise RuntimeError("published receipt payload drift")
        _fsync_parent(tar_path)
        if receipt_path.parent.resolve(strict=False) != tar_path.parent.resolve(strict=False):
            _fsync_parent(receipt_path)

        os.close(tar_fd)
        tar_fd = None
        os.close(receipt_fd)
        receipt_fd = None
        return receipt
    except BaseException:
        for fd in (tar_fd, receipt_fd):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
        for path, identity in reversed(owned):
            _unlink_if_owned(path, identity)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--tar", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        files, before, after = build(args.baseline)
        packed = archive_bytes(files)
        receipt = {
            "schema": "titan-v5-p02-goose-capacity-economy/v2",
            "baseline_candidate_archive_sha256": BASELINE_SHA,
            "candidate_archive_sha256": digest(packed),
            "members": len(files),
            "changed_members": [MAIN],
            "new_members": [HELPER],
            "main_before_sha256": digest(before),
            "main_after_sha256": digest(after),
            "helper_git_blob": _git_blob(files[HELPER]),
            "candidate_treatment_enabled": True,
            "canonical_default_unchanged": True,
            "kaggle_submission_hold": True,
            "files": {name: digest(body) for name, body in sorted(files.items())},
        }
        publish_pair(args.tar, args.receipt, packed, receipt)
    except (FileExistsError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))

    print(json.dumps({
        "candidate_archive_sha256": receipt["candidate_archive_sha256"],
        "members": receipt["members"],
        "changed_members": receipt["changed_members"],
        "new_members": receipt["new_members"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
