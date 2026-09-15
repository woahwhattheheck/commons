"""Authenticated current-use wrapper for pursuit portfolio allocation.

The low-level :mod:`core` engine is deterministic replay machinery.  This module
is the production trust boundary: READY/CURABLE rows must be present in a
host-key-authenticated upstream authority generation, current time is sampled by
the verifier, file bytes are consumed from retained no-follow descriptor
generations, and publication never removes a visible pathname during rollback.
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
    verify_compiled,
)

AUTHORITY_SCHEMA = "pursuit-portfolio-allocation/upstream-authority/v1"
KEY_SCHEMA = "pursuit-portfolio-allocation/authority-key/v1"
CURRENT_RECEIPT_SCHEMA = "pursuit-portfolio-allocation/current-receipt/v1"
MAX_AUTHORITY_BYTES = 512 * 1024
MAX_KEY_BYTES = 4096
_SHA = re.compile(r"^[0-9a-f]{64}$")
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}$")
_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_ENTRY_KEYS = frozenset(
    {
        "evidence_captured_at",
        "evidence_ref",
        "opportunity_id",
        "response_deadline",
        "revision",
        "source_sha256",
        "upstream_receipt_sha256",
        "upstream_state",
    }
)
_AUTHORITY_KEYS = frozenset({"schema", "key_id", "issued_at", "entries", "hmac_sha256"})
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


def _generation(info: os.stat_result) -> tuple[int, int]:
    return (int(info.st_dev), int(info.st_ino))


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
    if first != second or _stable_metadata(before) != _stable_metadata(middle) or _stable_metadata(middle) != _stable_metadata(after):
        raise PortfolioError(f"{where}: file generation changed while reading")
    if len(first) != before.st_size:
        raise PortfolioError(f"{where}: file size changed while reading")
    return first


def _read_relative(dir_fd: int, name: str, maximum: int, where: str, *, private: bool = False) -> bytes:
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


def read_regular_bytes(path: str | Path, maximum: int, where: str, *, private: bool = False) -> bytes:
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
    value = load_json_bytes(raw, "authority key")
    value = _exact(value, _KEY_KEYS, "authority key")
    if value["schema"] != KEY_SCHEMA:
        raise PortfolioError("authority key: unsupported schema")
    key_id = _token(value["key_id"], "authority key.key_id")
    key_hex = _sha(value["key_hex"], "authority key.key_hex")
    key = bytes.fromhex(key_hex)
    if len(key) != 32:
        raise PortfolioError("authority key: exactly 32 bytes required")
    return AuthorityKey(key_id=key_id, key=key)


def _normalize_authority(value: Mapping[str, Any]) -> dict[str, Any]:
    value = _exact(value, _AUTHORITY_KEYS, "upstream authority")
    if value["schema"] != AUTHORITY_SCHEMA:
        raise PortfolioError("upstream authority: unsupported schema")
    key_id = _token(value["key_id"], "upstream authority.key_id")
    issued_at = value["issued_at"]
    _dt(issued_at, "upstream authority.issued_at")
    entries_raw = value["entries"]
    if type(entries_raw) is not list or len(entries_raw) > 64:
        raise PortfolioError("upstream authority.entries: bounded list required")
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for idx, item in enumerate(entries_raw):
        item = _exact(item, _ENTRY_KEYS, f"upstream authority.entries[{idx}]")
        opportunity_id = _token(item["opportunity_id"], f"authority entry {idx}.opportunity_id")
        if opportunity_id in seen:
            raise PortfolioError("upstream authority: duplicate opportunity_id")
        seen.add(opportunity_id)
        revision = item["revision"]
        if type(revision) is not int or type(revision) is bool or revision < 1 or revision > 10**9:
            raise PortfolioError(f"authority entry {idx}.revision: positive integer required")
        state = item["upstream_state"]
        if state not in ("READY", "CURABLE"):
            raise PortfolioError(f"authority entry {idx}.upstream_state: READY or CURABLE required")
        captured = item["evidence_captured_at"]
        _dt(captured, f"authority entry {idx}.evidence_captured_at")
        deadline = item["response_deadline"]
        if deadline != "NO_DEADLINE":
            _dt(deadline, f"authority entry {idx}.response_deadline")
        entry = {
            "evidence_captured_at": captured,
            "evidence_ref": _token(item["evidence_ref"], f"authority entry {idx}.evidence_ref"),
            "opportunity_id": opportunity_id,
            "response_deadline": deadline,
            "revision": revision,
            "source_sha256": _sha(item["source_sha256"], f"authority entry {idx}.source_sha256"),
            "upstream_receipt_sha256": _sha(item["upstream_receipt_sha256"], f"authority entry {idx}.upstream_receipt_sha256"),
            "upstream_state": state,
        }
        entries.append(entry)
    return {
        "schema": AUTHORITY_SCHEMA,
        "key_id": key_id,
        "issued_at": issued_at,
        "entries": sorted(entries, key=lambda row: row["opportunity_id"]),
        "hmac_sha256": _sha(value["hmac_sha256"], "upstream authority.hmac_sha256"),
    }


def _authority_unsigned(authority: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "entries": authority["entries"],
        "issued_at": authority["issued_at"],
        "key_id": authority["key_id"],
        "schema": authority["schema"],
    }


def _expected_authority_entries(source: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for opp in source["opportunities"]:
        if opp["upstream_state"] not in ("READY", "CURABLE"):
            continue
        rows.append(
            {
                "evidence_captured_at": opp["evidence_captured_at"],
                "evidence_ref": opp["evidence_ref"],
                "opportunity_id": opp["opportunity_id"],
                "response_deadline": opp["response_deadline"],
                "revision": opp["revision"],
                "source_sha256": opp["source_sha256"],
                "upstream_receipt_sha256": opp["upstream_receipt_sha256"],
                "upstream_state": opp["upstream_state"],
            }
        )
    return sorted(rows, key=lambda row: row["opportunity_id"])


def verify_upstream_authority(
    source: Mapping[str, Any],
    authority: Mapping[str, Any],
    key: AuthorityKey,
    *,
    trusted_now: str,
) -> dict[str, Any]:
    """Verify one normalized authority generation against one normalized input."""
    normalized_source = normalize_input(dict(source))
    normalized = _normalize_authority(authority)
    if normalized["key_id"] != key.key_id:
        raise PortfolioError("upstream authority: key_id mismatch")
    if _dt(normalized["issued_at"], "upstream authority.issued_at") > _dt(trusted_now, "trusted_now"):
        raise PortfolioError("upstream authority: future-issued generation")
    claimed = normalized["hmac_sha256"]
    computed = hmac.new(key.key, _canonical(_authority_unsigned(normalized)), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(claimed, computed):
        raise PortfolioError("upstream authority: HMAC mismatch")
    expected = _expected_authority_entries(normalized_source)
    if normalized["entries"] != expected:
        raise PortfolioError("upstream authority: opportunity generation/state projection mismatch")
    issued_at = _dt(normalized["issued_at"], "upstream authority.issued_at")
    for entry in normalized["entries"]:
        if issued_at < _dt(entry["evidence_captured_at"], "authority evidence_captured_at"):
            raise PortfolioError("upstream authority: issued_at predates attested evidence")
    return normalized


def _current_receipt(
    compiled: CompiledPortfolio,
    authority_bytes: bytes,
    key_id: str,
) -> dict[str, Any]:
    base = {
        "authority_key_id": key_id,
        "authority_sha256": _digest(authority_bytes),
        "core_receipt_sha256": compiled.receipt["receipt_sha256"],
        "evaluated_at": compiled.result["evaluated_at"],
        "input_sha256": compiled.result["input_sha256"],
        "schema": CURRENT_RECEIPT_SCHEMA,
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
    normalized_authority = verify_upstream_authority(
        normalized_source, authority, key, trusted_now=evaluated_at
    )
    compiled = compile_portfolio(normalized_source, evaluated_at=evaluated_at)
    authority_bytes = _canonical(normalized_authority)
    current_receipt = _current_receipt(compiled, authority_bytes, key.key_id)
    return AuthorizedPortfolio(
        compiled=compiled,
        authority=normalized_authority,
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
        }
    )


def _parse_current_receipt(raw: bytes) -> dict[str, Any]:
    value = load_json_bytes(raw, "current receipt")
    value = _exact(value, _CURRENT_RECEIPT_KEYS, "current receipt")
    if value["schema"] != CURRENT_RECEIPT_SCHEMA:
        raise PortfolioError("current receipt: unsupported schema")
    _token(value["authority_key_id"], "current receipt.authority_key_id")
    for name in ("authority_sha256", "core_receipt_sha256", "input_sha256", "receipt_sha256"):
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
    history = verify_compiled(result_raw, markdown_raw, receipt_raw)
    result = load_json_bytes(result_raw, "result")
    source = result.get("normalized_input")
    if type(source) is not dict:
        raise PortfolioError("result: embedded normalized input required")
    authority_value = load_json_bytes(authority_raw, "upstream authority")
    normalized_authority = verify_upstream_authority(source, authority_value, key, trusted_now=trusted_now)
    canonical_authority = _canonical(normalized_authority)
    if authority_raw != canonical_authority:
        raise PortfolioError("upstream authority: noncanonical persisted bytes")
    current_receipt = _parse_current_receipt(current_receipt_raw)
    if current_receipt["authority_key_id"] != key.key_id:
        raise PortfolioError("current receipt: authority key mismatch")
    if current_receipt["authority_sha256"] != _digest(authority_raw):
        raise PortfolioError("current receipt: authority generation mismatch")
    if current_receipt["core_receipt_sha256"] != history["receipt_sha256"]:
        raise PortfolioError("current receipt: core receipt mismatch")
    if current_receipt["input_sha256"] != history["input_sha256"]:
        raise PortfolioError("current receipt: input mismatch")
    if current_receipt["evaluated_at"] != result.get("evaluated_at"):
        raise PortfolioError("current receipt: evaluation-time mismatch")
    current = _compile_authorized_at(source, normalized_authority, key, trusted_now)
    if _decision_fingerprint(result) != _decision_fingerprint(current.compiled.result):
        raise PortfolioError("current verification: allocation decision is stale")
    return {
        "authority_sha256": _digest(authority_raw),
        "historical_integrity_verified": True,
        "original_evaluated_at": result["evaluated_at"],
        "selected_opportunity_ids": result["selected_opportunity_ids"],
        "selected_priority_units": result["selected_priority_units"],
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


def _write_relative(dir_fd: int, name: str, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    fd = os.open(name, flags, 0o600, dir_fd=dir_fd)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise PortfolioError(f"publication: {name} is not a regular file")
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise PortfolioError(f"publication: short write for {name}")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def publish_authorized(value: AuthorizedPortfolio, out_dir: str | Path) -> None:
    """Publish under retained directory custody; never pathname-delete on failure."""
    absolute = os.path.abspath(os.fspath(out_dir))
    parent, name = os.path.split(absolute)
    if not name or name in (".", ".."):
        raise PortfolioError("publication: final directory component required")
    parent_fd = _open_dir_chain(parent or os.sep)
    dest_fd: int | None = None
    published: list[str] = []
    try:
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent_fd)
        except OSError as exc:
            raise PortfolioError("publication: output directory must be new") from exc
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        dest_fd = os.open(name, flags, dir_fd=parent_fd)
        files = (
            ("portfolio.json", value.compiled.result_bytes),
            ("portfolio.md", value.compiled.markdown_bytes),
            ("receipt.json", value.compiled.receipt_bytes),
            ("upstream-authority.json", value.authority_bytes),
            ("current-receipt.json", value.current_receipt_bytes),
        )
        for filename, raw in files:
            _write_relative(dest_fd, filename, raw)
            published.append(filename)
        os.fsync(dest_fd)
        os.fsync(parent_fd)
    except Exception as exc:
        if isinstance(exc, PortfolioError):
            raise PortfolioError(
                f"publication failed; already-published files are preserved: {','.join(published) or 'none'}; {exc}"
            ) from exc
        raise PortfolioError(
            f"publication failed; already-published files are preserved: {','.join(published) or 'none'}"
        ) from exc
    finally:
        if dest_fd is not None:
            os.close(dest_fd)
        os.close(parent_fd)


def read_published_authorized(out_dir: str | Path) -> tuple[bytes, bytes, bytes, bytes, bytes]:
    dir_fd = _open_dir_chain(out_dir)
    try:
        return (
            _read_relative(dir_fd, "portfolio.json", MAX_FILE_BYTES, "portfolio.json"),
            _read_relative(dir_fd, "portfolio.md", MAX_FILE_BYTES, "portfolio.md"),
            _read_relative(dir_fd, "receipt.json", MAX_FILE_BYTES, "receipt.json"),
            _read_relative(dir_fd, "upstream-authority.json", MAX_AUTHORITY_BYTES, "upstream-authority.json"),
            _read_relative(dir_fd, "current-receipt.json", MAX_AUTHORITY_BYTES, "current-receipt.json"),
        )
    finally:
        os.close(dir_fd)
