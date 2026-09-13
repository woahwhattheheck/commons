"""Production host authority for pursuit-portfolio current-use operations.

The trusted key location is not selected by candidate input or CLI arguments.
Production emits a second host HMAC seal over the exact compiled files plus the
full normalized input digest.  The upstream authority HMAC proves READY/CURABLE
provenance; the host seal prevents later reprioritization/capacity/effort edits
from being laundered through self-hashed deterministic engine receipts.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
from pathlib import Path
import re
from typing import Any, Mapping

from .core import PortfolioError, load_json_bytes
from .current import (
    AuthorizedPortfolio,
    AuthorityKey,
    _canonical,
    compile_authorized_current,
    load_authority_key,
    verify_authorized_current,
)

HOST_KEY_PATH = Path.home() / ".config" / "commons" / "pursuit-portfolio" / "authority-key.json"
HOST_SEAL_SCHEMA = "pursuit-portfolio-allocation/host-seal/v1"
_SHA = re.compile(r"^[0-9a-f]{64}$")
_HOST_SEAL_KEYS = frozenset(
    {
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


def _seal_base(value: AuthorizedPortfolio, key: AuthorityKey) -> dict[str, Any]:
    return {
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


def _seal(value: AuthorizedPortfolio, key: AuthorityKey) -> dict[str, Any]:
    base = _seal_base(value, key)
    return {
        **base,
        "hmac_sha256": hmac.new(key.key, _canonical(base), hashlib.sha256).hexdigest(),
    }


def compile_current(
    source: Mapping[str, Any], authority: Mapping[str, Any]
) -> HostAuthorizedPortfolio:
    """Compile and host-seal current-use evidence under the fixed authority."""
    key = load_authority_key(HOST_KEY_PATH)
    authorized = compile_authorized_current(source, authority, key)
    host_seal = _seal(authorized, key)
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
    for name in (
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
    """Verify the fixed-host seal, upstream authority, history, and fresh state."""
    key = load_authority_key(HOST_KEY_PATH)
    seal = _parse_host_seal(host_seal_raw)
    if seal["key_id"] != key.key_id:
        raise PortfolioError("host seal: key_id mismatch")
    result = load_json_bytes(result_raw, "result")
    expected_bindings = {
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
        raise PortfolioError("host seal: exact compiled-generation binding mismatch")
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
    return {
        **verified,
        "host_seal_sha256": _digest(host_seal_raw),
        "host_seal_verified": True,
    }
