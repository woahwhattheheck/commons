"""One-shot terminal consumer for externally mutating outbound provider calls.

The module is deliberately provider-agnostic.  It does not grant send authority;
it consumes host-retained authority exactly once and serializes concurrent workers
at a Git ref before an external provider callback can run.
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

RESERVATION_SCHEMA = "outbound-send-consumer-reservation/v1"
OUTCOME_SCHEMA = "outbound-send-consumer-outcome/v1"
RECEIPT_SCHEMA = "outbound-send-consumer-receipt/v1"
INDETERMINATE_HTTP = frozenset({0, 408, 500, 502, 503, 504})
TERMINAL_STATES = frozenset({"SENT", "REJECTED", "OUTCOME_UNKNOWN", "HELD_AUTHORITY"})
_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9._:@/+\-]{1,191}$")
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
_HEX40_64_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


class ConsumerError(ValueError):
    """Structurally invalid input or provider coordination response."""


class ProviderRejected(RuntimeError):
    """Known provider rejection where the adapter can prove no send completed."""

    def __init__(self, reason_code: str = "provider_rejected") -> None:
        self.reason_code = _token(reason_code, "provider rejection reason")
        super().__init__(self.reason_code)


Transport = Callable[[str, str, Mapping[str, Any] | None], tuple[int, Any]]
AuthorityProbe = Callable[[], str | None]
ProviderCallback = Callable[[str], Any]


def _canon(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise ConsumerError("value is not canonical JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _token(value: Any, field: str) -> str:
    if not isinstance(value, str) or value != value.casefold() or not value.isascii():
        raise ConsumerError(f"{field}: lowercase ASCII machine token required")
    if _TOKEN_RE.fullmatch(value) is None:
        raise ConsumerError(f"{field}: malformed machine token")
    return value


def _display(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.isascii() or not (3 <= len(value) <= 192):
        raise ConsumerError(f"{field}: 3..192 ASCII chars required")
    if any(ord(ch) < 0x20 or ch == "\x7f" for ch in value):
        raise ConsumerError(f"{field}: control characters forbidden")
    return value


def _repo(value: Any) -> str:
    if not isinstance(value, str) or _REPO_RE.fullmatch(value) is None:
        raise ConsumerError("repo: owner/name required")
    # GitHub owner/name routing is case-insensitive. Fold before storage and
    # seam hashing so alias spellings share one reservation ref.
    owner, name = value.split("/", 1)
    return f"{owner.casefold()}/{name.casefold()}"
