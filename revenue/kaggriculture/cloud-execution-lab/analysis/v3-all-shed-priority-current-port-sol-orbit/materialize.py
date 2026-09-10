# SPDX-License-Identifier: Apache-2.0
"""Materialize one exact current-TITAN all-shed priority factor.

The canonical runtime archive is verified member-by-member, materialized into
separate control and candidate closures, and only ``scheduler.py`` is changed.
The factor preserves every positive-shed target and quantity; it changes only
first-wins traversal priority to pending intent, inherited SELL intent, then
the remaining canonical PRODUCTS order.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tarfile
import tempfile
from typing import Any, Iterable, Mapping

EXPERIMENT = "titan-v3-all-shed-priority-current-port-20260910-01"
OPERATION = "titan-v3-all-shed-priority-current-port-sol-orbit-01"

EXPECTED_ARCHIVE_SHA256 = (
    "5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1"
)
EXPECTED_ARCHIVE_GIT_BLOB = "10e92806e24a32f3f301e32edbb1f0b5106be92a"
EXPECTED_ARCHIVE_BYTES = 428_158
EXPECTED_SOURCE_MANIFEST_SHA256 = (
    "3249398b6aa56d1b3464db8d0cce5aa35e8edee397fc4341bd710d1f74dad469"
)
EXPECTED_RUNTIME_FILES = 109
EXPECTED_ARCHIVE_MEMBERS = EXPECTED_RUNTIME_FILES + 1
EXPECTED_ENTRYPOINT = "main.py::agent"
EXPECTED_ENTRY_SHA256 = (
    "c4c22d0f2b1071cadf6a9f74effccc8cb20ea9f4d10ca1cf9f1fe57351709dc1"
)
EXPECTED_SCHEDULER_GIT_BLOB = "a483b24dd72b580d7d8811636b54d2d44f391575"
MAX_MEMBER_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024

OLD = (
    "        targets={p:max(0,int(shed.get(p,0))) for p in PRODUCTS "
    "if shed.get(p,0)>0}\n"
)
NEW = (
    "        target_order={\n"
    "            **{p:0 for p in self.pending if p in PRODUCTS},\n"
    "            **{p:0 for p in baseline_q},\n"
    "            **{p:0 for p in PRODUCTS},\n"
    "        }\n"
    "        targets={p:max(0,int(shed.get(p,0))) for p in target_order "
    "if shed.get(p,0)>0}\n"
)


class MaterializeError(ValueError):
    """The archive, manifest, output closure, or one-factor patch is invalid."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def inventory(root: Path) -> dict[str, dict[str, Any]]:
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise MaterializeError(f"closure root is not one regular directory: {root}")
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(
        root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
    ):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise MaterializeError(f"non-regular closure member: {relative}")
        data = path.read_bytes()
        result[relative] = {
            "bytes": len(data),
            "sha256": sha256(data),
            "git_blob_sha1": git_blob_sha1(data),
        }
    if not result:
        raise MaterializeError("closure inventory is empty")
    return result


