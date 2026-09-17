"""Deterministic outbound single-writer lease and replay guard.

This module has no provider/network integration. It compiles retained
coordination evidence into a fail-closed owner-review state. In particular,
it cannot send, mint Muse authority, or infer delivery/payment/revenue.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone

SCHEMA = "outbound-collision-replay-guard/v1"
STATES = {
    "CLAIMED", "YIELD_EXISTING", "WAIT_MUSE", "READY_SINGLE_WRITER",
    "SENT_TERMINAL", "RELEASED_UNSENT", "HOLD_AMBIGUOUS_COUNTERPARTY",
}
AUTHORITY = {
    "external_send": False,
    "muse_arbitration": False,
    "provider_mutation": False,
    "payment": False,
    "revenue": False,
}
_MAX_TEXT = 512
_SAFE_KEY = re.compile(r"^[a-z0-9][a-z0-9._:@/+~-]{0,511}$")


class GuardError(ValueError):
    pass


def _strict_obj(value, *, name, keys):
    if type(value) is not dict:
        raise GuardError(f"{name} must be an object")
    extra = set(value) - set(keys)
    if extra:
        raise GuardError(f"{name} has unsupported keys: {sorted(extra)!r}")


def _text(value, name, *, allow_empty=False):
    if not isinstance(value, str):
        raise GuardError(f"{name} must be text")
    value = unicodedata.normalize("NFKC", value).strip()
    if not allow_empty and not value:
        raise GuardError(f"{name} must be non-empty")
    if len(value.encode("utf-8")) > _MAX_TEXT:
        raise GuardError(f"{name} too long")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise GuardError(f"{name} contains control characters")
    return value


def _key(value, name):
    value = _text(value, name).casefold()
    value = " ".join(value.split())
    if not _SAFE_KEY.fullmatch(value):
        raise GuardError(f"{name} has unsafe/ambiguous characters")
    return value


def _utc(value, name):
    value = _text(value, name)
    if not value.endswith("Z"):
        raise GuardError(f"{name} must be canonical UTC ending Z")
    try:
        dt = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise GuardError(f"{name} invalid timestamp") from exc
    if dt.tzinfo != timezone.utc:
        raise GuardError(f"{name} must be UTC")
    canonical = dt.isoformat(timespec="seconds").replace("+00:00", "Z")
    if value != canonical:
        raise GuardError(f"{name} must use second-resolution canonical UTC")
    return dt


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(obj):
    return hashlib.sha256(_canon(obj).encode("utf-8")).hexdigest()


def canonical_intent(intent):
    keys = ("counterparty_key", "route_key", "thread_key", "purpose_key")
    _strict_obj(intent, name="intent", keys=keys)
    out = {k: _key(intent.get(k), f"intent.{k}") for k in keys}
    ambiguous = {"unknown", "tbd", "n/a", "na", "*", "any", "general"}
    if out["counterparty_key"] in ambiguous or out["route_key"] in ambiguous:
        raise GuardError("counterparty/route is ambiguous")
    return out


def intent_fingerprint(intent):
    return _sha({"schema": SCHEMA, "intent": canonical_intent(intent)})


def _claimant(claimant):
    keys = ("claimant_id", "session_id")
    _strict_obj(claimant, name="claimant", keys=keys)
    return {k: _key(claimant.get(k), f"claimant.{k}") for k in keys}


def _muse(muse, *, fingerprint, claimant, now):
    if muse is None:
        return None
    keys = (
        "receipt_id", "intent_fingerprint", "selected_claimant_id",
        "selected_session_id", "arbitrated_at", "expires_at",
    )
    _strict_obj(muse, name="muse", keys=keys)
    out = {
        "receipt_id": _key(muse.get("receipt_id"), "muse.receipt_id"),
        "intent_fingerprint": _key(muse.get("intent_fingerprint"), "muse.intent_fingerprint"),
        "selected_claimant_id": _key(muse.get("selected_claimant_id"), "muse.selected_claimant_id"),
        "selected_session_id": _key(muse.get("selected_session_id"), "muse.selected_session_id"),
        "arbitrated_at": _text(muse.get("arbitrated_at"), "muse.arbitrated_at"),
        "expires_at": _text(muse.get("expires_at"), "muse.expires_at"),
    }
    a = _utc(out["arbitrated_at"], "muse.arbitrated_at")
    e = _utc(out["expires_at"], "muse.expires_at")
    if out["intent_fingerprint"] != fingerprint:
        raise GuardError("Muse receipt binds a different intent")
    if out["selected_claimant_id"] != claimant["claimant_id"]:
        raise GuardError("Muse receipt selects a different claimant")
    if out["selected_session_id"] != claimant["session_id"]:
        raise GuardError("Muse receipt selects a different session")
    if a > now:
        raise GuardError("Muse receipt is future-dated")
    if e <= a:
        raise GuardError("Muse expiry must be after arbitration")
    return out, e


def _validate_attempt(attempt):
    keys = ("attempt_id", "body_sha256", "provider", "started_at")
    _strict_obj(attempt, name="attempt", keys=keys)
    _key(attempt.get("attempt_id"), "attempt.attempt_id")
    body = _key(attempt.get("body_sha256"), "attempt.body_sha256")
    if not re.fullmatch(r"[0-9a-f]{64}", body):
        raise GuardError("attempt.body_sha256 must be sha256 hex")
    _key(attempt.get("provider"), "attempt.provider")
    _utc(attempt.get("started_at"), "attempt.started_at")


def _validate_result(result):
    keys = ("attempt_id", "provider_status", "provider_message_id", "observed_at")
    _strict_obj(result, name="terminal_result", keys=keys)
    _key(result.get("attempt_id"), "terminal_result.attempt_id")
    if result.get("provider_status") != "SENT":
        raise GuardError("terminal result must be provider SENT")
    _key(result.get("provider_message_id"), "terminal_result.provider_message_id")
    _utc(result.get("observed_at"), "terminal_result.observed_at")


def _validate_lease(lease):
    if lease is None:
        return None
    keys = (
        "schema", "fingerprint", "intent", "claimant", "generation",
        "taken_at", "expires_at", "state", "muse_receipt_id",
        "attempt", "terminal_result",
    )
    _strict_obj(lease, name="lease", keys=keys)
    if lease.get("schema") != SCHEMA:
        raise GuardError("lease schema mismatch")
    intent = canonical_intent(lease.get("intent"))
    fp = intent_fingerprint(intent)
    if lease.get("fingerprint") != fp:
        raise GuardError("lease fingerprint mismatch")
    claimant = _claimant(lease.get("claimant"))
    generation = lease.get("generation")
    if type(generation) is not int or generation < 1:
        raise GuardError("lease generation invalid")
    taken = _utc(lease.get("taken_at"), "lease.taken_at")
    expires = _utc(lease.get("expires_at"), "lease.expires_at")
    if expires <= taken:
        raise GuardError("lease expiry invalid")
    state = lease.get("state")
    if state not in STATES:
        raise GuardError("lease state invalid")
    if lease.get("muse_receipt_id") is not None:
        _key(lease["muse_receipt_id"], "lease.muse_receipt_id")
    attempt = lease.get("attempt")
    if attempt is not None:
        _validate_attempt(attempt)
    terminal = lease.get("terminal_result")
    if terminal is not None:
        _validate_result(terminal)
    return {
        "schema": SCHEMA, "fingerprint": fp, "intent": intent,
        "claimant": claimant, "generation": generation,
        "taken_at": lease["taken_at"], "expires_at": lease["expires_at"],
        "state": state, "muse_receipt_id": lease.get("muse_receipt_id"),
        "attempt": attempt, "terminal_result": terminal,
    }


def acquire(*, intent, claimant, now, ttl_s, existing=None, muse=None):
    """Acquire/inspect a lease. Muse evidence is consumed, never minted."""
    if type(ttl_s) is not int or not 30 <= ttl_s <= 7200:
        raise GuardError("ttl_s must be an int in [30,7200]")
    now_dt = _utc(now, "now")
    intent = canonical_intent(intent)
    fp = intent_fingerprint(intent)
    claimant = _claimant(claimant)
    old = _validate_lease(existing)
    if old is not None and old["fingerprint"] != fp:
        raise GuardError("existing lease is for a different intent")
    if old is not None and old["state"] == "SENT_TERMINAL":
        return _envelope("SENT_TERMINAL", old, "provider-confirmed send is terminal")
    if old is not None:
        expiry = _utc(old["expires_at"], "lease.expires_at")
        live = expiry > now_dt
        same = old["claimant"] == claimant
        if live and not same:
            return _envelope("YIELD_EXISTING", old, "live lease belongs to another claimant")
        if live and same:
            generation, taken_at, attempt = old["generation"], old["taken_at"], old["attempt"]
        else:
            generation, taken_at, attempt = old["generation"] + 1, now, None
    else:
        generation, taken_at, attempt = 1, now, None
    expires_dt = datetime.fromtimestamp(now_dt.timestamp() + ttl_s, tz=timezone.utc)
    expires = expires_dt.isoformat(timespec="seconds").replace("+00:00", "Z")
    base = {
        "schema": SCHEMA, "fingerprint": fp, "intent": intent,
        "claimant": claimant, "generation": generation,
        "taken_at": taken_at, "expires_at": expires, "state": "CLAIMED",
        "muse_receipt_id": None, "attempt": attempt, "terminal_result": None,
    }
    try:
        muse_checked = _muse(muse, fingerprint=fp, claimant=claimant, now=now_dt)
    except GuardError:
        base["state"] = "WAIT_MUSE"
        return _envelope("WAIT_MUSE", base, "Muse evidence invalid or mismatched")
    if muse_checked is None:
        base["state"] = "WAIT_MUSE"
        return _envelope("WAIT_MUSE", base, "fresh exact Muse arbitration required")
    muse_norm, muse_expiry = muse_checked
    if muse_expiry <= now_dt:
        base["state"] = "WAIT_MUSE"
        return _envelope("WAIT_MUSE", base, "Muse clearance expired")
    if muse_expiry < expires_dt:
        base["expires_at"] = muse_expiry.isoformat(timespec="seconds").replace("+00:00", "Z")
    base["muse_receipt_id"] = muse_norm["receipt_id"]
    base["state"] = "READY_SINGLE_WRITER"
    return _envelope("READY_SINGLE_WRITER", base, "exact claimant/session/intent arbitration is current")


def begin_send(*, lease, body_sha256, provider, now):
    """Reserve an idempotent provider attempt; changed retry bytes are rejected."""
    now_dt = _utc(now, "now")
    row = _validate_lease(lease)
    if row["state"] == "SENT_TERMINAL":
        return _envelope("SENT_TERMINAL", row, "already sent")
    if _utc(row["expires_at"], "lease.expires_at") <= now_dt:
        raise GuardError("lease expired before send attempt")
    if row["state"] != "READY_SINGLE_WRITER":
        raise GuardError("lease is not READY_SINGLE_WRITER")
    body_sha256 = _key(body_sha256, "body_sha256")
    if not re.fullmatch(r"[0-9a-f]{64}", body_sha256):
        raise GuardError("body_sha256 must be sha256 hex")
    provider = _key(provider, "provider")
    current = row.get("attempt")
    if current is not None:
        if current["body_sha256"] != body_sha256 or current["provider"] != provider:
            raise GuardError("in-flight retry changed body/provider")
        return _envelope("READY_SINGLE_WRITER", row, "same send attempt replayed idempotently")
    seed = {
        "fingerprint": row["fingerprint"], "generation": row["generation"],
        "claimant": row["claimant"], "body_sha256": body_sha256, "provider": provider,
    }
    row["attempt"] = {
        "attempt_id": _sha(seed)[:32], "body_sha256": body_sha256,
        "provider": provider, "started_at": now,
    }
    return _envelope("READY_SINGLE_WRITER", row, "send attempt reserved; provider call remains external")


def observe_send(*, lease, attempt_id, provider_status, provider_message_id, now):
    """Only exact provider SENT terminalizes; UNKNOWN preserves the same attempt."""
    _utc(now, "now")
    row = _validate_lease(lease)
    if row["state"] == "SENT_TERMINAL":
        return _envelope("SENT_TERMINAL", row, "already terminal")
    attempt = row.get("attempt")
    if attempt is None:
        raise GuardError("no send attempt is reserved")
    attempt_id = _key(attempt_id, "attempt_id")
    if attempt_id != attempt["attempt_id"]:
        raise GuardError("provider result binds a different attempt")
    if provider_status == "UNKNOWN":
        if provider_message_id not in (None, ""):
            raise GuardError("UNKNOWN must not assert provider message id")
        return _envelope("READY_SINGLE_WRITER", row, "provider result unresolved; reconcile exact attempt before retry")
    if provider_status != "SENT":
        raise GuardError("provider_status must be SENT or UNKNOWN")
    provider_message_id = _key(provider_message_id, "provider_message_id")
    row["terminal_result"] = {
        "attempt_id": attempt_id, "provider_status": "SENT",
        "provider_message_id": provider_message_id, "observed_at": now,
    }
    row["state"] = "SENT_TERMINAL"
    return _envelope("SENT_TERMINAL", row, "provider-confirmed send; exact intent is hard terminal")


def release_unsent(*, lease, claimant, now):
    now_dt = _utc(now, "now")
    row = _validate_lease(lease)
    claimant = _claimant(claimant)
    if row["state"] == "SENT_TERMINAL":
        return _envelope("SENT_TERMINAL", row, "sent lease cannot be released as unsent")
    if row["claimant"] != claimant:
        raise GuardError("only exact claimant/session may release")
    if row.get("attempt") is not None:
        raise GuardError("cannot release with unresolved send attempt")
    row["state"] = "RELEASED_UNSENT"
    row["expires_at"] = now_dt.isoformat(timespec="seconds").replace("+00:00", "Z")
    return _envelope("RELEASED_UNSENT", row, "lease released without provider send")


def ambiguous_hold(*, raw_counterparty, raw_route, purpose_key):
    evidence = {
        "raw_counterparty": _text(raw_counterparty, "raw_counterparty"),
        "raw_route": _text(raw_route, "raw_route"),
        "purpose_key": _key(purpose_key, "purpose_key"),
    }
    return {
        "schema": SCHEMA,
        "state": "HOLD_AMBIGUOUS_COUNTERPARTY",
        "reason": "counterparty/route aliases require upstream canonical resolution",
        "evidence": evidence,
        "authority": dict(AUTHORITY),
        "receipt_sha256": _sha({"state": "HOLD_AMBIGUOUS_COUNTERPARTY", "evidence": evidence}),
    }


def verify(envelope):
    keys = ("schema", "state", "reason", "lease", "authority", "receipt_sha256")
    _strict_obj(envelope, name="envelope", keys=keys)
    if envelope.get("schema") != SCHEMA:
        raise GuardError("envelope schema mismatch")
    if envelope.get("state") not in STATES:
        raise GuardError("envelope state invalid")
    if envelope.get("authority") != AUTHORITY:
        raise GuardError("authority must remain exactly all-false")
    lease = _validate_lease(envelope.get("lease"))
    expected = _sha({
        "schema": SCHEMA, "state": envelope["state"], "reason": envelope.get("reason"),
        "lease": lease, "authority": AUTHORITY,
    })
    if envelope.get("receipt_sha256") != expected:
        raise GuardError("receipt digest mismatch")
    return True


def _envelope(state, lease, reason):
    if state not in STATES:
        raise GuardError("internal state invalid")
    lease = _validate_lease(lease)
    lease["state"] = state
    body = {
        "schema": SCHEMA, "state": state, "reason": _text(reason, "reason"),
        "lease": lease, "authority": dict(AUTHORITY),
    }
    body["receipt_sha256"] = _sha(body)
    return body
