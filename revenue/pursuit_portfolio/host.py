"""Production host authority for pursuit-portfolio current-use operations.

Production has two fixed, non-candidate-selected host resources:

* the HMAC key authenticates upstream positive authority and the full package;
* the separately retained latest-authority floor names the only authority digest
  that is current now.

The second resource is what makes revocation/supersession real: an old valid HMAC
is historical evidence only once the retained floor advances.

On POSIX the trust root is derived from the effective account database entry,
never from HOME/Path.home() or another caller-controlled environment selector.
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
    AuthorizedPortfolio,
    AuthorityKey,
    _canonical,
    _open_dir_chain,
    compile_authorized_current,
    load_authority_key,
    verify_authorized_current,
)
from .floor import AuthorityFloor, load_authority_floor, require_current_authority


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


@dataclass(frozen=True)
class HostAuthorizedPortfolio:
    authorized: AuthorizedPortfolio
    host_seal: dict[str, Any]
    host_seal_bytes: bytes


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _validate_host_parent(path: Path, where: str) -> None:
    """Validate the retained parent generation used for one fixed host file."""
    try:
        fd = _open_dir_chain(path.parent)
    except OSError as exc:
        raise PortfolioError(f"{where}: retained host directory unavailable") from exc
    try:
        info = os.fstat(fd)
    finally:
        os.close(fd)
    if os.name == "posix":
        if int(info.st_uid) != int(os.geteuid()):
            raise PortfolioError(f"{where}: retained host directory ownership mismatch")
        if stat.S_IMODE(info.st_mode) & 0o022:
            raise PortfolioError(
                f"{where}: retained host directory must not be group/world writable"
            )


def _load_host_key() -> AuthorityKey:
    _validate_host_parent(HOST_KEY_PATH, "authority key")
    return load_authority_key(HOST_KEY_PATH)


def _load_host_floor(key: AuthorityKey) -> AuthorityFloor:
    _validate_host_parent(HOST_FLOOR_PATH, "authority floor")
    return load_authority_floor(HOST_FLOOR_PATH, key)


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
