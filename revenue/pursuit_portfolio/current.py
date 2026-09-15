"""Authenticated current-use adapter for the v2 pursuit-portfolio core.

The deterministic core keeps owner planning input separate from upstream
readiness authority.  This module adds a host-key signature around the exact
normalized v2 authority generation, samples verifier-owned UTC, consumes files
from retained no-follow descriptor generations, and binds the signed authority
to a current-use receipt.  It does not move READY/CURABLE state back into the
portfolio source.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Mapping

from .core import (
    MAX_FILE_BYTES,
    CompiledPortfolio,
    PortfolioError,
    compile_portfolio,
    load_json_bytes,
    normalize_input,
    normalize_upstream_authority,
    upstream_authority_sha256,
    verify_compiled,
)

SIGNED_AUTHORITY_SCHEMA = "pursuit-portfolio-allocation/signed-upstream-authority/v1"
KEY_SCHEMA = "pursuit-portfolio-allocation/authority-key/v1"
CURRENT_RECEIPT_SCHEMA = "pursuit-portfolio-allocation/current-receipt/v2"
MAX_AUTHORITY_BYTES = 512 * 1024
MAX_KEY_BYTES = 4096
_SHA = re.compile(r"^[0-9a-f]{64}$")
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}$")
_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_SIGNED_AUTHORITY_KEYS = frozenset(
    {"schema", "key_id", "issued_at", "upstream_authority", "hmac_sha256"}
)
_KEY_KEYS = frozenset({"schema", "key_id", "key_hex"})
_CURRENT_RECEIPT_KEYS = frozenset(
    {
        "authority_key_id",
        "authority_sha256",
        "core_receipt_sha256",
        "evaluated_at",
        "input_sha256",
        "receipt_sha256",
        "schema",
        "upstream_authority_sha256",
    }
)


@dataclass(frozen=True)
class AuthorityKey:
    key_id: str
    key: bytes


@dataclass(frozen=True)
class AuthorizedPortfolio:
    compiled: CompiledPortfolio
    authority: dict[str, Any]
    authority_bytes: bytes
    current_receipt: dict[str, Any]
    current_receipt_bytes: bytes


def _canonical(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PortfolioError("current-use payload is not canonical JSON") from exc


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dt(value: str, where: str) -> datetime:
    if type(value) is not str or _TS.fullmatch(value) is None:
        raise PortfolioError(f"{where}: canonical UTC-second timestamp required")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise PortfolioError(f"{where}: invalid timestamp") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise PortfolioError(f"{where}: noncanonical timestamp")
    return parsed


def _exact(value: Any, keys: frozenset[str], where: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != set(keys):
        raise PortfolioError(f"{where}: exact key set required")
    return value


def _token(value: Any, where: str) -> str:
    if type(value) is not str or _TOKEN.fullmatch(value) is None:
        raise PortfolioError(f"{where}: bounded token required")
    return value


def _sha(value: Any, where: str) -> str:
    if type(value) is not str or _SHA.fullmatch(value) is None:
        raise PortfolioError(f"{where}: lowercase SHA-256 required")
    return value


def _stable_metadata(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        int(info.st_dev),
        int(info.st_ino),
        int(info.st_size),
        int(getattr(info, "st_mtime_ns", int(info.st_mtime * 1_000_000_000))),
        int(getattr(info, "st_ctime_ns", int(info.st_ctime * 1_000_000_000))),
    )


def _secure_dir_capable() -> bool:
    supports = getattr(os, "supports_dir_fd", set())
    return (
        os.open in supports
        and os.mkdir in supports
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
    )


def _open_dir_chain(path: str | Path) -> int:
    """Open an absolute directory by walking every component without symlinks."""
    if not _secure_dir_capable():
        raise PortfolioError("secure directory-descriptor operations unsupported on this platform")
    absolute = os.path.abspath(os.fspath(path))
    drive, tail = os.path.splitdrive(absolute)
    if drive:
        raise PortfolioError("secure directory-descriptor publication does not support drive paths")
    parts = [part for part in tail.split(os.sep) if part]
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(os.sep, flags)
    try:
        for part in parts:
            if part in (".", ".."):
                raise PortfolioError("directory traversal component forbidden")
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except Exception:
        os.close(fd)
        raise


def _read_fd_twice(fd: int, maximum: int, where: str) -> bytes:
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode):
        raise PortfolioError(f"{where}: regular file required")
    if before.st_size < 0 or before.st_size > maximum:
        raise PortfolioError(f"{where}: file exceeds byte bound")

    def read_once() -> bytes:
        os.lseek(fd, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining > 0:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > maximum:
            raise PortfolioError(f"{where}: file exceeds byte bound")
        return raw

    first = read_once()
    middle = os.fstat(fd)
    second = read_once()
    after = os.fstat(fd)
    if (
        first != second
        or _stable_metadata(before) != _stable_metadata(middle)
        or _stable_metadata(middle) != _stable_metadata(after)
    ):
        raise PortfolioError(f"{where}: file generation changed while reading")
    if len(first) != before.st_size:
        raise PortfolioError(f"{where}: file size changed while reading")
    return first


def _read_relative(
    dir_fd: int, name: str, maximum: int, where: str, *, private: bool = False
) -> bytes:
    if os.sep in name or (os.altsep and os.altsep in name) or name in (".", ".."):
        raise PortfolioError(f"{where}: invalid final path component")
    flags = os.O_RDONLY | os.O_NOFOLLOW
    fd = os.open(name, flags, dir_fd=dir_fd)
    try:
        info = os.fstat(fd)
        if private and os.name == "posix" and stat.S_IMODE(info.st_mode) & 0o077:
            raise PortfolioError(f"{where}: owner-only permissions required")
        return _read_fd_twice(fd, maximum, where)
    finally:
        os.close(fd)


def read_regular_bytes(
    path: str | Path, maximum: int, where: str, *, private: bool = False
) -> bytes:
    """Consume one retained ordinary-file generation; reject symlinked ancestors."""
    absolute = os.path.abspath(os.fspath(path))
    parent, name = os.path.split(absolute)
    if not name:
        raise PortfolioError(f"{where}: file path required")
    parent_fd = _open_dir_chain(parent or os.sep)
    try:
        return _read_relative(parent_fd, name, maximum, where, private=private)
    finally:
        os.close(parent_fd)


def load_current_input(path: str | Path) -> dict[str, Any]:
    return load_json_bytes(read_regular_bytes(path, MAX_FILE_BYTES, "input"), "input")


def load_authority_key(path: str | Path) -> AuthorityKey:
    raw = read_regular_bytes(path, MAX_KEY_BYTES, "authority key", private=True)
    value = _exact(load_json_bytes(raw, "authority key"), _KEY_KEYS, "authority key")
    if value["schema"] != KEY_SCHEMA:
        raise PortfolioError("authority key: unsupported schema")
    key_id = _token(value["key_id"], "authority key.key_id")
    key_hex = _sha(value["key_hex"], "authority key.key_hex")
    key = bytes.fromhex(key_hex)
    if len(key) != 32:
        raise PortfolioError("authority key: exactly 32 bytes required")
    return AuthorityKey(key_id=key_id, key=key)


def _normalize_signed_authority(value: Mapping[str, Any]) -> dict[str, Any]:
    value = _exact(value, _SIGNED_AUTHORITY_KEYS, "signed upstream authority")
    if value["schema"] != SIGNED_AUTHORITY_SCHEMA:
        raise PortfolioError("signed upstream authority: unsupported schema")
    key_id = _token(value["key_id"], "signed upstream authority.key_id")
    issued_at = value["issued_at"]
    _dt(issued_at, "signed upstream authority.issued_at")
    inner = normalize_upstream_authority(dict(value["upstream_authority"]))
    return {
        "hmac_sha256": _sha(value["hmac_sha256"], "signed upstream authority.hmac_sha256"),
        "issued_at": issued_at,
        "key_id": key_id,
        "schema": SIGNED_AUTHORITY_SCHEMA,
        "upstream_authority": inner,
    }


def _authority_unsigned(authority: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "issued_at": authority["issued_at"],
        "key_id": authority["key_id"],
        "schema": authority["schema"],
        "upstream_authority": authority["upstream_authority"],
    }


def verify_upstream_authority(
    authority: Mapping[str, Any], key: AuthorityKey, *, trusted_now: str
) -> dict[str, Any]:
    """Verify a host-signed wrapper around one exact normalized v2 authority generation."""
    normalized = _normalize_signed_authority(authority)
    if normalized["key_id"] != key.key_id:
        raise PortfolioError("signed upstream authority: key_id mismatch")
    issued = _dt(normalized["issued_at"], "signed upstream authority.issued_at")
    now = _dt(trusted_now, "trusted_now")
    if issued > now:
        raise PortfolioError("signed upstream authority: future-issued generation")
    generated = _dt(
        normalized["upstream_authority"]["generated_at"],
        "signed upstream authority.upstream_authority.generated_at",
    )
    if generated > issued:
        raise PortfolioError("signed upstream authority: issued_at predates authority generation")
    expected = hmac.new(
        key.key, _canonical(_authority_unsigned(normalized)), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(normalized["hmac_sha256"], expected):
        raise PortfolioError("signed upstream authority: HMAC mismatch")
    return normalized


def _current_receipt(
    compiled: CompiledPortfolio,
    authority_bytes: bytes,
    upstream_authority_sha: str,
    key_id: str,
) -> dict[str, Any]:
    base = {
        "authority_key_id": key_id,
        "authority_sha256": _digest(authority_bytes),
        "core_receipt_sha256": compiled.receipt["receipt_sha256"],
        "evaluated_at": compiled.result["evaluated_at"],
        "input_sha256": compiled.result["input_sha256"],
        "schema": CURRENT_RECEIPT_SCHEMA,
        "upstream_authority_sha256": upstream_authority_sha,
    }
    return {**base, "receipt_sha256": _digest(_canonical(base))}


def _compile_authorized_at(
    source: Mapping[str, Any],
    authority: Mapping[str, Any],
    key: AuthorityKey,
    evaluated_at: str,
) -> AuthorizedPortfolio:
    _dt(evaluated_at, "evaluated_at")
    normalized_source = normalize_input(dict(source))
    signed = verify_upstream_authority(authority, key, trusted_now=evaluated_at)
    inner = signed["upstream_authority"]
    inner_sha = upstream_authority_sha256(inner)
    compiled = compile_portfolio(
        normalized_source,
        upstream_authority=inner,
        trusted_upstream_authority_sha256=inner_sha,
        evaluated_at=evaluated_at,
    )
    authority_bytes = _canonical(signed)
    current_receipt = _current_receipt(compiled, authority_bytes, inner_sha, key.key_id)
    return AuthorizedPortfolio(
        compiled=compiled,
        authority=signed,
        authority_bytes=authority_bytes,
        current_receipt=current_receipt,
        current_receipt_bytes=_canonical(current_receipt),
    )


def compile_authorized_current(
    source: Mapping[str, Any], authority: Mapping[str, Any], key: AuthorityKey
) -> AuthorizedPortfolio:
    """Compile a production current-use portfolio using verifier-owned UTC."""
    return _compile_authorized_at(source, authority, key, _now())


def _decision_fingerprint(result: Mapping[str, Any]) -> bytes:
    rows = [
        {
            "allocation_state": row["allocation_state"],
            "individual_fit_counterfactual": row["individual_fit_counterfactual"],
            "opportunity_id": row["opportunity_id"],
            "reasons": row["reasons"],
            "upstream_state": row["upstream_state"],
        }
        for row in result["opportunities"]
    ]
    return _canonical(
        {
            "capacity": result["capacity"],
            "opportunities": rows,
            "policy_sha256": result["policy_sha256"],
            "selected_opportunity_ids": result["selected_opportunity_ids"],
            "selected_priority_units": result["selected_priority_units"],
            "upstream_authority_sha256": result["upstream_authority_sha256"],
        }
    )


def _parse_current_receipt(raw: bytes) -> dict[str, Any]:
    value = _exact(
        load_json_bytes(raw, "current receipt"),
        _CURRENT_RECEIPT_KEYS,
        "current receipt",
    )
    if value["schema"] != CURRENT_RECEIPT_SCHEMA:
        raise PortfolioError("current receipt: unsupported schema")
    _token(value["authority_key_id"], "current receipt.authority_key_id")
    for name in (
        "authority_sha256",
        "core_receipt_sha256",
        "input_sha256",
        "receipt_sha256",
        "upstream_authority_sha256",
    ):
        _sha(value[name], f"current receipt.{name}")
    _dt(value["evaluated_at"], "current receipt.evaluated_at")
    base = dict(value)
    claimed = base.pop("receipt_sha256")
    if not hmac.compare_digest(claimed, _digest(_canonical(base))):
        raise PortfolioError("current receipt: self commitment mismatch")
    return value


def _verify_authorized_at(
    result_raw: bytes,
    markdown_raw: bytes,
    receipt_raw: bytes,
    authority_raw: bytes,
    current_receipt_raw: bytes,
    key: AuthorityKey,
    trusted_now: str,
) -> dict[str, Any]:
    result = load_json_bytes(result_raw, "result")
    source = result.get("normalized_input")
    if type(source) is not dict:
        raise PortfolioError("result: embedded normalized input required")

    authority_value = load_json_bytes(authority_raw, "signed upstream authority")
    signed = verify_upstream_authority(authority_value, key, trusted_now=trusted_now)
    canonical_authority = _canonical(signed)
    if authority_raw != canonical_authority:
        raise PortfolioError("signed upstream authority: noncanonical persisted bytes")
    inner = signed["upstream_authority"]
    inner_sha = upstream_authority_sha256(inner)
    if result.get("normalized_upstream_authority") != inner:
        raise PortfolioError("result: embedded upstream authority differs from signed generation")

    history = verify_compiled(
        result_raw,
        markdown_raw,
        receipt_raw,
        trusted_upstream_authority_sha256=inner_sha,
    )
    current_receipt = _parse_current_receipt(current_receipt_raw)
    if current_receipt["authority_key_id"] != key.key_id:
        raise PortfolioError("current receipt: authority key mismatch")
    if current_receipt["authority_sha256"] != _digest(authority_raw):
        raise PortfolioError("current receipt: signed authority generation mismatch")
    if current_receipt["upstream_authority_sha256"] != inner_sha:
        raise PortfolioError("current receipt: inner authority generation mismatch")
    if current_receipt["core_receipt_sha256"] != history["receipt_sha256"]:
        raise PortfolioError("current receipt: core receipt mismatch")
    if current_receipt["input_sha256"] != history["input_sha256"]:
        raise PortfolioError("current receipt: input mismatch")
    if current_receipt["evaluated_at"] != result.get("evaluated_at"):
        raise PortfolioError("current receipt: evaluation-time mismatch")

    current = _compile_authorized_at(source, signed, key, trusted_now)
    if _decision_fingerprint(result) != _decision_fingerprint(current.compiled.result):
        raise PortfolioError("current verification: allocation decision is stale")
    return {
        "authority_sha256": _digest(authority_raw),
        "historical_integrity_verified": True,
        "original_evaluated_at": result["evaluated_at"],
        "selected_opportunity_ids": result["selected_opportunity_ids"],
        "selected_priority_units": result["selected_priority_units"],
        "upstream_authority_sha256": inner_sha,
        "verified_at": trusted_now,
        "verified_current": True,
    }


def verify_authorized_current(
    result_raw: bytes,
    markdown_raw: bytes,
    receipt_raw: bytes,
    authority_raw: bytes,
    current_receipt_raw: bytes,
    key: AuthorityKey,
) -> dict[str, Any]:
    """Verify historical integrity and fresh-current semantics using process UTC."""
    return _verify_authorized_at(
        result_raw,
        markdown_raw,
        receipt_raw,
        authority_raw,
        current_receipt_raw,
        key,
        _now(),
    )
