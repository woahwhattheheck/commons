from __future__ import annotations

import hashlib
import hmac
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import pwd
except ImportError:  # pragma: no cover - non-POSIX fails closed in production
    pwd = None

from .engine import DealEconomicsError, canonical_json, compile_report, digest, parse_strict_json

AUTHORITY_SCHEMA = "commons.service-deal-economics.authority/v1"
FLOOR_SCHEMA = "commons.service-deal-economics.authority-floor/v1"
KEY_SCHEMA = "commons.service-deal-economics.authority-key/v1"
CURRENT_SCHEMA = "commons.service-deal-economics.current-report/v2"
CURRENT_VERIFY_SCHEMA = "commons.service-deal-economics.authority-verification/v3"
READY = "READY_FOR_OWNER_QUOTE_REVIEW"
AUTHORITY_HOLD = "HOLD_INPUT_AUTHORITY_UNVERIFIED"
MAX_HOST_BYTES = 128 * 1024


class AuthorityError(DealEconomicsError):
    pass


def _fixed_host_root() -> Path:
    if os.name != "posix" or pwd is None:
        raise AuthorityError("fixed-host authority requires POSIX account semantics")
    try:
        home = pwd.getpwuid(os.getuid()).pw_dir
    except (KeyError, OSError) as exc:
        raise AuthorityError("cannot resolve fixed OS-account home") from exc
    return Path(home) / ".config" / "commons" / "service-deal-economics"


def _host_paths() -> tuple[Path, Path, Path]:
    root = _fixed_host_root()
    return root / "authority-key.json", root / "current-authority.json", root / "authority-floor.json"


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise AuthorityError(f"{label} must be lowercase SHA-256 hex")
    return value


def _generation(value: Any, label: str) -> int:
    if type(value) is not int or not 1 <= value <= 1_000_000_000:
        raise AuthorityError(f"{label} must be a positive bounded integer")
    return value


def _utc(value: Any, label: str) -> datetime:
    if type(value) is not str:
        raise AuthorityError(f"{label} must be canonical UTC")
    try:
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise AuthorityError(f"{label} must be canonical whole-second UTC") from exc
    if dt.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise AuthorityError(f"{label} must be canonical whole-second UTC")
    return dt


def _utc_text(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise AuthorityError("trusted current time must be timezone-aware")
    return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _process_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def authority_subject(packet: Any) -> dict[str, str]:
    if type(packet) is not dict or any(type(packet.get(k)) is not dict for k in ("policy", "deal", "capacity")):
        raise AuthorityError("packet must contain policy, deal, and capacity objects")
    deal_basis = dict(packet["deal"])
    if "target_price_cents" not in deal_basis:
        raise AuthorityError("deal.target_price_cents missing")
    deal_basis.pop("target_price_cents")
    return {
        "policy_sha256": digest(packet["policy"]),
        "scope_cost_sha256": digest(deal_basis),
        "capacity_sha256": digest(packet["capacity"]),
    }
