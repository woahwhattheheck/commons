#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed release-pointer transaction authority for TITAN V5.

This module is outside gameplay.  It replays the V5 promotion gate, requires a
paired competitive-economics PASS, replays the current V4 trust-root gate,
binds the promoted component bytes into the proposed release SOURCE manifest,
authenticates the proposed archive/pointer pair, and then produces a
deterministic expected-old -> approved-new transaction receipt.

The optional writer changes only CURRENT-ARCHIVE.json.  It uses an exclusive
cooperating-writer lock, re-reads the exact expected-old bytes under that lock,
atomically replaces the pointer, verifies the postimage, and only then publishes
the deterministic transaction receipt.  It never builds or changes an archive,
source manifest, runtime source, config, or gameplay default.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile
import uuid
from typing import Any, Callable, Mapping

SCHEMA = "titan-v5-release-transaction/v2"
TRANSITION_PREFIX = "v5tx:"
_POINTER_KEYS = frozenset(
    ("path", "entrypoint", "config", "sha256", "bytes",
     "runtime_files", "source_manifest", "source_manifest_sha256")
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_V5C = re.compile(r"^v5c:[0-9a-f]{64}$")


class TransactionError(ValueError):
    """Release transaction input or state is unsafe."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise TransactionError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_constant(token: str) -> None:
    raise TransactionError(f"non-finite JSON constant is forbidden: {token}")


def _loads(raw: bytes, label: str) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TransactionError(f"{label} is not UTF-8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise TransactionError(f"{label} invalid JSON: {exc.msg}") from exc


def _read(path: Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise TransactionError(f"cannot read {label}: {path}") from exc


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise TransactionError("value is not canonical-JSON serializable") from exc


def _hex64(value: Any, field: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise TransactionError(f"{field} must be 64 lowercase hex")
    return value


def _plain_int(value: Any, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise TransactionError(f"{field} must be a plain int >= {minimum}")
    return value


def _safe_rel(value: Any, field: str) -> str:
    if type(value) is not str or not value or "\\" in value:
        raise TransactionError(f"{field} must be a canonical relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value or any(
        part in ("", ".", "..") for part in path.parts
    ):
        raise TransactionError(f"{field} must be a canonical relative path")
    return value


def _source_key(value: Any, field: str) -> str:
    """Validate a producer source_path string without treating it as a filesystem target.

    build_integrated intentionally records a few sibling Kaggriculture sources as
    ../cloud-... paths.  They are provenance strings here, not traversal inputs.
    """
    if type(value) is not str or not value or "\\" in value:
        raise TransactionError(f"{field} must be a non-empty POSIX source path")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value or any(
        part in ("", ".") for part in path.parts
    ):
        raise TransactionError(f"{field} must be a canonical POSIX source path")
    return value


def validate_pointer(value: Any, field: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _POINTER_KEYS:
        raise TransactionError(f"{field} must have exact current-archive pointer keys")
    if value["path"] != "exports/titan-current.tar.gz":
        raise TransactionError(f"{field}.path must be exports/titan-current.tar.gz")
    if value["entrypoint"] != "main.py::agent":
        raise TransactionError(f"{field}.entrypoint must be main.py::agent")
    if value["config"] != "TITAN-CONFIG.json":
        raise TransactionError(f"{field}.config must be TITAN-CONFIG.json")
    _hex64(value["sha256"], f"{field}.sha256")
    _plain_int(value["bytes"], f"{field}.bytes", 1)
    _plain_int(value["runtime_files"], f"{field}.runtime_files", 1)
    if value["source_manifest"] != "runtime/integrated-selected/CURRENT-SOURCE.json":
        raise TransactionError(
            f"{field}.source_manifest must be runtime/integrated-selected/CURRENT-SOURCE.json"
        )
    _hex64(value["source_manifest_sha256"], f"{field}.source_manifest_sha256")
    return value


def _archive_members(raw: bytes) -> dict[str, bytes]:
    """Return a strict regular-file map for the approved gzip/tar archive."""
    members: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
            for info in archive:
                name = _safe_rel(info.name, "approved archive member")
                if name in members:
                    raise TransactionError(f"duplicate approved archive member: {name}")
                if not info.isfile():
                    raise TransactionError(
                        f"approved archive contains non-regular member: {name}"
                    )
                stream = archive.extractfile(info)
                if stream is None:
                    raise TransactionError(f"cannot read approved archive member: {name}")
                payload = stream.read()
                if len(payload) != info.size:
                    raise TransactionError(
                        f"approved archive member size changed while reading: {name}"
                    )
                members[name] = payload
    except (tarfile.TarError, OSError) as exc:
        raise TransactionError(f"approved archive is not a valid gzip/tar: {exc}") from exc
    if "SOURCE.json" not in members:
        raise TransactionError("approved archive is missing SOURCE.json")
    return members


def _runtime_index(source_manifest: Any) -> tuple[dict[str, list[dict[str, Any]]], int]:
    if type(source_manifest) is not dict or type(source_manifest.get("runtime")) is not dict:
        raise TransactionError("approved source manifest must contain runtime object")
    runtime = source_manifest["runtime"]
    by_source: dict[str, list[dict[str, Any]]] = {}
    for archive_path, row in runtime.items():
        _safe_rel(archive_path, "approved source runtime key")
        if type(row) is not dict or set(row) != {"source_path", "sha256", "bytes"}:
            raise TransactionError(
                f"approved source runtime[{archive_path!r}] has noncanonical keys"
            )
        source_path = _source_key(
            row["source_path"], f"approved source runtime[{archive_path!r}].source_path"
        )
        sha = _hex64(
            row["sha256"], f"approved source runtime[{archive_path!r}].sha256"
        )
        _plain_int(row["bytes"], f"approved source runtime[{archive_path!r}].bytes", 0)
        by_source.setdefault(source_path, []).append(
            {"archive_path": archive_path, "sha256": sha}
        )
    return by_source, len(runtime)


def bind_promoted_sources(
    candidate_manifest: Any,
    source_manifest: Any,
    archive_members: Mapping[str, bytes],
) -> None:
    if type(candidate_manifest) is not dict or type(candidate_manifest.get("components")) is not list:
        raise TransactionError("candidate manifest must contain components list")
    by_source, _ = _runtime_index(source_manifest)
    for index, component in enumerate(candidate_manifest["components"]):
        if type(component) is not dict:
            raise TransactionError(f"candidate component[{index}] must be an object")
        source = _safe_rel(component.get("source"), f"candidate component[{index}].source")
        wanted = _hex64(
            component.get("source_sha256"),
            f"candidate component[{index}].source_sha256",
        )
        rows = by_source.get(source, [])
        if not rows:
            raise TransactionError(
                f"promoted component source is absent from approved release: {source}"
            )
        for row in rows:
            if row["sha256"] != wanted:
                observed = sorted({item["sha256"] for item in rows})
                raise TransactionError(
                    f"promoted component source hash disagrees with approved release: "
                    f"{source}; observed={observed!r}"
                )
            payload = archive_members.get(row["archive_path"])
            if payload is None:
                raise TransactionError(
                    f"approved archive is missing promoted component member: "
                    f"{row['archive_path']}"
                )
            if _sha(payload) != wanted:
                raise TransactionError(
                    f"approved archive member disagrees with promoted component: "
                    f"{row['archive_path']}"
                )


def _promotion_replay(
    promotion_builder: Callable[..., Mapping[str, Any]],
    candidate_manifest_raw: bytes,
    engagement_raw: bytes,
    runtime_raw: bytes,
    promotion_receipt_raw: bytes,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = _loads(candidate_manifest_raw, "candidate manifest")
    engagement = _loads(engagement_raw, "engagement report")
    runtime = _loads(runtime_raw, "runtime report")
    supplied = _loads(promotion_receipt_raw, "promotion receipt")
    if type(supplied) is not dict:
        raise TransactionError("promotion receipt must be an object")
    try:
        replayed = promotion_builder(
            manifest,
            engagement,
            runtime,
            evidence_sha256={
                "candidate_manifest": _sha(candidate_manifest_raw),
                "engagement_report": _sha(engagement_raw),
                "runtime_report": _sha(runtime_raw),
            },
        )
    except Exception as exc:
        raise TransactionError(f"promotion gate replay failed: {exc}") from exc
    if replayed != supplied:
        raise TransactionError("supplied promotion receipt disagrees with gate replay")
    candidate_id = supplied.get("candidate_id")
    control_id = supplied.get("control_id")
    if type(candidate_id) is not str or _V5C.fullmatch(candidate_id) is None:
        raise TransactionError("promotion receipt candidate_id is noncanonical")
    if type(control_id) is not str or _V5C.fullmatch(control_id) is None:
        raise TransactionError("promotion receipt control_id is noncanonical")
    if candidate_id == control_id:
        raise TransactionError("promotion receipt candidate_id and control_id must differ")
    if supplied.get("classification") != "PASS" or supplied.get("promotion_ready") is not True:
        raise TransactionError("promotion receipt is not a promotion-ready PASS")
    return manifest, supplied


def _economics_replay(
    economics_builder: Callable[..., Mapping[str, Any]],
    economics_raw: bytes,
    *,
    candidate_id: str,
    control_id: str,
) -> dict[str, Any]:
    report = _loads(economics_raw, "economics report")
    if type(report) is not dict:
        raise TransactionError("economics report must be an object")
    try:
        receipt = economics_builder(
            report,
            candidate_id=candidate_id,
            control_id=control_id,
        )
    except Exception as exc:
        raise TransactionError(f"economics gate replay failed: {exc}") from exc
    if type(receipt) is not dict:
        raise TransactionError("economics gate did not return an object")
    if receipt.get("classification") != "PASS" or receipt.get("promotion_ready") is not True:
        raise TransactionError("economics gate is not a promotion-ready PASS")
    if receipt.get("candidate_id") != candidate_id or receipt.get("control_id") != control_id:
        raise TransactionError("economics receipt identity disagrees with promotion receipt")
    return receipt


def _trust_digest(files: Mapping[str, bytes]) -> str:
    if set(files) != {
        "CANONICAL.json",
        "INTEGRATION.json",
        "COMPOSITION.json",
        "check_control_plane.py",
    }:
        raise TransactionError("trusted-base files are incomplete")
    rows = {name: _sha(raw) for name, raw in sorted(files.items())}
    return _sha(_canonical(rows))


def build_transaction(
    *,
    live_pointer_raw: bytes,
    expected_old_pointer_raw: bytes,
    approved_new_pointer_raw: bytes,
    approved_archive_raw: bytes,
    approved_source_manifest_raw: bytes,
    candidate_manifest_raw: bytes,
    engagement_raw: bytes,
    runtime_raw: bytes,
    promotion_receipt_raw: bytes,
    economics_raw: bytes,
    promotion_builder: Callable[..., Mapping[str, Any]],
    economics_builder: Callable[..., Mapping[str, Any]],
    trust_result: Mapping[str, Any],
    trust_files: Mapping[str, bytes],
) -> dict[str, Any]:
    """Authenticate one expected-old -> approved-new transition without writing."""
    if live_pointer_raw != expected_old_pointer_raw:
        raise TransactionError("live release pointer is stale versus expected-old bytes")

    old_pointer = validate_pointer(_loads(expected_old_pointer_raw, "expected-old pointer"), "expected-old pointer")
    new_pointer = validate_pointer(_loads(approved_new_pointer_raw, "approved-new pointer"), "approved-new pointer")
    if _sha(expected_old_pointer_raw) == _sha(approved_new_pointer_raw):
        raise TransactionError("approved-new pointer must differ from expected-old pointer")

    if len(approved_archive_raw) != new_pointer["bytes"]:
        raise TransactionError("approved archive byte count disagrees with approved-new pointer")
    if _sha(approved_archive_raw) != new_pointer["sha256"]:
        raise TransactionError("approved archive hash disagrees with approved-new pointer")
    if _sha(approved_source_manifest_raw) != new_pointer["source_manifest_sha256"]:
        raise TransactionError("approved source hash disagrees with approved-new pointer")

    source_manifest = _loads(approved_source_manifest_raw, "approved source manifest")
    _, runtime_count = _runtime_index(source_manifest)
    if runtime_count != new_pointer["runtime_files"]:
        raise TransactionError("approved source runtime count disagrees with approved-new pointer")
    archive_members = _archive_members(approved_archive_raw)
    if archive_members["SOURCE.json"] != approved_source_manifest_raw:
        raise TransactionError(
            "approved archive SOURCE.json differs from approved source manifest bytes"
        )

    manifest, promotion = _promotion_replay(
        promotion_builder,
        candidate_manifest_raw,
        engagement_raw,
        runtime_raw,
        promotion_receipt_raw,
    )
    economics = _economics_replay(
        economics_builder,
        economics_raw,
        candidate_id=promotion["candidate_id"],
        control_id=promotion["control_id"],
    )
    bind_promoted_sources(manifest, source_manifest, archive_members)

    if type(trust_result) is not dict or trust_result.get("ok") is not True:
        raise TransactionError("current V4 trusted-base gate did not PASS")
    if trust_result.get("errors") != []:
        raise TransactionError("current V4 trusted-base gate returned errors")

    trust_sha = _trust_digest(trust_files)
    core = {
        "expected_old": {
            "pointer_sha256": _sha(expected_old_pointer_raw),
            "archive_sha256": old_pointer["sha256"],
            "source_manifest_sha256": old_pointer["source_manifest_sha256"],
        },
        "approved_new": {
            "pointer_sha256": _sha(approved_new_pointer_raw),
            "archive_sha256": new_pointer["sha256"],
            "source_manifest_sha256": new_pointer["source_manifest_sha256"],
            "runtime_files": new_pointer["runtime_files"],
        },
        "promotion": {
            "receipt_sha256": _sha(promotion_receipt_raw),
            "candidate_id": promotion["candidate_id"],
            "control_id": promotion["control_id"],
            "evidence_sha256": promotion.get("evidence_sha256"),
        },
        "economics": {
            "report_sha256": _sha(economics_raw),
            "cell_count": economics["cell_count"],
            "seed_count": economics["seed_count"],
            "sum_margin_delta": economics["sum_margin_delta"],
            "mean_margin_delta": economics["mean_margin_delta"],
            "panel_sha256": economics["panel_sha256"],
        },
        "trusted_base": {
            "control_plane_sha256": trust_sha,
            "validator_sha256": _sha(trust_files["check_control_plane.py"]),
        },
    }
    transition_id = TRANSITION_PREFIX + _sha(_canonical(core))
    return {
        "schema": SCHEMA,
        "classification": "PASS",
        "transition_id": transition_id,
        **core,
    }


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            remaining = memoryview(raw)
            while remaining:
                written = handle.write(remaining)
                if written is None or written <= 0:
                    raise OSError("transaction write made no progress")
                remaining = remaining[written:]
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def commit_pointer(
    *,
    current_pointer: Path,
    expected_old_pointer_raw: bytes,
    approved_new_pointer_raw: bytes,
    receipt_path: Path,
    receipt: Mapping[str, Any],
) -> None:
    """Commit a previously authenticated pointer under a cooperating-writer lock."""
    lock_path = current_pointer.with_name(f".{current_pointer.name}.transaction.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        live = _read(current_pointer, "live current pointer")
        if live != expected_old_pointer_raw:
            raise TransactionError("live release pointer changed before commit")
        _atomic_write(current_pointer, approved_new_pointer_raw)
        if _read(current_pointer, "committed current pointer") != approved_new_pointer_raw:
            raise TransactionError("release pointer postimage verification failed")
        receipt_raw = _canonical(dict(receipt)) + b"\n"
        _atomic_write(receipt_path, receipt_raw)
        if _read(receipt_path, "transaction receipt") != receipt_raw:
            raise TransactionError("transaction receipt postimage verification failed")


def _load_module(path: Path, name: str):
    source = _read(path, name)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise TransactionError(f"cannot load module {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, source


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve()
    lab = here.parents[3]
    default_pointer = lab / "runtime/integrated-selected/CURRENT-ARCHIVE.json"
    default_v4 = here.parents[2] / "v4"

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-pointer", type=Path, default=default_pointer)
    parser.add_argument("--expected-old-pointer", type=Path, required=True)
    parser.add_argument("--approved-new-pointer", type=Path, required=True)
    parser.add_argument("--approved-archive", type=Path, required=True)
    parser.add_argument("--approved-source-manifest", type=Path, required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--engagement-report", type=Path, required=True)
    parser.add_argument("--runtime-report", type=Path, required=True)
    parser.add_argument("--promotion-receipt", type=Path, required=True)
    parser.add_argument("--economics-report", type=Path, required=True)
    parser.add_argument("--v4-root", type=Path, default=default_v4)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args(argv)

    try:
        promotion_module, _ = _load_module(here.with_name("promotion_gate.py"), "_titan_v5_promotion_gate")
        economics_module, _ = _load_module(here.with_name("economics_gate.py"), "_titan_v5_economics_gate")
        v4_module, validator_raw = _load_module(
            args.v4_root / "check_control_plane.py", "_titan_v4_control_plane"
        )
        trust_result = v4_module.validate_control_plane(args.v4_root)
        trust_files = {
            name: _read(args.v4_root / name, f"trusted-base {name}")
            for name in ("CANONICAL.json", "INTEGRATION.json", "COMPOSITION.json")
        }
        trust_files["check_control_plane.py"] = validator_raw

        expected_old_raw = _read(args.expected_old_pointer, "expected-old pointer")
        approved_new_raw = _read(args.approved_new_pointer, "approved-new pointer")
        receipt = build_transaction(
            live_pointer_raw=_read(args.current_pointer, "live current pointer"),
            expected_old_pointer_raw=expected_old_raw,
            approved_new_pointer_raw=approved_new_raw,
            approved_archive_raw=_read(args.approved_archive, "approved archive"),
            approved_source_manifest_raw=_read(
                args.approved_source_manifest, "approved source manifest"
            ),
            candidate_manifest_raw=_read(args.candidate_manifest, "candidate manifest"),
            engagement_raw=_read(args.engagement_report, "engagement report"),
            runtime_raw=_read(args.runtime_report, "runtime report"),
            promotion_receipt_raw=_read(args.promotion_receipt, "promotion receipt"),
            economics_raw=_read(args.economics_report, "economics report"),
            promotion_builder=promotion_module.build_receipt,
            economics_builder=economics_module.validate_report,
            trust_result=trust_result,
            trust_files=trust_files,
        )
        if args.commit:
            if args.output is None:
                raise TransactionError("--commit requires --output transaction receipt path")
            commit_pointer(
                current_pointer=args.current_pointer,
                expected_old_pointer_raw=expected_old_raw,
                approved_new_pointer_raw=approved_new_raw,
                receipt_path=args.output,
                receipt=receipt,
            )
        elif args.output is not None:
            _atomic_write(args.output, _canonical(receipt) + b"\n")
        else:
            print(_canonical(receipt).decode("utf-8"))
    except (TransactionError, OSError, TypeError, ValueError) as exc:
        print(f"release_transaction: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
