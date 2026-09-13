"""Terminal, one-shot outbound send control.

This module never serializes a reusable pre-send capability.  A trusted host
approval authenticates the exact guard/lease/message generation; the live lease
is re-read from the coordination provider; then one deterministic Git ref is
created exactly once immediately before invoking the supplied send transport.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping

from tools.outbound_send_guard.atomic_lease import LeaseError
from tools.outbound_send_guard.lease_authority import verify_authoritative_receipt

APPROVAL_SCHEMA = "outbound-send-host-approval/v1"
PRECONDITION_SCHEMA = "outbound-send-preconditions/v2"
CONSUME_SCHEMA = "outbound-send-consumption/v1"
RESULT_SCHEMA = "outbound-send-consume-result/v1"
GUARD_SCHEMA = "outbound-send-guard-receipt/v1"
MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_AGE_SECONDS = 300
MAX_FUTURE_SKEW_SECONDS = 30
MAX_APPROVAL_LIFETIME_SECONDS = 300
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_MACHINE = re.compile(r"^[a-z0-9][a-z0-9._:@/+\-]{2,191}$")
_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class AuthorityError(ValueError):
    pass


Transport = Callable[[str, str, Mapping[str, Any] | None], tuple[int, Any]]
SendTransport = Callable[[bytes, str], tuple[int, Any]]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise AuthorityError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _loads(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_INPUT_BYTES:
        raise AuthorityError(f"{label} must be 1..{MAX_INPUT_BYTES} bytes")
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                AuthorityError(f"{label} contains non-finite number {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuthorityError(f"{label} is invalid UTF-8 JSON") from exc
    if type(value) is not dict:
        raise AuthorityError(f"{label} must be an object")
    return value


def _canon(value: Any, *, newline: bool = False, ascii_only: bool = False) -> bytes:
    try:
        raw = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=ascii_only,
            allow_nan=False,
        ).encode("ascii" if ascii_only else "utf-8")
    except (TypeError, ValueError) as exc:
        raise AuthorityError("value is not canonical JSON") from exc
    return raw + (b"\n" if newline else b"")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha_object(value: Any, *, newline: bool = False, ascii_only: bool = False) -> str:
    return _sha(_canon(value, newline=newline, ascii_only=ascii_only))


def _exact(obj: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(obj)
    if actual != expected:
        raise AuthorityError(
            f"{label} keys mismatch missing={sorted(expected-actual)} extra={sorted(actual-expected)}"
        )


def _text(value: Any, label: str, max_len: int = 256) -> str:
    if type(value) is not str or not value or len(value) > max_len:
        raise AuthorityError(f"{label} must be non-empty text <= {max_len} chars")
    if any(ord(ch) < 0x20 or ch == "\x7f" for ch in value):
        raise AuthorityError(f"{label} contains control characters")
    return value


def _machine(value: Any, label: str) -> str:
    value = _text(value, label, 192)
    if not value.isascii() or value != value.casefold() or _MACHINE.fullmatch(value) is None:
        raise AuthorityError(f"{label} must be a lowercase ASCII machine token")
    return value


def _hex64(value: Any, label: str) -> str:
    value = _text(value, label, 64)
    if _HEX64.fullmatch(value) is None:
        raise AuthorityError(f"{label} must be 64 lowercase hex characters")
    return value


def _git_sha(value: Any, label: str) -> str:
    value = _text(value, label, 64)
    if _GIT_SHA.fullmatch(value) is None:
        raise AuthorityError(f"{label} must be 40 or 64 lowercase hex characters")
    return value


def _repo(value: Any) -> str:
    value = _text(value, "approval.repo", 200)
    if _REPO.fullmatch(value) is None:
        raise AuthorityError("approval.repo must be owner/name")
    return value


def _time(value: Any, label: str) -> datetime:
    text = _text(value, label, 64)
    raw = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise AuthorityError(f"{label} must be RFC3339") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AuthorityError(f"{label} must include timezone")
    return parsed.astimezone(timezone.utc)


def _fmt(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _key(host_key: bytes) -> bytes:
    if type(host_key) is not bytes or len(host_key) < 32:
        raise AuthorityError("host_key must be at least 32 secret bytes")
    return host_key


_APPROVAL_FIELDS = {
    "schema_version", "repo", "buyer_scope", "commercial_scope", "offer_scope",
    "recipient_sha256", "message_sha256", "claimant", "claim_id",
    "claim_started_at", "anchor_sha", "guard_receipt_sha256",
    "guard_payload_receipt_sha256", "lease_receipt_sha256", "issued_at", "expires_at",
}


def _normalize_approval_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if type(payload) is not dict:
        raise AuthorityError("approval.payload must be an object")
    _exact(payload, _APPROVAL_FIELDS, "approval.payload")
    if payload["schema_version"] != APPROVAL_SCHEMA:
        raise AuthorityError(f"approval.payload.schema_version must be {APPROVAL_SCHEMA}")
    issued = _time(payload["issued_at"], "approval.payload.issued_at")
    expires = _time(payload["expires_at"], "approval.payload.expires_at")
    if expires <= issued or expires - issued > timedelta(seconds=MAX_APPROVAL_LIFETIME_SECONDS):
        raise AuthorityError("approval expiry must be after issuance and within 300 seconds")
    return {
        "schema_version": APPROVAL_SCHEMA,
        "repo": _repo(payload["repo"]),
        "buyer_scope": _machine(payload["buyer_scope"], "approval.payload.buyer_scope"),
        "commercial_scope": _machine(payload["commercial_scope"], "approval.payload.commercial_scope"),
        "offer_scope": _machine(payload["offer_scope"], "approval.payload.offer_scope"),
        "recipient_sha256": _hex64(payload["recipient_sha256"], "approval.payload.recipient_sha256"),
        "message_sha256": _hex64(payload["message_sha256"], "approval.payload.message_sha256"),
        "claimant": _text(payload["claimant"], "approval.payload.claimant", 192),
        "claim_id": _machine(payload["claim_id"], "approval.payload.claim_id"),
        "claim_started_at": _fmt(_time(payload["claim_started_at"], "approval.payload.claim_started_at")),
        "anchor_sha": _git_sha(payload["anchor_sha"], "approval.payload.anchor_sha"),
        "guard_receipt_sha256": _hex64(payload["guard_receipt_sha256"], "approval.payload.guard_receipt_sha256"),
        "guard_payload_receipt_sha256": _hex64(payload["guard_payload_receipt_sha256"], "approval.payload.guard_payload_receipt_sha256"),
        "lease_receipt_sha256": _hex64(payload["lease_receipt_sha256"], "approval.payload.lease_receipt_sha256"),
        "issued_at": _fmt(issued),
        "expires_at": _fmt(expires),
    }


def sign_host_approval(payload: Mapping[str, Any], *, host_key: bytes) -> dict[str, Any]:
    """Sign an owner/host-authenticated pre-send approval.

    `host_key` is an operational secret and must never be placed in candidate
    packets, receipts, source control, or chat logs.
    """
    normalized = _normalize_approval_payload(payload)
    mac = hmac.new(_key(host_key), _canon(normalized, ascii_only=True), hashlib.sha256).hexdigest()
    return {"payload": normalized, "host_mac_sha256": mac}


def _parse_approval(raw: bytes, host_key: bytes) -> tuple[dict[str, Any], str, str]:
    obj = _loads(raw, "host approval")
    _exact(obj, {"payload", "host_mac_sha256"}, "host approval")
    payload = _normalize_approval_payload(obj["payload"])
    supplied = _hex64(obj["host_mac_sha256"], "host approval.host_mac_sha256")
    expected = hmac.new(_key(host_key), _canon(payload, ascii_only=True), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied, expected):
        raise AuthorityError("host approval MAC mismatch")
    return payload, _sha(raw), _sha_object(payload, ascii_only=True)


def _parse_guard(raw: bytes) -> dict[str, Any]:
    obj = _loads(raw, "guard receipt")
    _exact(obj, {"payload", "receipt_sha256"}, "guard receipt")
    payload = obj["payload"]
    if type(payload) is not dict:
        raise AuthorityError("guard receipt.payload must be an object")
    receipt_sha = _hex64(obj["receipt_sha256"], "guard receipt.receipt_sha256")
    if _sha_object(payload, newline=True) != receipt_sha:
        raise AuthorityError("guard receipt digest mismatch")
    _exact(
        payload,
        {"schema_version", "intent", "evidence", "policy", "decision", "authority",
         "reasons", "latest_outbound_at", "latest_inbound_at", "reply_message_id",
         "side_effects_authorized"},
        "guard receipt.payload",
    )
    if payload["schema_version"] != GUARD_SCHEMA:
        raise AuthorityError("unsupported guard receipt schema")
    intent = payload["intent"]
    evidence = payload["evidence"]
    if type(intent) is not dict or type(evidence) is not dict:
        raise AuthorityError("guard intent/evidence must be objects")
    _exact(intent, {"intent_id", "recipient", "offer_id", "requested_at", "route_kind"}, "guard intent")
    _exact(
        evidence,
        {"generated_at", "mailbox_complete", "mailbox_query_id", "slack_complete",
         "slack_query_id", "intent_sha256", "evidence_sha256", "matched_refs"},
        "guard evidence",
    )
    if type(payload["side_effects_authorized"]) is not bool:
        raise AuthorityError("guard side_effects_authorized must be boolean")
    if type(evidence["mailbox_complete"]) is not bool or type(evidence["slack_complete"]) is not bool:
        raise AuthorityError("guard completeness must be boolean")
    if type(payload["reasons"]) is not list or type(evidence["matched_refs"]) is not list:
        raise AuthorityError("guard list fields malformed")
    recipient = _text(intent["recipient"], "guard intent.recipient", 320).casefold()
    return {
        "exact_sha256": _sha(raw),
        "payload_receipt_sha256": receipt_sha,
        "decision": _text(payload["decision"], "guard decision", 32),
        "authority": _text(payload["authority"], "guard authority", 32),
        "side_effects_authorized": payload["side_effects_authorized"],
        "mailbox_complete": evidence["mailbox_complete"],
        "slack_complete": evidence["slack_complete"],
        "recipient_sha256": _sha(recipient.encode("utf-8")),
        "offer_scope": _machine(intent["offer_id"], "guard intent.offer_id"),
        "requested_at": _time(intent["requested_at"], "guard intent.requested_at"),
        "generated_at": _time(evidence["generated_at"], "guard evidence.generated_at"),
        "route_kind": _text(intent["route_kind"], "guard intent.route_kind", 32),
    }


def _parse_lease(raw: bytes) -> dict[str, Any]:
    return _loads(raw, "lease receipt")


def _context_reasons(
    approval: Mapping[str, Any],
    *,
    expected_claimant: str,
    expected_claim_id: str,
    expected_claim_started_at: str,
    expected_anchor_sha: str,
) -> list[str]:
    reasons: list[str] = []
    claimant = _text(expected_claimant, "expected_claimant", 192)
    claim_id = _machine(expected_claim_id, "expected_claim_id")
    started = _fmt(_time(expected_claim_started_at, "expected_claim_started_at"))
    anchor = _git_sha(expected_anchor_sha, "expected_anchor_sha")
    if approval["claimant"] != claimant:
        reasons.append("CALLER_CLAIMANT_MISMATCH")
    if approval["claim_id"] != claim_id:
        reasons.append("CALLER_CLAIM_ID_MISMATCH")
    if approval["claim_started_at"] != started:
        reasons.append("CALLER_CLAIM_STARTED_AT_MISMATCH")
    if approval["anchor_sha"] != anchor:
        reasons.append("CALLER_ANCHOR_MISMATCH")
    return reasons


def _evaluate_at(
    approval_bytes: bytes,
    guard_receipt_bytes: bytes,
    lease_receipt_bytes: bytes,
    *,
    host_key: bytes,
    lease_transport: Transport,
    expected_claimant: str,
    expected_claim_id: str,
    expected_claim_started_at: str,
    expected_anchor_sha: str,
    now: datetime,
) -> dict[str, Any]:
    if type(now) is not datetime or now.tzinfo is None or now.utcoffset() is None:
        raise AuthorityError("now must be timezone-aware")
    now = now.astimezone(timezone.utc)
    approval, approval_exact_sha, approval_payload_sha = _parse_approval(approval_bytes, host_key)
    guard = _parse_guard(guard_receipt_bytes)
    lease = _parse_lease(lease_receipt_bytes)
    reasons = _context_reasons(
        approval,
        expected_claimant=expected_claimant,
        expected_claim_id=expected_claim_id,
        expected_claim_started_at=expected_claim_started_at,
        expected_anchor_sha=expected_anchor_sha,
    )

    if guard["exact_sha256"] != approval["guard_receipt_sha256"]:
        reasons.append("GUARD_EXACT_BYTES_MISMATCH")
    if guard["payload_receipt_sha256"] != approval["guard_payload_receipt_sha256"]:
        reasons.append("GUARD_PAYLOAD_RECEIPT_MISMATCH")
    if _sha(lease_receipt_bytes) != approval["lease_receipt_sha256"]:
        reasons.append("LEASE_EXACT_BYTES_MISMATCH")
    if guard["decision"] != "ALLOW_NEW":
        reasons.append("GUARD_NOT_ALLOW_NEW")
    if guard["authority"] != "complete" or not guard["mailbox_complete"] or not guard["slack_complete"]:
        reasons.append("GUARD_AUTHORITY_INCOMPLETE")
    if guard["side_effects_authorized"] is not False:
        reasons.append("GUARD_SIDE_EFFECT_BIT_INVALID")
    if guard["route_kind"] != "email":
        reasons.append("GUARD_ROUTE_MISMATCH")
    if guard["recipient_sha256"] != approval["recipient_sha256"]:
        reasons.append("GUARD_RECIPIENT_MISMATCH")
    if guard["offer_scope"] != approval["offer_scope"]:
        reasons.append("GUARD_OFFER_MISMATCH")

    skew = timedelta(seconds=MAX_FUTURE_SKEW_SECONDS)
    age = timedelta(seconds=MAX_AGE_SECONDS)
    issued = _time(approval["issued_at"], "approval issued_at")
    expires = _time(approval["expires_at"], "approval expires_at")
    started = _time(approval["claim_started_at"], "approval claim_started_at")
    if now < issued - skew:
        reasons.append("APPROVAL_FUTURE")
    if now > expires:
        reasons.append("APPROVAL_EXPIRED")
    for label, ts in (("GUARD", guard["generated_at"]), ("REQUEST", guard["requested_at"]), ("LEASE", started)):
        if ts - now > skew:
            reasons.append(f"{label}_FUTURE")
        elif now - ts > age:
            reasons.append(f"{label}_STALE")
    if started < guard["generated_at"] - skew:
        reasons.append("LEASE_PREDATES_GUARD")
    if issued < guard["generated_at"] - skew:
        reasons.append("APPROVAL_PREDATES_GUARD")

    lease_authoritative = False
    if not reasons:
        try:
            lease_authoritative = bool(verify_authoritative_receipt(
                lease,
                repo=approval["repo"],
                buyer_scope=approval["buyer_scope"],
                offer_scope=approval["offer_scope"],
                claimant=approval["claimant"],
                claim_id=approval["claim_id"],
                claim_started_at=approval["claim_started_at"],
                anchor_sha=approval["anchor_sha"],
                preflight_sha256=approval["guard_payload_receipt_sha256"],
                transport=lease_transport,
            ))
        except (LeaseError, OSError, ValueError, TypeError):
            lease_authoritative = False
        if not lease_authoritative:
            reasons.append("LIVE_LEASE_AUTHORITY_FAILED")

    reasons = sorted(set(reasons))
    decision = "PRECONDITIONS_READY" if not reasons else "HOLD"
    payload = {
        "schema_version": PRECONDITION_SCHEMA,
        "decision": decision,
        "external_send_authorized": False,
        "consumption_required": True,
        "repo": approval["repo"],
        "buyer_scope": approval["buyer_scope"],
        "commercial_scope": approval["commercial_scope"],
        "offer_scope": approval["offer_scope"],
        "recipient_sha256": approval["recipient_sha256"],
        "message_sha256": approval["message_sha256"],
        "claimant": approval["claimant"],
        "claim_id": approval["claim_id"],
        "approval_exact_sha256": approval_exact_sha,
        "approval_payload_sha256": approval_payload_sha,
        "guard_receipt_sha256": approval["guard_receipt_sha256"],
        "lease_receipt_sha256": approval["lease_receipt_sha256"],
        "evaluated_at": _fmt(now),
        "reasons": reasons,
    }
    return {"payload": payload, "receipt_sha256": _sha_object(payload, newline=True)}


def evaluate_current(
    approval_bytes: bytes,
    guard_receipt_bytes: bytes,
    lease_receipt_bytes: bytes,
    *,
    host_key: bytes,
    lease_transport: Transport,
    expected_claimant: str,
    expected_claim_id: str,
    expected_claim_started_at: str,
    expected_anchor_sha: str,
) -> dict[str, Any]:
    """Revalidate current preconditions. This function never grants send authority."""
    return _evaluate_at(
        approval_bytes, guard_receipt_bytes, lease_receipt_bytes,
        host_key=host_key,
        lease_transport=lease_transport,
        expected_claimant=expected_claimant,
        expected_claim_id=expected_claim_id,
        expected_claim_started_at=expected_claim_started_at,
        expected_anchor_sha=expected_anchor_sha,
        now=_utcnow(),
    )


def _object_sha(body: Any) -> str | None:
    if not isinstance(body, Mapping):
        return None
    candidate = body.get("sha")
    if isinstance(candidate, str) and _GIT_SHA.fullmatch(candidate):
        return candidate
    obj = body.get("object")
    if isinstance(obj, Mapping):
        candidate = obj.get("sha")
        if isinstance(candidate, str) and _GIT_SHA.fullmatch(candidate):
            return candidate
    return None


def _consumption_seam(approval: Mapping[str, Any]) -> tuple[str, str]:
    material = {
        "schema": CONSUME_SCHEMA,
        "repo": approval["repo"],
        "buyer_scope": approval["buyer_scope"],
        "commercial_scope": approval["commercial_scope"],
    }
    digest = _sha_object(material, ascii_only=True)
    return digest, f"refs/tags/outbound-send-once-v1/{digest}"


def _consume_once(
    approval: Mapping[str, Any],
    *,
    approval_exact_sha256: str,
    approval_payload_sha256: str,
    consume_transport: Transport,
    now: datetime,
) -> tuple[str, str, str | None]:
    seam_sha, ref = _consumption_seam(approval)
    metadata = {
        "schema": CONSUME_SCHEMA,
        "repo": approval["repo"],
        "buyer_scope": approval["buyer_scope"],
        "commercial_scope": approval["commercial_scope"],
        "offer_scope": approval["offer_scope"],
        "recipient_sha256": approval["recipient_sha256"],
        "message_sha256": approval["message_sha256"],
        "claimant": approval["claimant"],
        "claim_id": approval["claim_id"],
        "approval_exact_sha256": approval_exact_sha256,
        "approval_payload_sha256": approval_payload_sha256,
        "guard_receipt_sha256": approval["guard_receipt_sha256"],
        "lease_receipt_sha256": approval["lease_receipt_sha256"],
        "seam_sha256": seam_sha,
    }
    owner, repo_name = approval["repo"].split("/", 1)
    tag_body = {
        "tag": f"outbound-send-once-v1-{seam_sha[:16]}-{approval_payload_sha256[:16]}",
        "message": _canon(metadata, ascii_only=True).decode("ascii"),
        "object": approval["anchor_sha"],
        "type": "commit",
        "tagger": {
            "name": "outbound-send-once",
            "email": "send-once@tokenjunkielabs.invalid",
            "date": _fmt(now),
        },
    }
    tag_status, tag_response = consume_transport(
        "POST", f"/repos/{owner}/{repo_name}/git/tags", tag_body
    )
    if tag_status != 201:
        return "TAG_CREATE_FAILED", ref, None
    tag_sha = _object_sha(tag_response)
    if tag_sha is None:
        return "TAG_CREATE_UNVERIFIED", ref, None

    ref_status, ref_response = consume_transport(
        "POST", f"/repos/{owner}/{repo_name}/git/refs", {"ref": ref, "sha": tag_sha}
    )
    if ref_status == 201 and _object_sha(ref_response) == tag_sha:
        return "ACQUIRED_CREATE_201", ref, tag_sha
    if ref_status in {409, 422}:
        return "ALREADY_CONSUMED", ref, tag_sha
    if ref_status == 201 or ref_status in {0, 408, 425, 429, 500, 502, 503, 504}:
        quoted = urllib.parse.quote(ref.removeprefix("refs/"), safe="/")
        get_status, get_body = consume_transport(
            "GET", f"/repos/{owner}/{repo_name}/git/ref/{quoted}", None
        )
        if get_status == 200 and _object_sha(get_body) == tag_sha:
            return "ACQUIRED_READBACK", ref, tag_sha
        return "CONSUME_OUTCOME_UNKNOWN", ref, tag_sha
    return "CONSUME_FAILED", ref, tag_sha


def consume_and_send(
    approval_bytes: bytes,
    guard_receipt_bytes: bytes,
    lease_receipt_bytes: bytes,
    message_bytes: bytes,
    *,
    host_key: bytes,
    lease_transport: Transport,
    consume_transport: Transport,
    send_transport: SendTransport,
    expected_claimant: str,
    expected_claim_id: str,
    expected_claim_started_at: str,
    expected_anchor_sha: str,
) -> dict[str, Any]:
    """Consume one commercial send seam and invoke the provider adapter once.

    The function does not return a reusable authorization artifact. If the
    consumption ref already exists, or if any precondition fails, the provider
    send callback is never invoked. After a provider-ambiguous first attempt,
    later calls remain blocked and must reconcile outcome instead of retrying.
    """
    if type(message_bytes) is not bytes or not message_bytes or len(message_bytes) > MAX_INPUT_BYTES:
        raise AuthorityError(f"message_bytes must be 1..{MAX_INPUT_BYTES} bytes")
    now = _utcnow()
    pre = _evaluate_at(
        approval_bytes, guard_receipt_bytes, lease_receipt_bytes,
        host_key=host_key,
        lease_transport=lease_transport,
        expected_claimant=expected_claimant,
        expected_claim_id=expected_claim_id,
        expected_claim_started_at=expected_claim_started_at,
        expected_anchor_sha=expected_anchor_sha,
        now=now,
    )
    approval, approval_exact_sha, approval_payload_sha = _parse_approval(approval_bytes, host_key)
    reasons = list(pre["payload"]["reasons"])
    if _sha(message_bytes) != approval["message_sha256"]:
        reasons.append("MESSAGE_EXACT_BYTES_MISMATCH")
    if reasons:
        return {
            "schema_version": RESULT_SCHEMA,
            "decision": "HOLD",
            "external_send_authorized": False,
            "send_attempted": False,
            "consumption_state": "NOT_ATTEMPTED",
            "consumption_ref": None,
            "consumption_tag_sha": None,
            "provider_message_id_sha256": None,
            "reasons": sorted(set(reasons)),
        }

    state, ref, tag_sha = _consume_once(
        approval,
        approval_exact_sha256=approval_exact_sha,
        approval_payload_sha256=approval_payload_sha,
        consume_transport=consume_transport,
        now=now,
    )
    if state not in {"ACQUIRED_CREATE_201", "ACQUIRED_READBACK"}:
        return {
            "schema_version": RESULT_SCHEMA,
            "decision": "HOLD_RECONCILE_ONLY" if state in {"ALREADY_CONSUMED", "CONSUME_OUTCOME_UNKNOWN"} else "HOLD",
            "external_send_authorized": False,
            "send_attempted": False,
            "consumption_state": state,
            "consumption_ref": ref,
            "consumption_tag_sha": tag_sha,
            "provider_message_id_sha256": None,
            "reasons": [state],
        }

    consumption_id = _sha_object({
        "schema": CONSUME_SCHEMA,
        "ref": ref,
        "tag_sha": tag_sha,
        "message_sha256": approval["message_sha256"],
    }, ascii_only=True)
    try:
        provider_status, provider_body = send_transport(message_bytes, consumption_id)
    except Exception:
        provider_status, provider_body = 0, None

    provider_id_hash = None
    if 200 <= provider_status < 300:
        provider_id = None
        if isinstance(provider_body, Mapping):
            candidate = provider_body.get("message_id", provider_body.get("id"))
            if isinstance(candidate, str) and candidate:
                provider_id = candidate
        if provider_id is None:
            decision = "PROVIDER_OUTCOME_UNKNOWN_RECONCILE_ONLY"
            reasons = ["PROVIDER_SUCCESS_WITHOUT_MESSAGE_ID"]
        else:
            decision = "SENT_CONFIRMED"
            reasons = []
            provider_id_hash = _sha(provider_id.encode("utf-8"))
    elif 400 <= provider_status < 500 and provider_status not in {408, 425, 429}:
        decision = "PROVIDER_REJECTED_RECONCILE_ONLY"
        reasons = [f"PROVIDER_REJECTED_{provider_status}"]
    else:
        decision = "PROVIDER_OUTCOME_UNKNOWN_RECONCILE_ONLY"
        reasons = ["PROVIDER_OUTCOME_UNKNOWN"]

    return {
        "schema_version": RESULT_SCHEMA,
        "decision": decision,
        "external_send_authorized": False,
        "send_attempted": True,
        "consumption_state": state,
        "consumption_ref": ref,
        "consumption_tag_sha": tag_sha,
        "provider_message_id_sha256": provider_id_hash,
        "reasons": reasons,
    }
