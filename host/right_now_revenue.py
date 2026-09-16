#!/usr/bin/env python3
"""Canonical right-now revenue compiler with credential-host Stripe authority.

The frozen core preserves the historical compiler and replay contracts. Current
checkout truth is authorized only by a fresh Stripe readback emitted by a fixed,
host-owned collector outside the repository trust domain. Repository-retained
receipts remain audit evidence only and cannot mint current provider truth.
Human reply and scope-acceptance truth is captured from one canonical source
generation and bound into the final control manifest.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from host import right_now_human_authority
from host import right_now_revenue_core as _core


for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)


CHECKOUT_CURRENT_PATH = ROOT / "revenue" / "right_now" / "stripe_checkout_current.json"
CHECKOUT_CURRENT_MAX_AGE = timedelta(hours=24)
CHECKOUT_CURRENT_COLLECTOR = Path("/usr/local/libexec/commons-stripe-current-readback")
CHECKOUT_CURRENT_COLLECTOR_TIMEOUT_SECONDS = 10

# Hostile tests exec this wrapper under distinct module names in one process.
# Preserve the true core functions and a shared re-entrant lock exactly once
# so later copies cannot capture a sibling wrapper as historical, recurse
# through an unmocked collector, or race hook assignment.
# Pin names match the existing unwrapped-core sentinels on main.
_SENTINEL_CHECKOUT = "_UNWRAPPED_VALIDATE_CHECKOUT_AUTHORITY"
_SENTINEL_CATALOG = "_UNWRAPPED_VALIDATE_CATALOG"
_SENTINEL_BUILD_CHECKOUT = "_UNWRAPPED_BUILD_CHECKOUT_AUTHORITY"
_SENTINEL_BUILD = "_UNWRAPPED_BUILD_CONTROL"
_SENTINEL_LOCK = "_commons_right_now_build_lock"
if not hasattr(_core, _SENTINEL_CHECKOUT):
    setattr(_core, _SENTINEL_CHECKOUT, _core.validate_checkout_authority)
if not hasattr(_core, _SENTINEL_CATALOG):
    setattr(_core, _SENTINEL_CATALOG, _core.validate_catalog)
if not hasattr(_core, _SENTINEL_BUILD_CHECKOUT):
    setattr(_core, _SENTINEL_BUILD_CHECKOUT, _core.build_checkout_authority)
if not hasattr(_core, _SENTINEL_BUILD):
    setattr(_core, _SENTINEL_BUILD, _core.build_control)
if not hasattr(_core, _SENTINEL_LOCK):
    setattr(_core, _SENTINEL_LOCK, threading.RLock())

_HISTORICAL_VALIDATE_CHECKOUT_AUTHORITY = getattr(_core, _SENTINEL_CHECKOUT)
_HISTORICAL_VALIDATE_CATALOG = getattr(_core, _SENTINEL_CATALOG)
_ORIGINAL_BUILD_CONTROL = getattr(_core, _SENTINEL_BUILD)
_CORE_BUILD_LOCK = getattr(_core, _SENTINEL_LOCK)


def _current_utc() -> datetime:
    """Return the production freshness clock; callers cannot supply it."""

    return datetime.now(timezone.utc)


def _exact_keys(value: Any, expected: set[str], where: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ControlError(f"{where} fields differ from the current checkout contract")
    return value


def _canonical_readback_sha256(value: dict[str, Any]) -> str:
    """Hash the semantic readback, independent of collector JSON whitespace."""

    encoded = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _credential_host_readback() -> dict[str, Any]:
    """Read Stripe truth from the fixed credential-owning host collector.

    The collector path is intentionally absolute and has no caller/env override.
    Deployment owns that executable and its Stripe credentials outside this
    repository. Missing, failing, noisy, or malformed collectors fail closed.
    """

    try:
        result = subprocess.run(
            [str(CHECKOUT_CURRENT_COLLECTOR)],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
            timeout=CHECKOUT_CURRENT_COLLECTOR_TIMEOUT_SECONDS,
            env={},
        )
    except (FileNotFoundError, PermissionError, OSError, subprocess.TimeoutExpired) as error:
        raise ControlError("checkout current credential-host collector unavailable") from error

    if result.returncode != 0:
        raise ControlError("checkout current credential-host collector failed")
    if result.stderr:
        raise ControlError("checkout current credential-host collector emitted stderr")
    if len(result.stdout.encode("utf-8")) > 65536:
        raise ControlError("checkout current credential-host collector output is too large")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ControlError("checkout current credential-host collector output must be JSON") from error
    if not isinstance(value, dict):
        raise ControlError("checkout current credential-host collector must emit one JSON object")
    return value
