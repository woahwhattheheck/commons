#!/usr/bin/env python3
"""Canonical right-now revenue compiler with bound external authorities.

The frozen core preserves the historical compiler and replay contracts. Current
checkout truth is authorized only by a fresh Stripe readback emitted by a fixed,
host-owned collector outside the repository trust domain. Human reply and
scope-acceptance truth is compiled from canonical repository evidence and its
exact source generation is bound into the final control manifest.
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

from host import right_now_human_authority, right_now_revenue_core as _core


for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)


CHECKOUT_CURRENT_PATH = ROOT / "revenue" / "right_now" / "stripe_checkout_current.json"
CHECKOUT_CURRENT_MAX_AGE = timedelta(hours=24)
CHECKOUT_CURRENT_COLLECTOR = Path("/usr/local/libexec/commons-stripe-current-readback")
CHECKOUT_CURRENT_COLLECTOR_TIMEOUT_SECONDS = 10

# Several hostile tests load this wrapper under distinct module names in one
# process. Preserve the true core functions exactly once so later wrapper loads
# cannot capture another wrapper as their historical implementation.
_SENTINEL_CHECKOUT = "_commons_right_now_historical_validate_checkout_authority"
_SENTINEL_CATALOG = "_commons_right_now_historical_validate_catalog"
_SENTINEL_BUILD = "_commons_right_now_original_build_control"
_SENTINEL_LOCK = "_commons_right_now_build_lock"
if not hasattr(_core, _SENTINEL_CHECKOUT):
    setattr(_core, _SENTINEL_CHECKOUT, _core.validate_checkout_authority)
if not hasattr(_core, _SENTINEL_CATALOG):
    setattr(_core, _SENTINEL_CATALOG, _core.validate_catalog)
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


def validate_current_checkout_readback(
    value: dict[str, Any],
    *,
    current_moment: datetime,
) -> dict[str, Any]:
    """Validate a credential-host Stripe readback against process time."""

    _exact_keys(
        value,
        {
            "schema_version",
            "account_id",
            "livemode",
            "observed_at_utc",
            "payment_link",
            "line_item",
            "line_item_count",
            "line_items_has_more",
            "source",
        },
        "checkout current readback",
    )
    if value["schema_version"] != "commons-stripe-checkout-readback/v2":
        raise ControlError("checkout current readback schema drift")
    if value["account_id"] != CHECKOUT_AUTHORITY["provider_account_id"]:
        raise ControlError("checkout current readback account drift")
    if value["livemode"] is not True:
        raise ControlError("checkout current readback must be livemode")

    source = _exact_keys(
        value["source"],
        {
            "authenticated_read",
            "collector",
            "payment_link_operation",
            "line_items_operation",
        },
        "checkout current source",
    )
    if source["authenticated_read"] is not True:
        raise ControlError("checkout current readback lacks authenticated provider authority")
    if source["collector"] != "STRIPE_API_READ":
        raise ControlError("checkout current readback collector drift")
    if source["payment_link_operation"] != "GET /v1/payment_links/{id}":
        raise ControlError("checkout current payment-link operation drift")
    if source["line_items_operation"] != "GET /v1/payment_links/{id}/line_items":
        raise ControlError("checkout current line-items operation drift")

    payment_link = _exact_keys(
        value["payment_link"],
        {"id", "active", "livemode", "currency", "url", "offer_id", "contract_version"},
        "checkout current payment_link",
    )
    expected_link = {
        "id": CHECKOUT_AUTHORITY["provider_payment_link_id"],
        "active": True,
        "livemode": True,
        "currency": "usd",
        "url": CHECKOUT_AUTHORITY["payment_url"],
        "offer_id": CHECKOUT_AUTHORITY["offer_id"],
        "contract_version": "commons-agent-failure-autopsy-offer/v1",
    }
    for field, expected in expected_link.items():
        if payment_link[field] != expected:
            raise ControlError(f"checkout current payment_link {field} drift")

    if type(value["line_item_count"]) is not int or value["line_item_count"] != 1:
        raise ControlError("checkout current line-item count drift")
    if value["line_items_has_more"] is not False:
        raise ControlError("checkout current line-items pagination is incomplete")

    line_item = _exact_keys(
        value["line_item"],
        {
            "price_id",
            "price_active",
            "livemode",
            "product_id",
            "currency",
            "unit_amount",
            "quantity",
            "lookup_key",
        },
        "checkout current line_item",
    )
    expected_line_item = {
        "price_id": CHECKOUT_AUTHORITY["provider_price_id"],
        "price_active": True,
        "livemode": True,
        "product_id": CHECKOUT_AUTHORITY["provider_product_id"],
        "currency": "usd",
        "unit_amount": CHECKOUT_AUTHORITY["amount"] * 100,
        "quantity": 1,
        "lookup_key": "commons_agent_failure_autopsy_usd29_v1",
    }
    for field, expected in expected_line_item.items():
        actual = line_item[field]
        if field in {"unit_amount", "quantity"}:
            if type(actual) is not int or actual != expected:
                raise ControlError(f"checkout current line_item {field} drift")
        elif actual != expected:
            raise ControlError(f"checkout current line_item {field} drift")

    observed_text = value["observed_at_utc"]
    observed = _provider_utc(observed_text, "checkout current observed_at_utc")
    if observed.strftime("%Y-%m-%dT%H:%M:%SZ") != observed_text:
        raise ControlError("checkout current observed_at_utc must be canonical UTC seconds")
    if not isinstance(current_moment, datetime):
        raise ControlError("checkout current process time must be a datetime")
    if (
        current_moment.tzinfo is None
        or current_moment.utcoffset() != timezone.utc.utcoffset(current_moment)
    ):
        raise ControlError("checkout current process time must be UTC")
    current_moment = current_moment.astimezone(timezone.utc)
    if observed > current_moment:
        raise ControlError("checkout current provider evidence is from the future")
    if current_moment - observed > CHECKOUT_CURRENT_MAX_AGE:
        raise ControlError("checkout current provider evidence is stale")

    return {
        "observed_at_utc": observed_text,
        "readback_sha256": _canonical_readback_sha256(value),
        "max_age_seconds": int(CHECKOUT_CURRENT_MAX_AGE.total_seconds()),
        "authority_boundary": "CREDENTIAL_HOST_STRIPE_READ",
    }


def build_checkout_authority(catalog_as_of: str) -> dict[str, Any]:
    """Require fresh credential-host truth plus historical integrity.

    Currentness is evaluated before retained chronology so stale live evidence
    cannot be masked by an unrelated historical catalog boundary failure.
    """

    try:
        public_page = AUTOPSY_PUBLIC_PAGE_PATH.read_text(encoding="utf-8")
    except OSError as error:
        raise ControlError(f"cannot read {AUTOPSY_PUBLIC_PAGE_PATH}: {error}") from error

    provider_readback = _credential_host_readback()
    current = validate_current_checkout_readback(
        provider_readback,
        current_moment=_current_utc(),
    )
    historical = _HISTORICAL_VALIDATE_CHECKOUT_AUTHORITY(
        read_object(AUTOPSY_PROVIDER_PATH),
        public_page,
        catalog_as_of,
    )

    result = dict(historical)
    result["current_observed_at_utc"] = current["observed_at_utc"]
    result["current_readback_sha256"] = current["readback_sha256"]
    result["current_max_age_seconds"] = current["max_age_seconds"]
    result["current_authority_boundary"] = current["authority_boundary"]
    return result


def validate_catalog(
    catalog: dict[str, Any],
    checkout_authority: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate catalog truth against freshly recomputed provider authority.

    ``checkout_authority`` remains in the signature for source compatibility,
    but is intentionally not trusted. A caller cannot preserve ACTIVE by
    passing a historical, fabricated, or repo-retained authority object.
    """

    if checkout_authority is not None and not isinstance(checkout_authority, dict):
        raise ControlError("checkout authority override must be an object")
    current = build_checkout_authority(catalog.get("as_of"))
    return _HISTORICAL_VALIDATE_CATALOG(catalog, current)


