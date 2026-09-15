"""Production host authority for pursuit-portfolio current-use operations.

Production has two fixed, non-candidate-selected host resources:

* the HMAC key authenticates upstream positive authority and the full package;
* the separately retained latest-authority floor names the only authority digest
  that is current now.

The second resource is what makes revocation/supersession real: an old valid HMAC
is historical evidence only once the retained floor advances.

On POSIX the trust root is derived from the effective account database entry,
never from HOME/Path.home() or another caller-controlled environment selector.
Each trust leaf is consumed relative to the exact retained directory descriptor
generation whose ownership and mode were validated.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import os
from pathlib import Path
import re
import stat
from typing import Any, Mapping

from .core import PortfolioError, load_json_bytes
from .current import (
    MAX_KEY_BYTES,
    KEY_SCHEMA,
    AuthorizedPortfolio,
    AuthorityKey,
    _canonical,
    _dt,
    _now,
    _open_dir_chain,
    _read_fd_twice,
    _sha,
    _token,
    compile_authorized_current,
    verify_authorized_current,
)
from .floor import (
    FLOOR_SCHEMA,
    MAX_FLOOR_BYTES,
    AuthorityFloor,
    require_current_authority,
)


def _effective_account_home() -> Path:
    """Resolve the POSIX effective account home without consulting process HOME."""
    if os.name != "posix":
        raise PortfolioError("host trust root requires POSIX effective-account authority")
    try:
        import pwd
    except ImportError as exc:  # pragma: no cover - guarded by os.name
        raise PortfolioError("host trust root: POSIX account database unavailable") from exc
    try:
        entry = pwd.getpwuid(os.geteuid())
    except KeyError as exc:
        raise PortfolioError("host trust root: effective account has no passwd entry") from exc
    home = Path(entry.pw_dir)
    if not home.is_absolute():
        raise PortfolioError("host trust root: effective account home must be absolute")
    try:
        info = os.lstat(home)
    except OSError as exc:
        raise PortfolioError("host trust root: effective account home unavailable") from exc
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise PortfolioError("host trust root: effective account home must be a real directory")
    if int(info.st_uid) != int(os.geteuid()):
        raise PortfolioError("host trust root: effective account home ownership mismatch")
    if stat.S_IMODE(info.st_mode) & 0o022:
        raise PortfolioError("host trust root: effective account home must not be group/world writable")
    return home


if os.name == "posix":
    HOST_ROOT = _effective_account_home() / ".config" / "commons" / "pursuit-portfolio"
else:
    # Current-use descriptor custody is POSIX-only and fails closed before trust use.
    # Keep importability on unsupported platforms without consulting HOME.
    HOST_ROOT = Path("/__pursuit_portfolio_unsupported_host_root__")
HOST_KEY_PATH = HOST_ROOT / "authority-key.json"
HOST_FLOOR_PATH = HOST_ROOT / "authority-floor.json"
HOST_SEAL_SCHEMA = "pursuit-portfolio-allocation/host-seal/v2"
_SHA = re.compile(r"^[0-9a-f]{64}$")
_HOST_SEAL_KEYS = frozenset(
    {
        "authority_floor_generation",
        "authority_floor_sha256",
        "authority_sha256",
        "current_receipt_sha256",
        "evaluated_at",
        "hmac_sha256",
        "input_sha256",
        "key_id",
        "markdown_sha256",
        "receipt_file_sha256",
        "result_sha256",
        "schema",
    }
)
_HOST_KEY_KEYS = frozenset({"schema", "key_id", "key_hex"})
_HOST_FLOOR_KEYS = frozenset(
    {
        "authority_sha256",
        "generation",
        "hmac_sha256",
        "key_id",
        "schema",
        "updated_at",
    }
)


@dataclass(frozen=True)
class HostAuthorizedPortfolio:
    authorized: AuthorizedPortfolio
    host_seal: dict[str, Any]
    host_seal_bytes: bytes


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _open_validated_host_parent(path: Path, where: str) -> int:
    """Return the exact parent directory descriptor generation authorized for use."""
    try:
        fd = _open_dir_chain(path.parent)
    except OSError as exc:
        raise PortfolioError(f"{where}: retained host directory unavailable") from exc
    try:
        info = os.fstat(fd)
        if os.name == "posix":
            if int(info.st_uid) != int(os.geteuid()):
                raise PortfolioError(f"{where}: retained host directory ownership mismatch")
            if stat.S_IMODE(info.st_mode) & 0o022:
                raise PortfolioError(
                    f"{where}: retained host directory must not be group/world writable"
                )
        return fd
    except Exception:
        os.close(fd)
        raise


def _leaf_guard(info: os.stat_result) -> tuple[int, ...]:
    return (
        int(info.st_dev),
        int(info.st_ino),
        int(info.st_mode),
        int(info.st_uid),
        int(info.st_gid),
        int(info.st_nlink),
        int(info.st_size),
        int(getattr(info, "st_mtime_ns", int(info.st_mtime * 1_000_000_000))),
        int(getattr(info, "st_ctime_ns", int(info.st_ctime * 1_000_000_000))),
    )


def _read_host_leaf(dir_fd: int, name: str, maximum: int, where: str) -> bytes:
    """Read one private host leaf from the already-validated retained parent."""
    if os.sep in name or (os.altsep and os.altsep in name) or name in (".", ".."):
        raise PortfolioError(f"{where}: invalid final path component")
    flags = os.O_RDONLY | os.O_NOFOLLOW
    try:
        fd = os.open(name, flags, dir_fd=dir_fd)
    except OSError as exc:
        raise PortfolioError(f"{where}: retained host file unavailable") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise PortfolioError(f"{where}: regular file required")
        if before.st_size < 0 or before.st_size > maximum:
            raise PortfolioError(f"{where}: file exceeds byte bound")
        if os.name == "posix":
            if int(before.st_uid) != int(os.geteuid()):
                raise PortfolioError(f"{where}: effective-owner file required")
            if stat.S_IMODE(before.st_mode) & 0o077:
                raise PortfolioError(f"{where}: owner-only permissions required")
            if int(before.st_nlink) != 1:
                raise PortfolioError(f"{where}: single-link retained file required")
        guard = _leaf_guard(before)
        raw = _read_fd_twice(fd, maximum, where)
        after = os.fstat(fd)
        if guard != _leaf_guard(after):
            raise PortfolioError(f"{where}: retained file metadata changed while reading")
        return raw
    finally:
        os.close(fd)


def _parse_host_key(raw: bytes) -> AuthorityKey:
    value = load_json_bytes(raw, "authority key")
    if type(value) is not dict or set(value) != set(_HOST_KEY_KEYS):
        raise PortfolioError("authority key: exact key set required")
    if value["schema"] != KEY_SCHEMA:
        raise PortfolioError("authority key: unsupported schema")
    key_id = _token(value["key_id"], "authority key.key_id")
    key_hex = _sha(value["key_hex"], "authority key.key_hex")
    key = bytes.fromhex(key_hex)
    if len(key) != 32:
        raise PortfolioError("authority key: exactly 32 bytes required")
    return AuthorityKey(key_id=key_id, key=key)


def _floor_unsigned(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "authority_sha256": value["authority_sha256"],
        "generation": value["generation"],
        "key_id": value["key_id"],
        "schema": value["schema"],
        "updated_at": value["updated_at"],
    }


def _parse_host_floor(raw: bytes, key: AuthorityKey) -> AuthorityFloor:
    value = load_json_bytes(raw, "authority floor")
    if type(value) is not dict or set(value) != set(_HOST_FLOOR_KEYS):
        raise PortfolioError("authority floor: exact key set required")
    if value["schema"] != FLOOR_SCHEMA:
        raise PortfolioError("authority floor: unsupported schema")
    key_id = _token(value["key_id"], "authority floor.key_id")
    generation = value["generation"]
    if type(generation) is not int or type(generation) is bool or not (1 <= generation <= 10**12):
        raise PortfolioError("authority floor.generation: positive bounded integer required")
    updated_at = value["updated_at"]
    _dt(updated_at, "authority floor.updated_at")
    normalized = {
        "authority_sha256": _sha(
            value["authority_sha256"], "authority floor.authority_sha256"
        ),
        "generation": generation,
        "hmac_sha256": _sha(value["hmac_sha256"], "authority floor.hmac_sha256"),
        "key_id": key_id,
        "schema": FLOOR_SCHEMA,
        "updated_at": updated_at,
    }
    if raw != _canonical(normalized):
        raise PortfolioError("authority floor: persisted bytes must be canonical JSON")
    if normalized["key_id"] != key.key_id:
        raise PortfolioError("authority floor: key_id mismatch")
    if _dt(normalized["updated_at"], "authority floor.updated_at") > _dt(
        _now(), "trusted_now"
    ):
        raise PortfolioError("authority floor: future-updated generation")
    expected = hmac.new(
        key.key, _canonical(_floor_unsigned(normalized)), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(normalized["hmac_sha256"], expected):
        raise PortfolioError("authority floor: HMAC mismatch")
    return AuthorityFloor(
        authority_sha256=normalized["authority_sha256"],
        generation=normalized["generation"],
        key_id=normalized["key_id"],
        updated_at=normalized["updated_at"],
        value=normalized,
        raw=raw,
    )


def _load_host_key() -> AuthorityKey:
    parent_fd = _open_validated_host_parent(HOST_KEY_PATH, "authority key")
    try:
        raw = _read_host_leaf(
            parent_fd, HOST_KEY_PATH.name, MAX_KEY_BYTES, "authority key"
        )
        return _parse_host_key(raw)
    finally:
        os.close(parent_fd)


def _load_host_floor(key: AuthorityKey) -> AuthorityFloor:
    parent_fd = _open_validated_host_parent(HOST_FLOOR_PATH, "authority floor")
    try:
        raw = _read_host_leaf(
            parent_fd, HOST_FLOOR_PATH.name, MAX_FLOOR_BYTES, "authority floor"
        )
        return _parse_host_floor(raw, key)
    finally:
        os.close(parent_fd)


def _seal_base(
    value: AuthorizedPortfolio, key: AuthorityKey, floor: AuthorityFloor
) -> dict[str, Any]:
    return {
        "authority_floor_generation": floor.generation,
        "authority_floor_sha256": _digest(floor.raw),
        "authority_sha256": _digest(value.authority_bytes),
        "current_receipt_sha256": _digest(value.current_receipt_bytes),
        "evaluated_at": value.compiled.result["evaluated_at"],
        "input_sha256": value.compiled.result["input_sha256"],
        "key_id": key.key_id,
        "markdown_sha256": _digest(value.compiled.markdown_bytes),
        "receipt_file_sha256": _digest(value.compiled.receipt_bytes),
        "result_sha256": _digest(value.compiled.result_bytes),
        "schema": HOST_SEAL_SCHEMA,
    }


def _seal(
    value: AuthorizedPortfolio, key: AuthorityKey, floor: AuthorityFloor
) -> dict[str, Any]:
    base = _seal_base(value, key, floor)
    return {
        **base,
        "hmac_sha256": hmac.new(key.key, _canonical(base), hashlib.sha256).hexdigest(),
    }


def _same_floor(before: AuthorityFloor, after: AuthorityFloor) -> None:
    if not hmac.compare_digest(before.raw, after.raw):
        raise PortfolioError("authority floor: generation changed during current-use operation")


def compile_current(
    source: Mapping[str, Any], authority: Mapping[str, Any]
) -> HostAuthorizedPortfolio:
    """Compile under fixed host key and the retained latest-authority floor."""
    key = _load_host_key()
    authorized = compile_authorized_current(source, authority, key)

    # The floor is deliberately acquired after candidate/authority parsing. A
    # concurrent supersession that lands before this point wins. We reacquire
    # again after sealing so a floor move during the operation fails closed.
    floor_before = _load_host_floor(key)
    require_current_authority(floor_before, authorized.authority_bytes)
    host_seal = _seal(authorized, key, floor_before)
    floor_after = _load_host_floor(key)
    _same_floor(floor_before, floor_after)
    require_current_authority(floor_after, authorized.authority_bytes)

    return HostAuthorizedPortfolio(
        authorized=authorized,
        host_seal=host_seal,
        host_seal_bytes=_canonical(host_seal),
    )


def _parse_host_seal(raw: bytes) -> dict[str, Any]:
    value = load_json_bytes(raw, "host seal")
    if type(value) is not dict or set(value) != set(_HOST_SEAL_KEYS):
        raise PortfolioError("host seal: exact key set required")
    if value["schema"] != HOST_SEAL_SCHEMA:
        raise PortfolioError("host seal: unsupported schema")
    if type(value["key_id"]) is not str or not value["key_id"]:
        raise PortfolioError("host seal: key_id required")
    if type(value["evaluated_at"]) is not str or not value["evaluated_at"]:
        raise PortfolioError("host seal: evaluated_at required")
    generation = value["authority_floor_generation"]
    if type(generation) is not int or type(generation) is bool or not (1 <= generation <= 10**12):
        raise PortfolioError("host seal: invalid authority_floor_generation")
    for name in (
        "authority_floor_sha256",
        "authority_sha256",
        "current_receipt_sha256",
        "hmac_sha256",
        "input_sha256",
        "markdown_sha256",
        "receipt_file_sha256",
        "result_sha256",
    ):
        if type(value[name]) is not str or _SHA.fullmatch(value[name]) is None:
            raise PortfolioError(f"host seal: invalid {name}")
    return value


def verify_current(
    result_raw: bytes,
    markdown_raw: bytes,
    receipt_raw: bytes,
    authority_raw: bytes,
    current_receipt_raw: bytes,
    host_seal_raw: bytes,
) -> dict[str, Any]:
    """Verify retained authority currentness, host seal, history, and fresh state."""
    key = _load_host_key()
    floor_before = _load_host_floor(key)
    require_current_authority(floor_before, authority_raw)

    seal = _parse_host_seal(host_seal_raw)
    if seal["key_id"] != key.key_id:
        raise PortfolioError("host seal: key_id mismatch")
    result = load_json_bytes(result_raw, "result")
    expected_bindings = {
        "authority_floor_generation": floor_before.generation,
        "authority_floor_sha256": _digest(floor_before.raw),
        "authority_sha256": _digest(authority_raw),
        "current_receipt_sha256": _digest(current_receipt_raw),
        "evaluated_at": result.get("evaluated_at"),
        "input_sha256": result.get("input_sha256"),
        "key_id": key.key_id,
        "markdown_sha256": _digest(markdown_raw),
        "receipt_file_sha256": _digest(receipt_raw),
        "result_sha256": _digest(result_raw),
        "schema": HOST_SEAL_SCHEMA,
    }
    base = {name: seal[name] for name in expected_bindings}
    if base != expected_bindings:
        raise PortfolioError("host seal: exact compiled-generation/current-floor binding mismatch")
    expected_mac = hmac.new(key.key, _canonical(base), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(seal["hmac_sha256"], expected_mac):
        raise PortfolioError("host seal: HMAC mismatch")

    verified = verify_authorized_current(
        result_raw,
        markdown_raw,
        receipt_raw,
        authority_raw,
        current_receipt_raw,
        key,
    )

    floor_after = _load_host_floor(key)
    _same_floor(floor_before, floor_after)
    require_current_authority(floor_after, authority_raw)
    return {
        **verified,
        "authority_floor_generation": floor_after.generation,
        "authority_floor_sha256": _digest(floor_after.raw),
        "host_seal_sha256": _digest(host_seal_raw),
        "host_seal_verified": True,
    }
