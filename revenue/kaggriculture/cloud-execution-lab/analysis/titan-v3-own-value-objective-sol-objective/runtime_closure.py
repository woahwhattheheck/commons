# SPDX-License-Identifier: Apache-2.0
"""Materialize TITAN's exact current archive/source-map closure for experiments.

This helper is intentionally evidence-only. It does not rebuild or publish the
canonical archive. Instead it validates the current ``build_integrated`` source
map, renders the exact in-memory archive, extracts only the expected regular
members into a new isolated directory, and emits a receipt that binds every
source and every materialized member.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import shutil
import tarfile
import uuid
from typing import Any, Mapping

OPERATION = "titan-v3-own-value-runtime-closure-20260909-sol-closure-01"
CASE = Path(__file__).resolve().parent
DEFAULT_LAB = CASE.parent.parent
BUILD_FILE = "build_integrated.py"


class RuntimeClosureError(RuntimeError):
    """The canonical source map or materialized runtime is unsafe or detached."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _member_name(name: Any) -> str:
    if not isinstance(name, str) or not name:
        raise RuntimeClosureError("archive member must be a nonempty string")
    if name.startswith("/") or "\\" in name:
        raise RuntimeClosureError(f"unsafe archive member path: {name!r}")
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise RuntimeClosureError(f"unsafe archive member path: {name!r}")
    if PurePosixPath(name).is_absolute():
        raise RuntimeClosureError(f"absolute archive member path: {name!r}")
    return name


def _source_path(lab: Path, source: Any, boundary: Path) -> Path:
    if not isinstance(source, str) or not source:
        raise RuntimeClosureError("declared source path must be a nonempty string")
    if Path(source).is_absolute():
        raise RuntimeClosureError(f"absolute declared source path: {source!r}")

    # Normalize lexically first so symlink checks still see real path components.
    raw = Path(os.path.normpath(str(lab / source)))
    try:
        relative = raw.relative_to(boundary)
    except ValueError as exc:
        raise RuntimeClosureError(
            f"declared source escapes Kaggriculture boundary: {source!r}"
        ) from exc

    current = boundary
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise RuntimeClosureError(
                f"declared source traverses symlink component: {source!r}"
            )
    if not raw.is_file():
        raise RuntimeClosureError(f"declared source is not one regular file: {source!r}")
    return raw