def _source_entry(value: Any, where: str) -> tuple[str, str]:
    if type(value) is not dict or set(value) != {"path", "sha256"}:
        raise ControlError(f"{where} must contain exact path and sha256 fields")
    path = value["path"]
    digest = value["sha256"]
    if (
        not isinstance(path, str)
        or not path
        or path.startswith("/")
        or "\\" in path
        or any(part in {"", ".", ".."} for part in path.split("/"))
    ):
        raise ControlError(f"{where}.path must be a canonical repository-relative path")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ControlError(f"{where}.sha256 must be lowercase SHA-256")
    return path, digest


def _bind_human_truth(control: Any) -> dict[str, Any]:
    """Bind canonical reply evidence into the current control generation."""

    if type(control) is not dict:
        raise ControlError("right-now control must be an exact object")
    if control.get("schema_version") != SCHEMA_VERSION:
        raise ControlError("right-now control schema version drift")
    if control.get("kind") != "RIGHT_NOW_REVENUE_CONTROL":
        raise ControlError("right-now control kind drift")
    truth = control.get("truth")
    if type(truth) is not dict:
        raise ControlError("right-now control truth must be an exact object")
    catalog_assertions = {
        "verified_positive_replies": truth.get("verified_positive_replies"),
        "accepted_scopes": truth.get("accepted_scopes"),
    }
    try:
        human_truth = right_now_human_authority.derive_human_truth(catalog_assertions)
    except right_now_human_authority.HumanOutcomeAuthorityError as error:
        raise ControlError(f"human-outcome authority failed: {error}") from error

    result = dict(control)
    result_truth = dict(truth)
    result_truth["verified_positive_replies"] = human_truth[
        "verified_positive_replies"
    ]
    result_truth["accepted_scopes"] = human_truth["accepted_scopes"]
    result["truth"] = result_truth

    blockers = control.get("blockers")
    if type(blockers) is not list:
        raise ControlError("right-now control blockers must be an exact array")
    rebound_blockers: list[dict[str, Any]] = []
    buyer_acceptance_count = 0
    for index, blocker in enumerate(blockers):
        if type(blocker) is not dict:
            raise ControlError(
                f"right-now control blockers[{index}] must be an exact object"
            )
        rebound = dict(blocker)
        if rebound.get("id") == "BUYER_ACCEPTANCE":
            buyer_acceptance_count += 1
            rebound["current"] = human_truth["accepted_scopes"]
        rebound_blockers.append(rebound)
    if buyer_acceptance_count != 1:
        raise ControlError(
            "right-now control must contain exactly one BUYER_ACCEPTANCE blocker"
        )
    result["blockers"] = rebound_blockers

    result["as_of"] = _latest_as_of(
        control.get("as_of"),
        human_truth["measured_at"],
    )

    existing_sources = control.get("source_receipts")
    if type(existing_sources) is not list:
        raise ControlError("right-now control source_receipts must be an exact array")
    merged_sources: list[dict[str, str]] = []
    source_digests: dict[str, str] = {}
    for index, entry in enumerate(existing_sources):
        path, digest = _source_entry(
            entry, f"right-now control source_receipts[{index}]"
        )
        previous = source_digests.get(path)
        if previous is not None:
            if previous != digest:
                raise ControlError(f"source digest conflict for {path}")
            raise ControlError(
                f"duplicate source path in right-now control: {path}"
            )
        source_digests[path] = digest
        merged_sources.append({"path": path, "sha256": digest})

    human_sources = human_truth.get("sources")
    if type(human_sources) is not list or not human_sources:
        raise ControlError("human-outcome sources must be a non-empty exact array")
    seen_human_paths: set[str] = set()
    for index, entry in enumerate(human_sources):
        path, digest = _source_entry(entry, f"human-outcome sources[{index}]")
        if path in seen_human_paths:
            raise ControlError(f"duplicate human-outcome source path: {path}")
        seen_human_paths.add(path)
        previous = source_digests.get(path)
        if previous is not None:
            if previous != digest:
                raise ControlError(f"source digest conflict for {path}")
            continue
        source_digests[path] = digest
        merged_sources.append({"path": path, "sha256": digest})
    result["source_receipts"] = merged_sources
    return result


def _compile_core_control() -> dict[str, Any]:
    """Run the frozen core with this module's authority hooks in isolation."""

    with _CORE_BUILD_LOCK:
        previous_checkout = _core.build_checkout_authority
        previous_catalog = _core.validate_catalog
        try:
            _core.build_checkout_authority = build_checkout_authority
            _core.validate_catalog = validate_catalog
            return _ORIGINAL_BUILD_CONTROL()
        finally:
            _core.build_checkout_authority = previous_checkout
            _core.validate_catalog = previous_catalog


def build_control() -> dict[str, Any]:
    """Compile current checkout truth and bind canonical human outcomes."""

    return _bind_human_truth(_compile_core_control())


with _CORE_BUILD_LOCK:
    _core.build_checkout_authority = build_checkout_authority
    _core.validate_catalog = validate_catalog
    _core.build_control = build_control
validate_checkout_authority = _HISTORICAL_VALIDATE_CHECKOUT_AUTHORITY


if __name__ == "__main__":
    raise SystemExit(_core.main())
