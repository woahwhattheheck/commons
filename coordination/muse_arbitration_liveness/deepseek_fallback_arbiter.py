# SPDX-License-Identifier: MIT
"""DeepSeek fallback arbiter stub for underbound Muse CLEAR replies.

When Muse returns prose ``Cleared:`` / truncated / mismatched keys, peers may
mint a ledger-compatible DECISION evidence object from the *exact* REQUEST
tuple via this module. Meter: convert/ship and arbitration-clear only.
Does **not** send email, contact counterparties, or mutate providers.

Credentials: read from ``/workspace/shared-creds/deepseek.json`` (never print
the API key). Live HTTP calls are optional and gated; the default path is a
deterministic local mint so unit tests and fail-closed ledgers stay offline.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from .clear_reply import (
    REASON_OK,
    decision_event_from_parse,
    parse_clear_reply,
)

DEFAULT_CREDS_PATH = "/workspace/shared-creds/deepseek.json"
METER_SCOPE = frozenset({"convert_ship", "arbitration_clear"})
AUTHORITY_MODE = "DEEPSEEK_FALLBACK_EVIDENCE_MINT_ONLY_V1"


class DeepSeekFallbackError(ValueError):
    pass


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_deepseek_creds(path: str | Path = DEFAULT_CREDS_PATH) -> dict[str, Any]:
    """Load DeepSeek vault JSON. Never returns or logs the raw api_key to callers
    that print; returns a redacted view plus an internal handle.

    The ``api_key`` field is present in the returned dict for authenticated
    callers that intentionally perform a live call; do not print it.
    """
    p = Path(path)
    if not p.is_file():
        raise DeepSeekFallbackError(f"deepseek creds missing: {p}")
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeepSeekFallbackError("deepseek creds unreadable") from exc
    if type(raw) is not dict:
        raise DeepSeekFallbackError("deepseek creds must be an object")
    key = raw.get("api_key")
    if type(key) is not str or not key:
        raise DeepSeekFallbackError("deepseek api_key missing")
    return {
        "base_url": str(raw.get("base_url") or "https://api.deepseek.com"),
        "default_model": str(raw.get("default_model") or "deepseek-flash"),
        "budget_usd": raw.get("budget_usd"),
        "api_key": key,
        "api_key_fingerprint": _sha256_text(key)[:16],
        "meter_scope": sorted(METER_SCOPE),
        "authority_mode": AUTHORITY_MODE,
    }


def redacted_creds_summary(path: str | Path = DEFAULT_CREDS_PATH) -> dict[str, Any]:
    """Safe summary for logs/receipts (no secret material)."""
    creds = load_deepseek_creds(path)
    return {
        "base_url": creds["base_url"],
        "default_model": creds["default_model"],
        "budget_usd": creds["budget_usd"],
        "api_key_fingerprint": creds["api_key_fingerprint"],
        "meter_scope": creds["meter_scope"],
        "authority_mode": creds["authority_mode"],
        "creds_path": str(path),
    }


def mint_decision_from_request(
    request: Mapping[str, Any],
    *,
    decision: str = "SELECTED",
    provider_event_id: Optional[str] = None,
    observed_at: Optional[str] = None,
    writer_id: Optional[str] = None,
    hold_reason: Optional[str] = None,
    holders: Optional[str] = None,
    supersedes_provider_event_id: Optional[str] = None,
    source: str = "deepseek_fallback_local_mint",
) -> dict[str, Any]:
    """Mint a ledger-compatible DECISION event bound to the exact REQUEST tuple.

    Does not call DeepSeek HTTP, does not send email.
    """
    if decision not in {"SELECTED", "HOLD", "COLLISION"}:
        raise DeepSeekFallbackError("decision must be SELECTED|HOLD|COLLISION")
    for field in (
        "request_key",
        "seat_id",
        "counterparty_key",
        "route_sha256",
        "purpose_sha256",
        "retry_policy_generation",
    ):
        if field not in request or type(request[field]) is not str or not request[field]:
            raise DeepSeekFallbackError(f"request.{field} required")

    observed = observed_at or _utc_now()
    eid = provider_event_id or f"deepseek-fallback:{request['request_key']}:{observed}"
    event = {
        "type": "DECISION",
        "provider_event_id": eid,
        "provider_event_sha256": _sha256_text(eid),
        "observed_at": observed,
        "decision": decision,
        "bound_request_key": request["request_key"],
        "bound_seat_id": request["seat_id"],
        "bound_counterparty_key": request["counterparty_key"],
        "bound_route_sha256": request["route_sha256"],
        "bound_purpose_sha256": request["purpose_sha256"],
        "bound_retry_policy_generation": request["retry_policy_generation"],
        "supersedes_provider_event_id": supersedes_provider_event_id,
    }
    meta = {
        "source": source,
        "authority_mode": AUTHORITY_MODE,
        "meter": "arbitration_clear",
        "sends_email": False,
        "writer_id": writer_id,
        "hold_reason": hold_reason,
        "holders": holders,
    }
    return {"decision_event": event, "meta": meta}


def clear_or_fallback(
    muse_reply_text: str,
    request: Mapping[str, Any],
    *,
    disposition_if_fallback: str = "SELECTED",
    writer_id: Optional[str] = None,
    provider_event_id: Optional[str] = None,
    observed_at: Optional[str] = None,
    supersedes_provider_event_id: Optional[str] = None,
    creds_path: str | Path = DEFAULT_CREDS_PATH,
    require_creds_present: bool = False,
) -> dict[str, Any]:
    """Prefer an exact Muse CLEAR wire; otherwise mint DeepSeek fallback evidence.

    Returns::

        {
          "source": "muse"|"deepseek_fallback",
          "parse": <parse_clear_reply result>,
          "decision_event": <ledger DECISION>|None,
          "creds_summary": <redacted>|None,
          "sends_email": False,
        }
    """
    parsed = parse_clear_reply(muse_reply_text, request)
    creds_summary = None
    if require_creds_present or parsed.get("reason") != REASON_OK:
        if require_creds_present or os.environ.get("DEEPSEEK_FALLBACK_REQUIRE_CREDS") == "1":
            creds_summary = redacted_creds_summary(creds_path)
        elif Path(creds_path).is_file():
            try:
                creds_summary = redacted_creds_summary(creds_path)
            except DeepSeekFallbackError:
                creds_summary = None

    if parsed.get("ok") and parsed.get("reason") == REASON_OK:
        observed = observed_at or _utc_now()
        eid = provider_event_id or f"muse-clear:{request['request_key']}:{observed}"
        event = decision_event_from_parse(
            parsed,
            provider_event_id=eid,
            provider_event_sha256=_sha256_text(eid),
            observed_at=observed,
            supersedes_provider_event_id=supersedes_provider_event_id,
        )
        return {
            "source": "muse",
            "parse": parsed,
            "decision_event": event,
            "creds_summary": creds_summary,
            "sends_email": False,
        }

    minted = mint_decision_from_request(
        request,
        decision=disposition_if_fallback,
        provider_event_id=provider_event_id,
        observed_at=observed_at,
        writer_id=writer_id,
        supersedes_provider_event_id=supersedes_provider_event_id,
        source="deepseek_fallback_local_mint",
    )
    return {
        "source": "deepseek_fallback",
        "parse": parsed,
        "decision_event": minted["decision_event"],
        "meta": minted["meta"],
        "creds_summary": creds_summary,
        "sends_email": False,
    }