def _load_builder(lab: Path) -> tuple[Any, Path, bytes]:
    lab = Path(lab).resolve(strict=True)
    build_path = lab / BUILD_FILE
    if build_path.is_symlink() or not build_path.is_file():
        raise RuntimeClosureError(f"{BUILD_FILE} is not one regular file")
    build_bytes = build_path.read_bytes()
    spec = importlib.util.spec_from_file_location(
        f"_titan_runtime_closure_builder_{uuid.uuid4().hex}", build_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeClosureError(f"cannot load {BUILD_FILE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module_root = Path(getattr(module, "ROOT", "")).resolve()
    if module_root != lab:
        raise RuntimeClosureError(
            f"builder ROOT mismatch: expected {lab}, got {module_root}"
        )
    if not callable(getattr(module, "source_files", None)) or not callable(
        getattr(module, "render", None)
    ):
        raise RuntimeClosureError("builder is missing source_files() or render()")
    return module, build_path, build_bytes


def _source_rows(
    lab: Path,
    mapping: Mapping[str, str],
) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    boundary = lab.parent.resolve(strict=True)
    if not isinstance(mapping, Mapping) or not mapping:
        raise RuntimeClosureError("source_files() returned an empty/non-mapping value")
    rows: list[dict[str, Any]] = []
    payloads: dict[str, bytes] = {}
    for member_raw, source in sorted(mapping.items()):
        member = _member_name(member_raw)
        if member in payloads:
            raise RuntimeClosureError(f"duplicate archive member: {member}")
        source_path = _source_path(lab, source, boundary)
        data = source_path.read_bytes()
        source_rel = source_path.relative_to(boundary).as_posix()
        rows.append(
            {
                "member": member,
                "declared_source": source,
                "source_relpath": source_rel,
                "git_blob_sha1": git_blob_sha1(data),
                "sha256": sha256(data),
                "bytes": len(data),
            }
        )
        payloads[member] = data
    for required in ("main.py", "TITAN-CONFIG.json", "observed_clone.py"):
        if required not in payloads:
            raise RuntimeClosureError(f"source map is missing required member {required}")
    return rows, payloads


def _closure_digest(payloads: Mapping[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name in sorted(payloads):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(payloads[name]).digest())
    return digest.hexdigest()


def _safe_extract_exact(
    archive_bytes: bytes,
    expected: Mapping[str, bytes],
    output: Path,
) -> None:
    if output.exists():
        raise RuntimeClosureError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = output.with_name(f".{output.name}.{uuid.uuid4().hex}.tmp")
    stage.mkdir(mode=0o700)
    try:
        seen: set[str] = set()
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
            for info in archive.getmembers():
                name = _member_name(info.name)
                if name in seen:
                    raise RuntimeClosureError(f"duplicate archive member in render: {name}")
                seen.add(name)
                if not info.isfile():
                    raise RuntimeClosureError(
                        f"archive contains non-regular member {name}: type={info.type!r}"
                    )
                if name not in expected:
                    raise RuntimeClosureError(f"unexpected rendered archive member: {name}")
                stream = archive.extractfile(info)
                if stream is None:
                    raise RuntimeClosureError(f"cannot read rendered archive member: {name}")
                data = stream.read()
                if data != expected[name]:
                    raise RuntimeClosureError(f"rendered member bytes detached from source: {name}")
                destination = stage.joinpath(*name.split("/"))
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as handle:
                    handle.write(data)
                os.chmod(destination, 0o644)
        if seen != set(expected):
            missing = sorted(set(expected) - seen)
            extra = sorted(seen - set(expected))
            raise RuntimeClosureError(
                f"rendered member set mismatch: missing={missing!r} extra={extra!r}"
            )
        os.replace(stage, output)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def materialize_runtime_closure(lab: Path, output: Path) -> dict[str, Any]:
    """Materialize one exact executable closure without mutating canonical files."""
    lab = Path(lab).resolve(strict=True)
    output = Path(output).absolute()
    if output.exists():
        raise RuntimeClosureError(f"output already exists: {output}")

    builder, build_path, build_bytes = _load_builder(lab)
    mapping = builder.source_files()
    rows, source_payloads = _source_rows(lab, mapping)

    try:
        archive_bytes, source_manifest, archive_receipt = builder.render()
    except Exception as exc:
        raise RuntimeClosureError(f"canonical builder render failed: {exc}") from exc
    if not isinstance(archive_bytes, bytes) or not isinstance(source_manifest, bytes):
        raise RuntimeClosureError("builder render did not return byte payloads")
    if not isinstance(archive_receipt, Mapping):
        raise RuntimeClosureError("builder render receipt is not an object")
    if archive_receipt.get("entrypoint") != "main.py::agent":
        raise RuntimeClosureError("rendered entrypoint mismatch")
    if archive_receipt.get("config") != "TITAN-CONFIG.json":
        raise RuntimeClosureError("rendered config mismatch")
    if archive_receipt.get("runtime_files") != len(source_payloads):
        raise RuntimeClosureError("rendered runtime file count mismatch")
    if archive_receipt.get("sha256") != sha256(archive_bytes):
        raise RuntimeClosureError("rendered archive SHA-256 receipt is detached")
    if archive_receipt.get("bytes") != len(archive_bytes):
        raise RuntimeClosureError("rendered archive byte-count receipt is detached")
    if archive_receipt.get("source_manifest_sha256") != sha256(source_manifest):
        raise RuntimeClosureError("rendered SOURCE manifest receipt is detached")

    expected = dict(source_payloads)
    if "SOURCE.json" in expected:
        raise RuntimeClosureError("source map must not predeclare SOURCE.json")
    expected["SOURCE.json"] = source_manifest
    _safe_extract_exact(archive_bytes, expected, output)

    # Re-read every materialized member after the atomic directory rename.
    materialized: dict[str, bytes] = {}
    for name, wanted in sorted(expected.items()):
        path = output.joinpath(*name.split("/"))
        if path.is_symlink() or not path.is_file():
            raise RuntimeClosureError(f"materialized member is not one regular file: {name}")
        actual = path.read_bytes()
        if actual != wanted:
            raise RuntimeClosureError(f"post-materialization byte mismatch: {name}")
        materialized[name] = actual

    external_root_members = sorted(
        row["member"]
        for row in rows
        if str(row["declared_source"]).startswith("../")
        and "/" not in str(row["member"])
    )
    return {
        "schema": "titan-runtime-closure/v1",
        "operation": OPERATION,
        "canonical_mutation": False,
        "entrypoint": "main.py::agent",
        "config": "TITAN-CONFIG.json",
        "builder": {
            "relpath": build_path.relative_to(lab.parent).as_posix(),
            "git_blob_sha1": git_blob_sha1(build_bytes),
            "sha256": sha256(build_bytes),
            "bytes": len(build_bytes),
        },
        "archive": {
            "sha256": sha256(archive_bytes),
            "bytes": len(archive_bytes),
            "runtime_files": len(source_payloads),
            "source_manifest_sha256": sha256(source_manifest),
        },
        "closure": {
            "members": len(materialized),
            "sha256": _closure_digest(materialized),
            "external_root_members": external_root_members,
        },
        "source_files": rows,
    }


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab", type=Path, default=DEFAULT_LAB)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = materialize_runtime_closure(args.lab, args.output)
    _atomic_json(args.receipt, receipt)
    print(
        json.dumps(
            {
                "archive_sha256": receipt["archive"]["sha256"],
                "closure_sha256": receipt["closure"]["sha256"],
                "members": receipt["closure"]["members"],
                "external_root_members": receipt["closure"]["external_root_members"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
