#!/usr/bin/env python3
"""Fail-closed verifier/materializer for the historical calibration carrier.

This validates the delivery manifest against the actual repository packet
parts, decodes exactly that packet, verifies gzip bytes + stable git patch-id,
and publishes the decoded patch to a new non-aliased path with O_EXCL.

It does not apply the patch or mutate a repository. Application/testing belongs
in an isolated worktree in the exact-head workflow.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
from pathlib import PurePosixPath
import stat
import subprocess
import sys
from typing import Any, Mapping, Sequence

SCHEMA = "titan-v3-historical-rank-inversion-calibration-delivery/v1"
OPERATION = "TITAN-V3-HISTORICAL-RANK-INVERSION-CALIBRATION-20260910-01"
EXPECTED_PART_COUNT = 4
EXPECTED_FILES_ADDED = 14
SHA256_HEX = 64
GIT_SHA_HEX = 40


class TransportError(ValueError):
    """Carrier bytes, manifest, or destination are unsafe or inconsistent."""


def _reject_constant(token: str) -> Any:
    raise TransportError(f"non-finite JSON constant forbidden: {token}")


def _finite_float(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise TransportError(f"non-finite JSON number forbidden: {token}")
    return value


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise TransportError(f"duplicate JSON key: {key!r}")
        out[key] = value
    return out


def strict_loads(text: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=_reject_constant,
            parse_float=_finite_float,
        )
    except json.JSONDecodeError as exc:
        raise TransportError(f"invalid JSON: {exc}") from exc


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TransportError(f"{field}: expected object")
    return value


def _require_int(value: Any, field: str, *, minimum: int = 0) -> int:
    if type(value) is not int:
        raise TransportError(f"{field}: expected integer")
    if value < minimum:
        raise TransportError(f"{field}: must be >= {minimum}")
    return value


def _require_lower_hex(value: Any, field: str, length: int) -> str:
    if not isinstance(value, str) or len(value) != length or value.lower() != value:
        raise TransportError(f"{field}: expected {length}-char lowercase hex")
    try:
        int(value, 16)
    except ValueError as exc:
        raise TransportError(f"{field}: invalid hex") from exc
    return value


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _real(path: Path) -> Path:
    return Path(os.path.realpath(os.fspath(path)))


def _require_real_directory(path: Path, label: str) -> Path:
    absolute = _absolute(path)
    if _real(path) != absolute:
        raise TransportError(f"{label}: symlinked path component forbidden")
    try:
        info = absolute.lstat()
    except OSError as exc:
        raise TransportError(f"{label}: cannot stat directory: {exc}") from exc
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise TransportError(f"{label}: expected real directory")
    return absolute


def _read_regular_file(path: Path, label: str) -> bytes:
    absolute = _absolute(path)
    if _real(path) != absolute:
        raise TransportError(f"{label}: symlinked path forbidden")
    try:
        info = absolute.lstat()
    except OSError as exc:
        raise TransportError(f"{label}: cannot stat file: {exc}") from exc
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise TransportError(f"{label}: expected regular non-symlink file")
    try:
        return absolute.read_bytes()
    except OSError as exc:
        raise TransportError(f"{label}: cannot read file: {exc}") from exc


def _load_manifest(delivery_dir: Path) -> tuple[Mapping[str, Any], bytes]:
    manifest_path = delivery_dir / "MANIFEST.json"
    raw = _read_regular_file(manifest_path, "manifest")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TransportError("manifest: expected UTF-8") from exc
    data = strict_loads(text)
    manifest = _require_mapping(data, "manifest")
    if manifest.get("schema") != SCHEMA:
        raise TransportError("manifest.schema mismatch")
    if manifest.get("operation") != OPERATION:
        raise TransportError("manifest.operation mismatch")
    _require_lower_hex(manifest.get("base_commit"), "manifest.base_commit", GIT_SHA_HEX)
    return manifest, raw


def _stable_patch_id(patch: bytes) -> str:
    try:
        proc = subprocess.run(
            ["git", "patch-id", "--stable"],
            input=patch,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise TransportError(f"git patch-id unavailable: {exc}") from exc
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()
        raise TransportError(f"git patch-id failed: {detail or proc.returncode}")
    lines = [line for line in proc.stdout.decode("ascii", errors="strict").splitlines() if line]
    if len(lines) != 1:
        raise TransportError("decoded packet must contain exactly one patch-id record")
    fields = lines[0].split()
    if len(fields) != 2:
        raise TransportError("malformed git patch-id output")
    return _require_lower_hex(fields[0], "actual stable patch-id", GIT_SHA_HEX)


def verify_delivery(delivery_dir: Path) -> tuple[bytes, dict[str, Any]]:
    delivery = _require_real_directory(delivery_dir, "delivery_dir")
    manifest, manifest_raw = _load_manifest(delivery)
    transport = _require_mapping(manifest.get("transport"), "manifest.transport")
    if transport.get("encoding") != "base64":
        raise TransportError("manifest.transport.encoding must be base64")
    if transport.get("parts_are_newline_terminated") is not True:
        raise TransportError("manifest must require newline-terminated parts")

    parts = transport.get("parts")
    if not isinstance(parts, list) or len(parts) != EXPECTED_PART_COUNT:
        raise TransportError(f"manifest.transport.parts: expected {EXPECTED_PART_COUNT} entries")

    payloads: list[bytes] = []
    part_receipts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, value in enumerate(parts):
        part = _require_mapping(value, f"parts[{index}]")
        expected_name = f"packet.b64.part-{index:02d}"
        name = part.get("path")
        if not isinstance(name, str):
            raise TransportError(f"parts[{index}].path: expected string")
        if name != expected_name or PurePosixPath(name).name != name or name in seen:
            raise TransportError(f"parts[{index}].path: unsafe or non-canonical part name")
        seen.add(name)
        path = delivery / name
        raw = _read_regular_file(path, f"parts[{index}]")
        repository_bytes = _require_int(
            part.get("repository_blob_bytes"), f"parts[{index}].repository_blob_bytes", minimum=1
        )
        if len(raw) != repository_bytes:
            raise TransportError(f"parts[{index}]: repository byte count mismatch")
        expected_repo_sha = _require_lower_hex(
            part.get("repository_blob_sha256"),
            f"parts[{index}].repository_blob_sha256",
            SHA256_HEX,
        )
        if _sha256(raw) != expected_repo_sha:
            raise TransportError(f"parts[{index}]: repository SHA-256 mismatch")
        if not raw.endswith(b"\n") or b"\n" in raw[:-1] or b"\r" in raw:
            raise TransportError(f"parts[{index}]: expected exactly one terminal LF")
        payload = raw[:-1]
        expected_payload_bytes = _require_int(
            part.get("payload_bytes"), f"parts[{index}].payload_bytes", minimum=1
        )
        if len(payload) != expected_payload_bytes:
            raise TransportError(f"parts[{index}]: payload byte count mismatch")
        try:
            payload.decode("ascii")
        except UnicodeDecodeError as exc:
            raise TransportError(f"parts[{index}]: base64 payload must be ASCII") from exc
        payloads.append(payload)
        part_receipts.append(
            {"path": name, "bytes": len(raw), "sha256": expected_repo_sha}
        )

    encoded = b"".join(payloads)
    try:
        compressed = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise TransportError(f"packet base64 decode failed: {exc}") from exc

    expected_gzip_bytes = _require_int(
        transport.get("decoded_gzip_bytes"),
        "manifest.transport.decoded_gzip_bytes",
        minimum=1,
    )
    if len(compressed) != expected_gzip_bytes:
        raise TransportError("decoded gzip byte count mismatch")
    expected_gzip_sha = _require_lower_hex(
        transport.get("decoded_gzip_sha256"),
        "manifest.transport.decoded_gzip_sha256",
        SHA256_HEX,
    )
    if _sha256(compressed) != expected_gzip_sha:
        raise TransportError("decoded gzip SHA-256 mismatch")
    try:
        patch = gzip.decompress(compressed)
    except (OSError, EOFError) as exc:
        raise TransportError(f"gzip decompression failed: {exc}") from exc

    expected_patch_bytes = _require_int(
        transport.get("decoded_patch_bytes"),
        "manifest.transport.decoded_patch_bytes",
        minimum=1,
    )
    if len(patch) != expected_patch_bytes:
        raise TransportError("decoded patch byte count mismatch")
    expected_patch_id = _require_lower_hex(
        transport.get("stable_patch_id"),
        "manifest.transport.stable_patch_id",
        GIT_SHA_HEX,
    )
    actual_patch_id = _stable_patch_id(patch)
    if actual_patch_id != expected_patch_id:
        raise TransportError("decoded stable patch-id mismatch")

    change = _require_mapping(manifest.get("change"), "manifest.change")
    if _require_int(change.get("files_added"), "manifest.change.files_added", minimum=0) != EXPECTED_FILES_ADDED:
        raise TransportError(f"manifest.change.files_added must remain {EXPECTED_FILES_ADDED}")
    if change.get("runtime_policy_changed") is not False:
        raise TransportError("manifest unexpectedly claims runtime policy change")
    if change.get("canonical_archive_changed") is not False:
        raise TransportError("manifest unexpectedly claims canonical archive change")
    if change.get("provider_or_kaggle_changed") is not False:
        raise TransportError("manifest unexpectedly claims provider/Kaggle change")

    receipt = {
        "schema": "titan-v3-calibration-transport-verification/v1",
        "operation": OPERATION,
        "manifest_sha256": _sha256(manifest_raw),
        "base_commit": manifest["base_commit"],
        "parts": part_receipts,
        "decoded_gzip_bytes": len(compressed),
        "decoded_gzip_sha256": expected_gzip_sha,
        "decoded_patch_bytes": len(patch),
        "decoded_patch_sha256": _sha256(patch),
        "stable_patch_id": actual_patch_id,
        "files_added_declared": EXPECTED_FILES_ADDED,
    }
    return patch, receipt


def exclusive_write(output: Path, payload: bytes) -> Path:
    output_abs = _absolute(output)
    parent = _require_real_directory(output_abs.parent, "output parent")
    output_abs = parent / output_abs.name
    if output_abs.name in {"", ".", ".."}:
        raise TransportError("output: invalid filename")
    if os.path.lexists(output_abs):
        raise TransportError("output: refusing to overwrite existing path")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(output_abs, flags, 0o600)
    except OSError as exc:
        raise TransportError(f"output: exclusive create failed: {exc}") from exc
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        directory_fd = None
        try:
            directory_fd = os.open(parent, os.O_RDONLY)
        except OSError:
            pass
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    except Exception:
        try:
            output_abs.unlink()
        except OSError:
            pass
        raise
    return output_abs


def materialize(delivery_dir: Path, output: Path) -> dict[str, Any]:
    patch, receipt = verify_delivery(delivery_dir)
    written = exclusive_write(output, patch)
    receipt = dict(receipt)
    receipt["output_bytes"] = len(patch)
    receipt["output_sha256"] = _sha256(written.read_bytes())
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the exact calibration carrier and write one new decoded patch."
    )
    parser.add_argument("delivery_dir", type=Path)
    parser.add_argument("output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        receipt = materialize(args.delivery_dir, args.output)
    except (TransportError, OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
