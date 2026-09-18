from __future__ import annotations

import hashlib
import hmac
import os
import re
from typing import Any

from firewall_codec import FirewallError, canonical_json

CONTEXT_AUTHORITY_ENV = "OUTREACH_CONTEXT_AUTHORITY_KEY_HEX"
_CONTEXT_DOMAIN = "outreach-qualification-firewall.context.v2"
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


def _load_context_key(
    _getenv=os.environ.get,
    _key_name=CONTEXT_AUTHORITY_ENV,
    _hex_re=_HEX64_RE,
    _type=type,
    _str_type=str,
    _fromhex=bytes.fromhex,
    _err=FirewallError,
) -> bytes | None:
    raw = _getenv(_key_name)
    if raw is None:
        return None
    if _type(raw) is not _str_type or not _hex_re.fullmatch(raw):
        raise _err(f"{_key_name} must be 32-byte lowercase hex")
    return _fromhex(raw)


_PROCESS_CONTEXT_AUTHORITY_KEY = _load_context_key()
_HMAC_NEW = hmac.new
_COMPARE_DIGEST = hmac.compare_digest
_SHA256 = hashlib.sha256


def context_authority_message(
    kind: str,
    payload: dict[str, Any],
    _canonical=canonical_json,
    _domain=_CONTEXT_DOMAIN,
) -> bytes:
    return _canonical({"domain": _domain, "kind": kind, "payload": payload})


def verify_context_authority(
    kind: str,
    payload: dict[str, Any],
    tag_hex: str,
    *,
    _key: bytes | None = _PROCESS_CONTEXT_AUTHORITY_KEY,
    _hmac_new=_HMAC_NEW,
    _compare=_COMPARE_DIGEST,
    _sha256=_SHA256,
    _message=context_authority_message,
) -> bool:
    if _key is None:
        return False
    expected = _hmac_new(_key, _message(kind, payload), _sha256).hexdigest()
    return _compare(expected, tag_hex)
