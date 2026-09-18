from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

from firewall_codec import FirewallError

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


def _load_key() -> bytes | None:
    raw = os.environ.get(WRITER_AUTHORITY_ENV)
    if raw is None:
        return None
    if type(raw) is not str or len(raw) != 64 or any(ch not in "0123456789abcdef" for ch in raw):
        raise FirewallError(f"{WRITER_AUTHORITY_ENV} must be 32-byte lowercase hex")
    return bytes.fromhex(raw)


_PROCESS_WRITER_AUTHORITY_KEY = _load_key()


def _make_writer_authority(
    key: bytes | None,
    hmac_new,
    compare_digest,
    sha256,
    dumps,
    signed_fields: tuple[str, ...],
):
    fields = tuple(signed_fields)

    def message(row: dict[str, Any]) -> bytes:
        return dumps(
            {field: row[field] for field in fields},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def verify(row: dict[str, Any]) -> bool:
        if key is None:
            return False
        expected = hmac_new(key, message(row), sha256).hexdigest()
        return compare_digest(expected, row["authority_tag_hex"])

    return message, verify


writer_lease_message, verify_writer_lease_authority = _make_writer_authority(
    _PROCESS_WRITER_AUTHORITY_KEY,
    hmac.new,
    hmac.compare_digest,
    hashlib.sha256,
    json.dumps,
    _SIGNED_FIELDS,
)

del _make_writer_authority
