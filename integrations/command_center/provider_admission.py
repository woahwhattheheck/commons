"""One publication admission policy for local, HTTP and equipment callers."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from .request_budget import RequestBudget, RequestDeferred

SCOPE = "github:publication"
SHARED_SCOPES = ("github:GET", "github:GET:core")
FIELDS = {
    "configure": {"capacity"}, "status": set(),
    "acquire": {"holder", "ttl_seconds"},
    "renew": {"holder", "lease_id", "ttl_seconds"},
    "release": {"holder", "lease_id", "successful"},
    "limited": {"retry_after", "reset_at", "primary_core"},
}


def execute(state_dir, payload):
    """Use only the authority's configured state directory and fixed scopes.

    No provider requests or automatic retries. Acquire is idempotent while its
    holder's lease is live; renew/release are fenced by the exact lease ID.
    """
    try:
        if not isinstance(payload, dict):
            raise ValueError("Admission requires a JSON object.")
        action = payload.get("action", "status")
        if not isinstance(action, str) or action not in FIELDS:
            raise ValueError("Unknown provider admission action.")
        if set(payload) - FIELDS[action] - {"action"}:
            raise ValueError("Unexpected fields for provider admission action.")
        for field in ("successful", "primary_core"):
            if field in payload and type(payload[field]) is not bool:
                raise ValueError(field + " must be a boolean.")
        if action in {"renew", "release"}:
            if not isinstance(payload.get("lease_id"), str) or not re.fullmatch(r"[0-9a-f]{32}", payload["lease_id"]):
                raise ValueError("lease_id must be the exact returned lease ID.")
        state_dir = Path(state_dir)
        state_dir.mkdir(parents=True, exist_ok=True)
        budget = RequestBudget(state_dir)
        if action == "configure":
            result = budget.set_capacity(SCOPE, payload.get("capacity"))
        elif action == "status":
            result = budget.lease_status(SCOPE, shared_scopes=SHARED_SCOPES)
        elif action == "acquire":
            result = budget.acquire_lease(SCOPE, payload.get("holder"),
                ttl_seconds=payload.get("ttl_seconds", 300), shared_scopes=SHARED_SCOPES)
        elif action == "renew":
            result = budget.renew_lease(SCOPE, payload.get("holder"), payload["lease_id"],
                ttl_seconds=payload.get("ttl_seconds", 300), shared_scopes=SHARED_SCOPES)
        elif action == "release":
            result = budget.release_lease(SCOPE, payload.get("holder"), payload["lease_id"])
            if result["released"] and payload.get("successful", False):
                budget.succeeded(SCOPE, shared_scopes=SHARED_SCOPES)
        else:
            primary = payload.get("primary_core", False)
            result = budget.rate_limited("github:GET:core" if primary else "github:GET",
                payload.get("retry_after"), reset_at=payload.get("reset_at") if primary else None)
        return {"ok": True, **result}
    except RequestDeferred as exc:
        return {"ok": False, "error": "provider_admission_deferred", "scope": exc.scope,
                "reason": exc.reason, "retry_not_before": exc.retry_not_before}
    except (OSError, ValueError, sqlite3.Error) as exc:
        return {"ok": False, "error": "provider_admission_failed", "message": str(exc)}


def call(center, payload):
    return execute(center.state_dir, payload)


def tool():
    return {
        "name": "command_center_provider_admission",
        "description": "Coordinate GitHub publication capacity and cooldowns in the shared command-center ledger. Configure capacity once; acquire per unique holder, renew exact lease_id before each write, release finally. No provider writes or publication authority. Never proceed on ok:false; deferred responses give retry_not_before. Expiry cannot cancel in-flight writes. Do not automatically replay limited after an uncertain response; read status first.",
        "inputSchema": {
            "type": "object", "required": ["action"], "additionalProperties": False,
            "properties": {
                "action": {"type": "string", "enum": list(FIELDS)},
                "capacity": {"type": "integer", "minimum": 1, "maximum": 64},
                "holder": {"type": "string", "minLength": 1, "maxLength": 200},
                "lease_id": {"type": "string", "pattern": "^[0-9a-f]{32}$"},
                "ttl_seconds": {"type": "integer", "minimum": 1, "maximum": 3600},
                "successful": {"type": "boolean", "description": "Only after confirmed provider success."},
                "retry_after": {"type": ["string", "number"], "description": "Observed provider seconds or HTTP date; omit if unavailable."},
                "reset_at": {"type": "number", "description": "Observed reset epoch for confirmed primary-core exhaustion."},
                "primary_core": {"type": "boolean", "description": "True only for confirmed primary-core quota exhaustion."},
            },
        },
    }
