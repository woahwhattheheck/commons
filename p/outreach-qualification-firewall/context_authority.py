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


def _load_context_key() -> bytes | None:
    raw = os.environ.get(CONTEXT_AUTHORITY_ENV)
    if raw is None:
        return None
    if type(raw) is not str or not _HEX64_RE.fullmatch(raw):
        raise FirewallError(f"{CONTEXT_AUTHORITY_ENV} must be 32-byte lowercase hex")
    return bytes.fromhex(raw)


_PROCESS_CONTEXT_AUTHORITY_KEY = _load_context_key()


def _make_context_authority(
    key: bytes | None,
    hmac_new,
    compare_digest,
    sha256,
    canonical,
    domain: str,
):
    def message(kind: str, payload: dict[str, Any]) -> bytes:
        return canonical({"domain": domain, "kind": kind, "payload": payload})

    def verify(kind: str, payload: dict[str, Any], tag_hex: str) -> bool:
        if key is None:
            return False
        expected = hmac_new(key, message(kind, payload), sha256).hexdigest()
        return compare_digest(expected, tag_hex)

    return message, verify


context_authority_message, verify_context_authority = _make_context_authority(
    _PROCESS_CONTEXT_AUTHORITY_KEY,
    hmac.new,
    hmac.compare_digest,
    hashlib.sha256,
    canonical_json,
    _CONTEXT_DOMAIN,
)

del _make_context_authority
