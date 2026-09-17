from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

from firewall_codec import FirewallError, canonical_json

WRITER_AUTHORITY_ENV = "OUTREACH_WRITER_LEASE_AUTHORITY_KEY_HEX"
_SIGNED_FIELDS = (
    "lease_id",
    "collision_key",
    "seat",
    "session_nonce",
    "issued_at",
    "expires_at",
    "status",
)


def _load_key(_getenv=os.environ.get) -> bytes | None:
    raw = _getenv(WRITER_AUTHORITY_ENV)
    if raw is None:
        return None
    if len(raw) != 64 or any(ch not in "0123456789abcdef" for ch in raw):
        raise FirewallError(f"{WRITER_AUTHORITY_ENV} must be 32-byte lowercase hex")
    return bytes.fromhex(raw)


_PROCESS_WRITER_AUTHORITY_KEY = _load_key()
_HMAC_NEW = hmac.new
_COMPARE_DIGEST = hmac.compare_digest
_SHA256 = hashlib.sha256


def writer_lease_message(row: dict[str, Any]) -> bytes:
    return canonical_json({field: row[field] for field in _SIGNED_FIELDS})


def verify_writer_lease_authority(
    row: dict[str, Any],
    *,
    _key: bytes | None = _PROCESS_WRITER_AUTHORITY_KEY,
    _hmac_new=_HMAC_NEW,
    _compare_digest=_COMPARE_DIGEST,
    _sha256=_SHA256,
) -> bool:
    if _key is None:
        return False
    expected = _hmac_new(_key, writer_lease_message(row), _sha256).hexdigest()
    return _compare_digest(expected, row["authority_tag_hex"])
