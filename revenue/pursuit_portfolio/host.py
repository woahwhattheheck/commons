"""Fixed-host current-use boundary for Pursuit Portfolio v2.

``core_v2`` is deterministic replay machinery: its ``trusted_*_sha256``
argument is useful only when the caller already owns an independent trust root.
This module supplies that production trust root from fixed owner-retained host
state and adds current/supersession semantics.

No function here can advance the retained authority floor.  The independent
owner/signer/registrar updates that state outside candidate packet authorship.
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
from typing import Any

from . import core_v2 as core

KEY_SCHEMA = "pursuit-portfolio-allocation/authority-key/v1"
FLOOR_SCHEMA = "pursuit-portfolio-allocation/authority-floor/v2"
HOST_SEAL_SCHEMA = "pursuit-portfolio-allocation/host-seal/v3"
HOST_ROOT = Path.home() / ".config" / "commons" / "pursuit-portfolio"
HOST_KEY_PATH = HOST_ROOT / "authority-key.json"
HOST_FLOOR_PATH = HOST_ROOT / "authority-floor.json"
MAX_KEY_BYTES = 4096
MAX_FLOOR_BYTES = 16 * 1024
MAX_SEAL_BYTES = 16 * 1024
_SHA = re.compile(r"^[0-9a-f]{64}$")
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}$")
_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_KEY_KEYS = frozenset({"schema", "key_id", "key_hex"})
_FLOOR_KEYS = frozenset(
    {"schema", "key_id", "revision", "authority_sha256", "updated_at", "hmac_sha256"}
)
_SEAL_KEYS = frozenset(
    {
        "authority_revision",
        "authority_sha256",
        "evaluated_at",
        "floor_sha256",
        "hmac_sha256",
        "input_sha256",
        "key_id",
        "markdown_sha256",
        "receipt_file_sha256",
        "result_sha256",
        "schema",
    }
)


@dataclass(frozen=True)
class HostKey:
    key_id: str
    key: bytes


@dataclass(frozen=True)
class AuthorityFloor:
    revision: int
    authority_sha256: str
    key_id: str
    updated_at: str
    raw: bytes


@dataclass(frozen=True)
class HostCompiledPortfolio:
    compiled: core.CompiledPortfolio
    host_seal: dict[str, Any]
    host_seal_bytes: bytes


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
        raise core.PortfolioError("host payload is not canonical JSON") from exc


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dt(value: Any, where: str) -> datetime:
    if type(value) is not str or _TS.fullmatch(value) is None:
        raise core.PortfolioError(f"{where}: canonical UTC-second timestamp required")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise core.PortfolioError(f"{where}: invalid timestamp") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise core.PortfolioError(f"{where}: noncanonical timestamp")
    return parsed


def _exact(value: Any, keys: frozenset[str], where: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != set(keys):
        raise core.PortfolioError(f"{where}: exact key set required")
    return value


def _sha(value: Any, where: str) -> str:
    if type(value) is not str or _SHA.fullmatch(value) is None:
        raise core.PortfolioError(f"{where}: lowercase SHA-256 required")
    return value


def _token(value: Any, where: str) -> str:
    if type(value) is not str or _TOKEN.fullmatch(value) is None:
        raise core.PortfolioError(f"{where}: bounded token required")
    return value


def _secure_dir_capable() -> bool:
    supports = getattr(os, "supports_dir_fd", set())
    return (
        os.open in supports
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
    )


def _open_dir_chain(path: str | Path) -> int:
    """Open an absolute directory generation without following any symlink component."""
    if not _secure_dir_capable():
        raise core.PortfolioError(
            "secure retained-directory operations unsupported on this platform"
        )
    absolute = os.path.abspath(os.fspath(path))
    drive, tail = os.path.splitdrive(absolute)
    if drive:
        raise core.PortfolioError("secure directory walk does not support drive paths")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    fd = os.open(os.sep, flags)
    try:
        for part in [p for p in tail.split(os.sep) if p]:
            if part in (".", ".."):
                raise core.PortfolioError("directory traversal component forbidden")
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except Exception:
        os.close(fd)
        raise


def _stable_metadata(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        int(info.st_dev),
        int(info.st_ino),
        int(info.st_size),
        int(getattr(info, "st_mtime_ns", int(info.st_mtime * 1_000_000_000))),
        int(getattr(info, "st_ctime_ns", int(info.st_ctime * 1_000_000_000))),
    )


def _read_fd_twice(fd: int, maximum: int, where: str) -> bytes:
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode):
        raise core.PortfolioError(f"{where}: regular file required")
    if before.st_size < 0 or before.st_size > maximum:
        raise core.PortfolioError(f"{where}: file exceeds byte bound")

    def once() -> bytes:
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
            raise core.PortfolioError(f"{where}: file exceeds byte bound")
        return raw

    first = once()
    middle = os.fstat(fd)
    second = once()
    after = os.fstat(fd)
    if (
        first != second
        or _stable_metadata(before) != _stable_metadata(middle)
        or _stable_metadata(middle) != _stable_metadata(after)
    ):
        raise core.PortfolioError(f"{where}: file generation changed while reading")
    if len(first) != before.st_size:
        raise core.PortfolioError(f"{where}: file size changed while reading")
    return first


def _read_relative(
    dir_fd: int,
    name: str,
    maximum: int,
    where: str,
    *,
    private: bool = False,
) -> bytes:
    if not name or os.sep in name or (os.altsep and os.altsep in name) or name in (".", ".."):
        raise core.PortfolioError(f"{where}: invalid final path component")
    flags = os.O_RDONLY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    fd = os.open(name, flags, dir_fd=dir_fd)
    try:
        info = os.fstat(fd)
        if private and os.name == "posix" and stat.S_IMODE(info.st_mode) & 0o077:
            raise core.PortfolioError(f"{where}: owner-only permissions required")
        return _read_fd_twice(fd, maximum, where)
    finally:
        os.close(fd)


def read_regular_bytes(
    path: str | Path,
    maximum: int = core.MAX_FILE_BYTES,
    where: str = "input",
    *,
    private: bool = False,
) -> bytes:
    absolute = os.path.abspath(os.fspath(path))
    parent, name = os.path.split(absolute)
    if not name:
        raise core.PortfolioError(f"{where}: file path required")
    parent_fd = _open_dir_chain(parent or os.sep)
    try:
        return _read_relative(parent_fd, name, maximum, where, private=private)
    finally:
        os.close(parent_fd)


def load_candidate_json(path: str | Path, where: str) -> dict[str, Any]:
    return core.load_json_bytes(read_regular_bytes(path, core.MAX_FILE_BYTES, where), where)


def load_host_key(path: str | Path = HOST_KEY_PATH) -> HostKey:
    raw = read_regular_bytes(path, MAX_KEY_BYTES, "authority key", private=True)
    value = _exact(core.load_json_bytes(raw, "authority key"), _KEY_KEYS, "authority key")
    if value["schema"] != KEY_SCHEMA:
        raise core.PortfolioError("authority key: unsupported schema")
    key_id = _token(value["key_id"], "authority key.key_id")
    key_hex = _sha(value["key_hex"], "authority key.key_hex")
    key = bytes.fromhex(key_hex)
    if len(key) != 32:
        raise core.PortfolioError("authority key: exactly 32 bytes required")
    return HostKey(key_id=key_id, key=key)


def _floor_unsigned(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "authority_sha256": value["authority_sha256"],
        "key_id": value["key_id"],
        "revision": value["revision"],
        "schema": value["schema"],
        "updated_at": value["updated_at"],
    }


def _load_floor_at(path: str | Path, key: HostKey, trusted_now: str) -> AuthorityFloor:
    raw = read_regular_bytes(path, MAX_FLOOR_BYTES, "authority floor", private=True)
    value = _exact(core.load_json_bytes(raw, "authority floor"), _FLOOR_KEYS, "authority floor")
    if value["schema"] != FLOOR_SCHEMA:
        raise core.PortfolioError("authority floor: unsupported schema")
    if value["key_id"] != key.key_id:
        raise core.PortfolioError("authority floor: key_id mismatch")
    revision = value["revision"]
    if type(revision) is not int or type(revision) is bool or not (1 <= revision <= 10**9):
        raise core.PortfolioError("authority floor.revision: positive bounded integer required")
    normalized = {
        "authority_sha256": _sha(value["authority_sha256"], "authority floor.authority_sha256"),
        "hmac_sha256": _sha(value["hmac_sha256"], "authority floor.hmac_sha256"),
        "key_id": key.key_id,
        "revision": revision,
        "schema": FLOOR_SCHEMA,
        "updated_at": value["updated_at"],
    }
    _dt(normalized["updated_at"], "authority floor.updated_at")
    if raw != _canonical(normalized):
        raise core.PortfolioError("authority floor: persisted bytes must be canonical JSON")
    if _dt(normalized["updated_at"], "authority floor.updated_at") > _dt(trusted_now, "trusted_now"):
        raise core.PortfolioError("authority floor: future-updated generation")
    expected = hmac.new(
        key.key, _canonical(_floor_unsigned(normalized)), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(normalized["hmac_sha256"], expected):
        raise core.PortfolioError("authority floor: HMAC mismatch")
    return AuthorityFloor(
        revision=revision,
        authority_sha256=normalized["authority_sha256"],
        key_id=key.key_id,
        updated_at=normalized["updated_at"],
        raw=raw,
    )


def load_authority_floor(path: str | Path = HOST_FLOOR_PATH) -> AuthorityFloor:
    key = load_host_key(HOST_KEY_PATH)
    return _load_floor_at(path, key, _now())


def _validate_current_authority(
    authority: dict[str, Any], floor: AuthorityFloor, trusted_now: str
) -> dict[str, Any]:
    normalized = core.normalize_upstream_authority(authority)
    observed = core.upstream_authority_sha256(normalized)
    if not hmac.compare_digest(observed, floor.authority_sha256):
        raise core.PortfolioError(
            "authority floor: packaged upstream authority is superseded or not the retained current generation"
        )
    if normalized["revision"] != floor.revision:
        raise core.PortfolioError("authority floor: authority revision mismatch")
    generated = _dt(normalized["generated_at"], "upstream_authority.generated_at")
    if generated > _dt(trusted_now, "trusted_now"):
        raise core.PortfolioError("upstream authority: future-generated current generation")
    if _dt(floor.updated_at, "authority floor.updated_at") < generated:
        raise core.PortfolioError("authority floor: update predates retained authority generation")
    return normalized


def _same_floor(before: AuthorityFloor, after: AuthorityFloor) -> None:
    if not hmac.compare_digest(before.raw, after.raw):
        raise core.PortfolioError("authority floor: generation changed during current-use operation")


def _seal_base(
    compiled: core.CompiledPortfolio, floor: AuthorityFloor, key: HostKey
) -> dict[str, Any]:
    return {
        "authority_revision": floor.revision,
        "authority_sha256": floor.authority_sha256,
        "evaluated_at": compiled.result["evaluated_at"],
        "floor_sha256": _digest(floor.raw),
        "input_sha256": compiled.result["input_sha256"],
        "key_id": key.key_id,
        "markdown_sha256": _digest(compiled.markdown_bytes),
        "receipt_file_sha256": _digest(compiled.receipt_bytes),
        "result_sha256": _digest(compiled.result_bytes),
        "schema": HOST_SEAL_SCHEMA,
    }


def _seal(compiled: core.CompiledPortfolio, floor: AuthorityFloor, key: HostKey) -> dict[str, Any]:
    base = _seal_base(compiled, floor, key)
    return {
        **base,
        "hmac_sha256": hmac.new(key.key, _canonical(base), hashlib.sha256).hexdigest(),
    }


def _compile_current_at(
    source: dict[str, Any],
    authority: dict[str, Any],
    *,
    trusted_now: str,
    key: HostKey,
    floor: AuthorityFloor,
) -> HostCompiledPortfolio:
    _validate_current_authority(authority, floor, trusted_now)
    compiled = core.compile_portfolio(
        source,
        upstream_authority=authority,
        trusted_upstream_authority_sha256=floor.authority_sha256,
        evaluated_at=trusted_now,
    )
    seal = _seal(compiled, floor, key)
    return HostCompiledPortfolio(compiled=compiled, host_seal=seal, host_seal_bytes=_canonical(seal))


def compile_current(source: dict[str, Any], authority: dict[str, Any]) -> HostCompiledPortfolio:
    """Compile using verifier-owned time and fixed retained host authority state."""
    trusted_now = _now()
    key = load_host_key(HOST_KEY_PATH)
    floor_before = _load_floor_at(HOST_FLOOR_PATH, key, trusted_now)
    value = _compile_current_at(
        source, authority, trusted_now=trusted_now, key=key, floor=floor_before
    )
    floor_after = _load_floor_at(HOST_FLOOR_PATH, key, trusted_now)
    _same_floor(floor_before, floor_after)
    _validate_current_authority(authority, floor_after, trusted_now)
    return value


def _parse_seal(raw: bytes) -> dict[str, Any]:
    value = _exact(core.load_json_bytes(raw, "host seal"), _SEAL_KEYS, "host seal")
    if value["schema"] != HOST_SEAL_SCHEMA:
        raise core.PortfolioError("host seal: unsupported schema")
    revision = value["authority_revision"]
    if type(revision) is not int or type(revision) is bool or not (1 <= revision <= 10**9):
        raise core.PortfolioError("host seal: invalid authority_revision")
    _token(value["key_id"], "host seal.key_id")
    _dt(value["evaluated_at"], "host seal.evaluated_at")
    for name in (
        "authority_sha256",
        "floor_sha256",
        "hmac_sha256",
        "input_sha256",
        "markdown_sha256",
        "receipt_file_sha256",
        "result_sha256",
    ):
        _sha(value[name], f"host seal.{name}")
    if raw != _canonical(value):
        raise core.PortfolioError("host seal: persisted bytes must be canonical JSON")
    return value


def _decision_fingerprint(result: dict[str, Any]) -> bytes:
    rows = [
        {
            "allocation_state": row["allocation_state"],
            "evidence_captured_at": row["evidence_captured_at"],
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


def _verify_current_at(
    result_raw: bytes,
    markdown_raw: bytes,
    receipt_raw: bytes,
    seal_raw: bytes,
    *,
    trusted_now: str,
    key: HostKey,
    floor: AuthorityFloor,
) -> dict[str, Any]:
    seal = _parse_seal(seal_raw)
    result = core.load_json_bytes(result_raw, "result")
    source = result.get("normalized_input")
    authority = result.get("normalized_upstream_authority")
    if type(source) is not dict or type(authority) is not dict:
        raise core.PortfolioError("result: embedded normalized input/authority required")
    _validate_current_authority(authority, floor, trusted_now)

    expected_base = {
        "authority_revision": floor.revision,
        "authority_sha256": floor.authority_sha256,
        "evaluated_at": result.get("evaluated_at"),
        "floor_sha256": _digest(floor.raw),
        "input_sha256": result.get("input_sha256"),
        "key_id": key.key_id,
        "markdown_sha256": _digest(markdown_raw),
        "receipt_file_sha256": _digest(receipt_raw),
        "result_sha256": _digest(result_raw),
        "schema": HOST_SEAL_SCHEMA,
    }
    base = {name: seal[name] for name in expected_base}
    if base != expected_base:
        raise core.PortfolioError("host seal: exact package/current-floor binding mismatch")
    expected_mac = hmac.new(key.key, _canonical(base), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(seal["hmac_sha256"], expected_mac):
        raise core.PortfolioError("host seal: HMAC mismatch")

    historical = core.verify_compiled(
        result_raw,
        markdown_raw,
        receipt_raw,
        trusted_upstream_authority_sha256=floor.authority_sha256,
    )
    current = core.compile_portfolio(
        source,
        upstream_authority=authority,
        trusted_upstream_authority_sha256=floor.authority_sha256,
        evaluated_at=trusted_now,
    )
    if _decision_fingerprint(result) != _decision_fingerprint(current.result):
        raise core.PortfolioError("current verification: portfolio allocation decision is stale")
    return {
        **historical,
        "authority_floor_revision": floor.revision,
        "authority_floor_sha256": _digest(floor.raw),
        "host_seal_sha256": _digest(seal_raw),
        "host_seal_verified": True,
        "verified_at": trusted_now,
        "verified_current": True,
    }


def verify_current_bytes(
    result_raw: bytes, markdown_raw: bytes, receipt_raw: bytes, seal_raw: bytes
) -> dict[str, Any]:
    """Verify current authority, host seal, deterministic history, and fresh semantics."""
    trusted_now = _now()
    key = load_host_key(HOST_KEY_PATH)
    floor_before = _load_floor_at(HOST_FLOOR_PATH, key, trusted_now)
    verified = _verify_current_at(
        result_raw,
        markdown_raw,
        receipt_raw,
        seal_raw,
        trusted_now=trusted_now,
        key=key,
        floor=floor_before,
    )
    floor_after = _load_floor_at(HOST_FLOOR_PATH, key, trusted_now)
    _same_floor(floor_before, floor_after)
    result = core.load_json_bytes(result_raw, "result")
    _validate_current_authority(result["normalized_upstream_authority"], floor_after, trusted_now)
    return verified


def _write_owned_relative(dir_fd: int, name: str, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    fd = os.open(name, flags, 0o600, dir_fd=dir_fd)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise core.PortfolioError(f"publication: {name} is not a regular file")
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise core.PortfolioError(f"publication: short write for {name}")
            view = view[written:]
        os.fsync(fd)
        final = os.fstat(fd)
        visible = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
        if (int(final.st_dev), int(final.st_ino)) != (int(visible.st_dev), int(visible.st_ino)):
            raise core.PortfolioError(f"publication: visible output ownership changed: {name}")
        if not stat.S_ISREG(visible.st_mode):
            raise core.PortfolioError(f"publication: visible output is not regular: {name}")
    finally:
        os.close(fd)


def publish_current(value: HostCompiledPortfolio, out_dir: str | Path) -> None:
    """Create package files exclusively inside one pre-existing retained directory."""
    dir_fd = _open_dir_chain(out_dir)
    published: list[str] = []
    try:
        files = (
            ("portfolio.json", value.compiled.result_bytes),
            ("portfolio.md", value.compiled.markdown_bytes),
            ("receipt.json", value.compiled.receipt_bytes),
            ("host-seal.json", value.host_seal_bytes),
        )
        for name, raw in files:
            try:
                _write_owned_relative(dir_fd, name, raw)
            except Exception as exc:
                raise core.PortfolioError(
                    "publication failed; retained output generation preserved; "
                    f"already-published files: {','.join(published) or 'none'}"
                ) from exc
            published.append(name)
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def read_current_directory(root: str | Path) -> tuple[bytes, bytes, bytes, bytes]:
    dir_fd = _open_dir_chain(root)
    try:
        return (
            _read_relative(dir_fd, "portfolio.json", core.MAX_FILE_BYTES, "portfolio.json"),
            _read_relative(dir_fd, "portfolio.md", core.MAX_FILE_BYTES, "portfolio.md"),
            _read_relative(dir_fd, "receipt.json", core.MAX_FILE_BYTES, "receipt.json"),
            _read_relative(dir_fd, "host-seal.json", MAX_SEAL_BYTES, "host-seal.json"),
        )
    finally:
        os.close(dir_fd)


def verify_current_directory(root: str | Path) -> dict[str, Any]:
    return verify_current_bytes(*read_current_directory(root))