def closure_sha256(items: Mapping[str, Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    for relative, record in sorted(items.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(record["bytes"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(record["sha256"]).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _safe_member_parts(name: str) -> tuple[str, ...]:
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise MaterializeError("archive contains an invalid member name")
    path = PurePosixPath(name)
    parts = path.parts
    if path.is_absolute() or not parts or any(p in ("", ".", "..") for p in parts):
        raise MaterializeError(f"unsafe archive member: {name!r}")
    if PurePosixPath(*parts).as_posix() != name:
        raise MaterializeError(f"noncanonical archive member: {name!r}")
    return tuple(parts)


def _strict_json_bytes(data: bytes, label: str) -> dict[str, Any]:
    def reject_pairs(pairs):
        output = {}
        for key, value in pairs:
            if key in output:
                raise MaterializeError(f"duplicate key {key!r} in {label}")
            output[key] = value
        return output

    try:
        value = json.loads(
            data,
            object_pairs_hook=reject_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                MaterializeError(f"non-finite token {token} in {label}")
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise MaterializeError(f"{label} is not strict JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise MaterializeError(f"{label} must be one object")
    return value


def read_archive(archive: Path) -> tuple[dict[str, bytes], dict[str, Any], dict[str, Any]]:
    archive = Path(archive)
    if not archive.is_file() or archive.is_symlink():
        raise MaterializeError(f"archive is not one regular file: {archive}")
    raw = archive.read_bytes()
    if len(raw) != EXPECTED_ARCHIVE_BYTES:
        raise MaterializeError(
            f"archive byte drift: expected {EXPECTED_ARCHIVE_BYTES}, got {len(raw)}"
        )
    archive_sha = sha256(raw)
    archive_blob = git_blob_sha1(raw)
    if archive_sha != EXPECTED_ARCHIVE_SHA256:
        raise MaterializeError(
            f"archive SHA-256 drift: expected {EXPECTED_ARCHIVE_SHA256}, got {archive_sha}"
        )
    if archive_blob != EXPECTED_ARCHIVE_GIT_BLOB:
        raise MaterializeError(
            f"archive Git blob drift: expected {EXPECTED_ARCHIVE_GIT_BLOB}, got {archive_blob}"
        )

    members: dict[str, bytes] = {}
    total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as bundle:
            for member in bundle:
                if not member.isfile():
                    raise MaterializeError(
                        f"archive member is not a regular file: {member.name!r}"
                    )
                _safe_member_parts(member.name)
                if member.name in members:
                    raise MaterializeError(f"duplicate archive member: {member.name}")
                if (
                    type(member.size) is not int
                    or member.size < 0
                    or member.size > MAX_MEMBER_BYTES
                ):
                    raise MaterializeError(
                        f"archive member size rejected: {member.name!r}"
                    )
                stream = bundle.extractfile(member)
                if stream is None:
                    raise MaterializeError(f"cannot read member: {member.name!r}")
                data = stream.read(member.size + 1)
                if len(data) != member.size:
                    raise MaterializeError(
                        f"archive member length mismatch: {member.name!r}"
                    )
                total += len(data)
                if total > MAX_TOTAL_BYTES:
                    raise MaterializeError("archive exceeds materialization byte ceiling")
                members[member.name] = data
    except tarfile.TarError as exc:
        raise MaterializeError(f"archive is not a valid gzip tar: {exc}") from exc

    if len(members) != EXPECTED_ARCHIVE_MEMBERS:
        raise MaterializeError(
            "archive member count drift: "
            f"expected {EXPECTED_ARCHIVE_MEMBERS}, got {len(members)}"
        )
    manifest_bytes = members.get("SOURCE.json")
    if manifest_bytes is None:
        raise MaterializeError("archive is missing SOURCE.json")
    manifest_sha = sha256(manifest_bytes)
    if manifest_sha != EXPECTED_SOURCE_MANIFEST_SHA256:
        raise MaterializeError(
            "SOURCE.json digest drift: "
            f"expected {EXPECTED_SOURCE_MANIFEST_SHA256}, got {manifest_sha}"
        )
    manifest = _strict_json_bytes(manifest_bytes, "SOURCE.json")
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict) or len(runtime) != EXPECTED_RUNTIME_FILES:
        raise MaterializeError("runtime manifest cardinality drift")
    if manifest.get("entrypoint") != EXPECTED_ENTRYPOINT:
        raise MaterializeError("runtime entrypoint drift")
    if manifest.get("config") != "TITAN-CONFIG.json":
        raise MaterializeError("runtime config drift")
    expected_names = set(runtime) | {"SOURCE.json"}
    if set(members) != expected_names:
        missing = sorted(expected_names - set(members))
        extra = sorted(set(members) - expected_names)
        raise MaterializeError(
            f"archive/manifest mismatch; missing={missing[:5]}, extra={extra[:5]}"
        )
    for name, metadata in runtime.items():
        _safe_member_parts(name)
        if not isinstance(metadata, dict):
            raise MaterializeError(f"invalid runtime metadata for {name}")
        data = members[name]
        if type(metadata.get("bytes")) is not int or metadata["bytes"] != len(data):
            raise MaterializeError(f"runtime byte-count drift for {name}")
        if metadata.get("sha256") != sha256(data):
            raise MaterializeError(f"runtime digest drift for {name}")
        if not isinstance(metadata.get("source_path"), str):
            raise MaterializeError(f"runtime source identity missing for {name}")

    if sha256(members.get("main.py", b"")) != EXPECTED_ENTRY_SHA256:
        raise MaterializeError("canonical main.py identity drift")
    scheduler = members.get("scheduler.py")
    if scheduler is None or git_blob_sha1(scheduler) != EXPECTED_SCHEDULER_GIT_BLOB:
        raise MaterializeError("canonical scheduler.py identity drift")
    return members, manifest, {
        "sha256": archive_sha,
        "git_blob_sha1": archive_blob,
        "bytes": len(raw),
        "source_manifest_sha256": manifest_sha,
        "runtime_files": len(runtime),
        "archive_members": len(members),
        "materialized_bytes": total,
        "entrypoint": manifest["entrypoint"],
        "config": manifest["config"],
    }


def _write_members(root: Path, members: Mapping[str, bytes]) -> None:
    root = Path(root)
    if root.exists():
        raise MaterializeError(f"output already exists: {root}")
    root.mkdir(parents=True)
    try:
        for name, data in sorted(members.items()):
            target = root.joinpath(*_safe_member_parts(name))
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                handle.write(data)
    except BaseException:
        import shutil

        shutil.rmtree(root, ignore_errors=True)
        raise


def control_targets(*, products: Iterable[str], shed: Mapping[str, Any]) -> dict[str, int]:
    return {
        product: max(0, int(shed.get(product, 0)))
        for product in products
        if shed.get(product, 0) > 0
    }


def priority_targets(
    *,
    pending: Mapping[str, Any],
    baseline_q: Mapping[str, Any],
    products: Iterable[str],
    shed: Mapping[str, Any],
) -> dict[str, int]:
    product_order = tuple(products)
    product_set = set(product_order)
    order: dict[str, None] = {}
    for product in pending:
        if product in product_set:
            order.setdefault(product, None)
    for product in baseline_q:
        if product in product_set:
            order.setdefault(product, None)
    for product in product_order:
        order.setdefault(product, None)
    return {
        product: max(0, int(shed.get(product, 0)))
        for product in order
        if shed.get(product, 0) > 0
    }


def materialize(
    archive: Path,
    control_root: Path,
    candidate_root: Path,
) -> dict[str, Any]:
    archive = Path(archive).resolve()
    control_root = Path(control_root).resolve()
    candidate_root = Path(candidate_root).resolve()
    if control_root == candidate_root:
        raise MaterializeError("control and candidate roots must differ")
    if control_root.exists() or candidate_root.exists():
        raise MaterializeError("control and candidate outputs must not exist")

    original_archive = archive.read_bytes()
    members, manifest, archive_receipt = read_archive(archive)
    scheduler = members["scheduler.py"]
    old = OLD.encode("utf-8")
    new = NEW.encode("utf-8")
    if scheduler.count(old) != 1:
        raise MaterializeError(
            f"expected one current target expression, found {scheduler.count(old)}"
        )
    if scheduler.count(new) != 0:
        raise MaterializeError("priority expression already exists in current source")
    patched = scheduler.replace(old, new, 1)
    try:
        compile(patched.decode("utf-8"), "candidate/scheduler.py", "exec")
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise MaterializeError(f"patched scheduler does not compile: {exc}") from exc

    _write_members(control_root, members)
    candidate_members = dict(members)
    candidate_members["scheduler.py"] = patched
    try:
        _write_members(candidate_root, candidate_members)
    except BaseException:
        import shutil

        shutil.rmtree(control_root, ignore_errors=True)
        raise

    control_inventory = inventory(control_root)
    candidate_inventory = inventory(candidate_root)
    if set(control_inventory) != set(candidate_inventory):
        raise MaterializeError("control/candidate inventories differ")
    changed = [
        name
        for name in sorted(control_inventory)
        if control_inventory[name]["sha256"] != candidate_inventory[name]["sha256"]
    ]
    if changed != ["scheduler.py"]:
        raise MaterializeError(f"one-factor boundary violated: changed={changed!r}")
    if archive.read_bytes() != original_archive:
        raise MaterializeError("canonical archive changed during materialization")
    if control_root.joinpath("scheduler.py").read_bytes() != scheduler:
        raise MaterializeError("control scheduler changed during materialization")
    if candidate_root.joinpath("scheduler.py").read_bytes() != patched:
        raise MaterializeError("candidate scheduler is detached from patch")

    diff = "".join(
        difflib.unified_diff(
            scheduler.decode("utf-8").splitlines(keepends=True),
            patched.decode("utf-8").splitlines(keepends=True),
            fromfile="current/scheduler.py",
            tofile="current-all-shed-priority/scheduler.py",
            n=5,
        )
    )
    return {
        "schema_version": 1,
        "operation": OPERATION,
        "experiment": EXPERIMENT,
        "git_source": "canonical exports/titan-current.tar.gz",
        "archive": archive_receipt,
        "source_manifest": {
            "sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
            "entrypoint": manifest["entrypoint"],
            "config": manifest["config"],
            "runtime_files": len(manifest["runtime"]),
        },
        "factor": {
            "target_domain": "all positive non-operating PRODUCTS in the post-unit shed",
            "target_quantity": "full post-unit shed quantity for every target",
            "control_priority": "PRODUCTS order",
            "candidate_priority": [
                "existing pending scheduler intent",
                "inherited baseline SELL first-seen order",
                "remaining PRODUCTS order",
            ],
            "selection_effect": (
                "first-wins priority under the unchanged strict-greater optimizer rank"
            ),
        },
        "source": {
            "entry": "main.py",
            "entry_sha256": EXPECTED_ENTRY_SHA256,
            "scheduler_git_blob_sha1": git_blob_sha1(scheduler),
            "scheduler_sha256": sha256(scheduler),
            "closure_sha256": closure_sha256(control_inventory),
            "files": len(control_inventory),
        },
        "ablation": {
            "changed_files": changed,
            "entry": "main.py",
            "entry_sha256": sha256(candidate_root.joinpath("main.py").read_bytes()),
            "scheduler_git_blob_sha1": git_blob_sha1(patched),
            "scheduler_sha256": sha256(patched),
            "closure_sha256": closure_sha256(candidate_inventory),
            "old_occurrences_before": scheduler.count(old),
            "old_occurrences_after": patched.count(old),
            "new_occurrences_before": scheduler.count(new),
            "new_occurrences_after": patched.count(new),
            "unified_diff": diff,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = materialize(args.archive, args.control, args.candidate)
    atomic_write(
        args.receipt,
        (
            json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n"
        ).encode("utf-8"),
    )
    print(
        json.dumps(
            {
                "experiment": receipt["experiment"],
                "archive_sha256": receipt["archive"]["sha256"],
                "source_scheduler": receipt["source"]["scheduler_git_blob_sha1"],
                "candidate_scheduler": receipt["ablation"]["scheduler_git_blob_sha1"],
                "source_closure": receipt["source"]["closure_sha256"],
                "candidate_closure": receipt["ablation"]["closure_sha256"],
                "changed_files": receipt["ablation"]["changed_files"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
