#!/usr/bin/env python3
"""Deterministic state machine for collision-free swarm outreach.

This module deliberately does not send mail.  It produces/validates compact claim
records that are safe to place behind an atomic compare-and-swap store such as
GitHub's contents API.  A sender may contact a lead only after it owns a record in
COMMITTED state.  COMMITTED and SENT records are terminal barriers against other
senders; an expired HELD record may be taken over with CAS.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "commons-outreach-claim-fence-v1"
_NAMESPACE = b"commons-outreach-claim-fence-v1\x00"
SOURCE_RE = re.compile(r"^[A-Za-z0-9:/._-]{3,256}$")
TOKEN_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
SCOPE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
OPAQUE_RE = re.compile(r"^[A-Za-z0-9:/._#=+-]{1,512}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_INTENTS = frozenset({"email", "dm", "call", "proposal", "other"})
ALLOWED_STATES = frozenset({"HELD", "COMMITTED", "SENT", "RELEASED"})


class ClaimError(ValueError):
    """The record or requested transition is invalid."""


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def parse_time(value: str | dt.datetime | None) -> dt.datetime:
    if value is None:
        return _utc_now()
    if isinstance(value, dt.datetime):
        out = value
    elif isinstance(value, str):
        raw = value.strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            out = dt.datetime.fromisoformat(raw)
        except ValueError as exc:
            raise ClaimError(f"invalid timestamp: {value!r}") from exc
    else:
        raise ClaimError("timestamp must be a string or datetime")
    if out.tzinfo is None:
        raise ClaimError("timestamp must include UTC offset")
    return out.astimezone(dt.timezone.utc).replace(microsecond=0)


def fmt_time(value: dt.datetime) -> str:
    return parse_time(value).isoformat().replace("+00:00", "Z")


def _token(name: str, value: str, regex: re.Pattern[str] = TOKEN_RE) -> str:
    if not isinstance(value, str):
        raise ClaimError(f"{name} must be a string")
    out = value.strip()
    if not regex.fullmatch(out):
        raise ClaimError(f"invalid {name}: {value!r}")
    return out


def normalize_source_ref(source_ref: str) -> str:
    """Return a non-PII, shared source identifier.

    Prefer Slack message identity, e.g. ``slack:C0C2BE7K0KA/1789317107.693609``.
    Raw email addresses are intentionally rejected so a public claim ledger does
    not become a contact database.
    """
    if not isinstance(source_ref, str):
        raise ClaimError("source_ref must be a string")
    value = source_ref.strip()
    if "@" in value or value.lower().startswith("mailto:"):
        raise ClaimError("source_ref must be an opaque lead/source id, not an email address")
    if not SOURCE_RE.fullmatch(value):
        raise ClaimError("source_ref must be 3-256 chars of A-Z a-z 0-9 : / . _ -")
    return value


def normalize_scope(scope: str) -> str:
    if not isinstance(scope, str):
        raise ClaimError("scope must be a string")
    value = scope.strip().lower()
    if not SCOPE_RE.fullmatch(value):
        raise ClaimError("scope must match [a-z0-9][a-z0-9._-]{0,63}")
    return value


def normalize_intent(intent: str) -> str:
    if not isinstance(intent, str):
        raise ClaimError("intent must be a string")
    value = intent.strip().lower()
    if value not in ALLOWED_INTENTS:
        raise ClaimError(f"intent must be one of {sorted(ALLOWED_INTENTS)}")
    return value


def source_fingerprint(source_ref: str) -> str:
    source = normalize_source_ref(source_ref)
    return hashlib.sha256(b"source\x00" + source.encode()).hexdigest()


def collision_sha256_from_fingerprint(source_fp: str, scope: str = "initial") -> str:
    """Return the cross-channel collision identity for one outreach phase.

    Delivery intent is deliberately excluded: email and DM attempts for the same
    lead and phase must rendezvous at the same atomic path.  A deliberate later
    touch uses a new scope such as ``followup-1``.
    """
    if not isinstance(source_fp, str) or not SHA256_RE.fullmatch(source_fp):
        raise ClaimError("source_fingerprint must be 64 lowercase hex chars")
    scope_n = normalize_scope(scope)
    material = _NAMESPACE + b"collision\x00" + source_fp.encode() + b"\x00" + scope_n.encode()
    return hashlib.sha256(material).hexdigest()


def identity_sha256_from_fingerprint(source_fp: str, scope: str = "initial", intent: str = "email") -> str:
    """Bind the redacted source fingerprint to canonical scope + chosen intent."""
    if not isinstance(source_fp, str) or not SHA256_RE.fullmatch(source_fp):
        raise ClaimError("source_fingerprint must be 64 lowercase hex chars")
    scope_n = normalize_scope(scope)
    intent_n = normalize_intent(intent)
    collision = collision_sha256_from_fingerprint(source_fp, scope_n)
    material = _NAMESPACE + b"record\x00" + collision.encode() + b"\x00" + intent_n.encode()
    return hashlib.sha256(material).hexdigest()


def collision_sha256(source_ref: str, scope: str = "initial") -> str:
    return collision_sha256_from_fingerprint(source_fingerprint(source_ref), scope)


def identity_sha256(source_ref: str, scope: str = "initial", intent: str = "email") -> str:
    return identity_sha256_from_fingerprint(source_fingerprint(source_ref), scope, intent)


def claim_id(source_ref: str, scope: str = "initial", intent: str = "email") -> str:
    # ``intent`` is accepted for API compatibility and validated, but is not part
    # of the atomic rendezvous key.  This makes the lock cross-channel by default.
    normalize_intent(intent)
    return collision_sha256(source_ref, scope)[:32]


def claim_path(claim: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{32}", claim):
        raise ClaimError("claim_id must be 32 lowercase hex chars")
    return f"ground/outreach-claims/v1/{claim[:2]}/{claim}.json"


def canonical_json(record: Mapping[str, Any]) -> str:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def _base_record(*, source_ref: str, actor: str, scope: str, intent: str,
                 now: dt.datetime, hold_seconds: int, generation: int) -> dict[str, Any]:
    if isinstance(hold_seconds, bool) or not isinstance(hold_seconds, int) or not 15 <= hold_seconds <= 3600:
        raise ClaimError("hold_seconds must be an integer from 15 through 3600")
    source = normalize_source_ref(source_ref)
    actor_n = _token("actor", actor)
    scope_n = normalize_scope(scope)
    intent_n = normalize_intent(intent)
    cid = claim_id(source, scope_n, intent_n)
    held_at = parse_time(now)
    hold_until = held_at + dt.timedelta(seconds=hold_seconds)
    return {
        "schema": SCHEMA,
        "claim_id": cid,
        "source_fingerprint": source_fingerprint(source),
        "collision_sha256": collision_sha256(source, scope_n),
        "identity_sha256": identity_sha256(source, scope_n, intent_n),
        "scope": scope_n,
        "intent": intent_n,
        "state": "HELD",
        "generation": generation,
        "actor": actor_n,
        "held_at": fmt_time(held_at),
        "hold_until": fmt_time(hold_until),
        "committed_at": None,
        "draft_sha256": None,
        "sent_at": None,
        "send_evidence": None,
        "released_at": None,
        "release_reason": None,
    }


def new_claim(*, source_ref: str, actor: str, scope: str = "initial", intent: str = "email",
              now: str | dt.datetime | None = None, hold_seconds: int = 120) -> dict[str, Any]:
    return _base_record(source_ref=source_ref, actor=actor, scope=scope, intent=intent,
                        now=parse_time(now), hold_seconds=hold_seconds, generation=1)


def _expected_keys() -> set[str]:
    return {
        "schema", "claim_id", "source_fingerprint", "collision_sha256", "identity_sha256", "scope", "intent", "state",
        "generation", "actor", "held_at", "hold_until", "committed_at", "draft_sha256",
        "sent_at", "send_evidence", "released_at", "release_reason",
    }


def validate_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise ClaimError("record must be a JSON object")
    extra = set(record) - _expected_keys()
    missing = _expected_keys() - set(record)
    if extra or missing:
        raise ClaimError(f"record keys mismatch missing={sorted(missing)} extra={sorted(extra)}")
    out = copy.deepcopy(dict(record))
    if out["schema"] != SCHEMA:
        raise ClaimError("unknown schema")
    if not re.fullmatch(r"[0-9a-f]{32}", str(out["claim_id"])):
        raise ClaimError("invalid claim_id")
    if not SHA256_RE.fullmatch(str(out["source_fingerprint"])):
        raise ClaimError("invalid source_fingerprint")
    if not SHA256_RE.fullmatch(str(out["collision_sha256"])):
        raise ClaimError("invalid collision_sha256")
    if not SHA256_RE.fullmatch(str(out["identity_sha256"])):
        raise ClaimError("invalid identity_sha256")
    scope_n = normalize_scope(out["scope"])
    intent_n = normalize_intent(out["intent"])
    if out["scope"] != scope_n or out["intent"] != intent_n:
        raise ClaimError("scope and intent must use canonical lowercase values")
    expected_collision = collision_sha256_from_fingerprint(out["source_fingerprint"], scope_n)
    if out["collision_sha256"] != expected_collision:
        raise ClaimError("collision_sha256 does not match source_fingerprint/scope")
    if out["claim_id"] != expected_collision[:32]:
        raise ClaimError("claim_id does not match collision_sha256")
    expected_identity = identity_sha256_from_fingerprint(out["source_fingerprint"], scope_n, intent_n)
    if out["identity_sha256"] != expected_identity:
        raise ClaimError("identity_sha256 does not match source_fingerprint/scope/intent")
    if out["state"] not in ALLOWED_STATES:
        raise ClaimError("invalid state")
    if isinstance(out["generation"], bool) or not isinstance(out["generation"], int) or out["generation"] < 1:
        raise ClaimError("generation must be positive integer")
    _token("actor", out["actor"])
    held_at = parse_time(out["held_at"])

    state = out["state"]
    if state == "HELD":
        hu = parse_time(out["hold_until"])
        if hu <= held_at:
            raise ClaimError("hold_until must be after held_at")
        for name in ("committed_at", "draft_sha256", "sent_at", "send_evidence", "released_at", "release_reason"):
            if out[name] is not None:
                raise ClaimError(f"HELD record must have {name}=null")
    elif state == "COMMITTED":
        if out["hold_until"] is not None:
            raise ClaimError("COMMITTED record must have hold_until=null")
        committed = parse_time(out["committed_at"])
        if committed < held_at:
            raise ClaimError("committed_at cannot precede held_at")
        if not SHA256_RE.fullmatch(str(out["draft_sha256"])):
            raise ClaimError("COMMITTED record requires draft_sha256")
        for name in ("sent_at", "send_evidence", "released_at", "release_reason"):
            if out[name] is not None:
                raise ClaimError(f"COMMITTED record must have {name}=null")
    elif state == "SENT":
        if out["hold_until"] is not None:
            raise ClaimError("SENT record must have hold_until=null")
        committed = parse_time(out["committed_at"])
        sent = parse_time(out["sent_at"])
        if committed < held_at or sent < committed:
            raise ClaimError("invalid SENT chronology")
        if not SHA256_RE.fullmatch(str(out["draft_sha256"])):
            raise ClaimError("SENT record requires draft_sha256")
        _token("send_evidence", out["send_evidence"], OPAQUE_RE)
        if out["released_at"] is not None or out["release_reason"] is not None:
            raise ClaimError("SENT record cannot be released")
    elif state == "RELEASED":
        if out["hold_until"] is not None:
            raise ClaimError("RELEASED record must have hold_until=null")
        released = parse_time(out["released_at"])
        if released < held_at:
            raise ClaimError("released_at cannot precede held_at")
        _token("release_reason", out["release_reason"], TOKEN_RE)
        for name in ("committed_at", "draft_sha256", "sent_at", "send_evidence"):
            if out[name] is not None:
                raise ClaimError(f"RELEASED record must have {name}=null")
    return out


def _require_owner(record: Mapping[str, Any], actor: str) -> str:
    actor_n = _token("actor", actor)
    if actor_n != record["actor"]:
        raise ClaimError(f"actor {actor_n!r} does not own generation {record['generation']}")
    return actor_n


def commit_claim(record: Mapping[str, Any], *, actor: str, draft_sha256: str,
                 now: str | dt.datetime | None = None) -> dict[str, Any]:
    out = validate_record(record)
    _require_owner(out, actor)
    if out["state"] != "HELD":
        raise ClaimError("only HELD may transition to COMMITTED")
    t = parse_time(now)
    if t > parse_time(out["hold_until"]):
        raise ClaimError("hold expired; reacquire with takeover before commit")
    digest = str(draft_sha256).lower()
    if not SHA256_RE.fullmatch(digest):
        raise ClaimError("draft_sha256 must be 64 lowercase hex chars")
    out.update({
        "state": "COMMITTED",
        "hold_until": None,
        "committed_at": fmt_time(t),
        "draft_sha256": digest,
    })
    return validate_record(out)


def mark_sent(record: Mapping[str, Any], *, actor: str, evidence: str,
              now: str | dt.datetime | None = None) -> dict[str, Any]:
    out = validate_record(record)
    _require_owner(out, actor)
    if out["state"] != "COMMITTED":
        raise ClaimError("only COMMITTED may transition to SENT")
    evidence_n = _token("send_evidence", evidence, OPAQUE_RE)
    t = parse_time(now)
    if t < parse_time(out["committed_at"]):
        raise ClaimError("sent_at cannot precede committed_at")
    out.update({"state": "SENT", "sent_at": fmt_time(t), "send_evidence": evidence_n})
    return validate_record(out)


def release_claim(record: Mapping[str, Any], *, actor: str, reason: str,
                  now: str | dt.datetime | None = None) -> dict[str, Any]:
    out = validate_record(record)
    _require_owner(out, actor)
    if out["state"] != "HELD":
        raise ClaimError("only HELD may transition to RELEASED; COMMITTED is a no-takeover barrier")
    reason_n = _token("release_reason", reason, TOKEN_RE)
    t = parse_time(now)
    if t < parse_time(out["held_at"]):
        raise ClaimError("released_at cannot precede held_at")
    out.update({
        "state": "RELEASED",
        "hold_until": None,
        "released_at": fmt_time(t),
        "release_reason": reason_n,
    })
    return validate_record(out)


def takeover_claim(record: Mapping[str, Any], *, new_actor: str,
                   now: str | dt.datetime | None = None, hold_seconds: int = 120) -> dict[str, Any]:
    current = validate_record(record)
    t = parse_time(now)
    allowed = current["state"] == "RELEASED"
    if current["state"] == "HELD" and t > parse_time(current["hold_until"]):
        allowed = True
    if not allowed:
        raise ClaimError("takeover allowed only for RELEASED or expired HELD records")
    # We cannot recover the raw source ref by design; preserve the committed
    # fingerprint/claim id and construct the next generation directly.
    if isinstance(hold_seconds, bool) or not isinstance(hold_seconds, int) or not 15 <= hold_seconds <= 3600:
        raise ClaimError("hold_seconds must be an integer from 15 through 3600")
    actor_n = _token("new_actor", new_actor)
    next_record = {
        "schema": SCHEMA,
        "claim_id": current["claim_id"],
        "source_fingerprint": current["source_fingerprint"],
        "collision_sha256": current["collision_sha256"],
        "identity_sha256": current["identity_sha256"],
        "scope": current["scope"],
        "intent": current["intent"],
        "state": "HELD",
        "generation": current["generation"] + 1,
        "actor": actor_n,
        "held_at": fmt_time(t),
        "hold_until": fmt_time(t + dt.timedelta(seconds=hold_seconds)),
        "committed_at": None,
        "draft_sha256": None,
        "sent_at": None,
        "send_evidence": None,
        "released_at": None,
        "release_reason": None,
    }
    return validate_record(next_record)


def decision(record: Mapping[str, Any], *, actor: str | None = None,
             now: str | dt.datetime | None = None) -> dict[str, Any]:
    out = validate_record(record)
    t = parse_time(now)
    own = actor is not None and _token("actor", actor) == out["actor"]
    state = out["state"]
    if state == "SENT":
        code = "BLOCKED_ALREADY_SENT"
        may_send = False
    elif state == "COMMITTED":
        code = "OWNER_MAY_SEND" if own else "BLOCKED_COMMITTED_BY_OTHER"
        may_send = bool(own)
    elif state == "RELEASED":
        code = "AVAILABLE_RELEASED"
        may_send = False
    elif t > parse_time(out["hold_until"]):
        code = "AVAILABLE_EXPIRED_HOLD"
        may_send = False
    else:
        code = "OWNER_MAY_COMMIT" if own else "BLOCKED_HELD_BY_OTHER"
        may_send = False
    return {
        "claim_id": out["claim_id"],
        "generation": out["generation"],
        "state": state,
        "owner": out["actor"],
        "code": code,
        "may_send": may_send,
    }


def load_record(path: str | Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ClaimError(f"cannot read record {path}: {exc}") from exc
    return validate_record(data)


def _dump(value: Any) -> None:
    sys.stdout.write(canonical_json(value) if isinstance(value, Mapping) else json.dumps(value, sort_keys=True) + "\n")


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="collision-free swarm outreach claim state machine")
    sub = p.add_subparsers(dest="cmd", required=True)

    fp = sub.add_parser("fingerprint")
    fp.add_argument("--source-ref", required=True)
    fp.add_argument("--scope", default="initial")
    fp.add_argument("--intent", default="email", choices=sorted(ALLOWED_INTENTS))

    new = sub.add_parser("new")
    new.add_argument("--source-ref", required=True)
    new.add_argument("--actor", required=True)
    new.add_argument("--scope", default="initial")
    new.add_argument("--intent", default="email", choices=sorted(ALLOWED_INTENTS))
    new.add_argument("--now")
    new.add_argument("--hold-seconds", type=int, default=120)

    check = sub.add_parser("check")
    check.add_argument("--input", required=True)
    check.add_argument("--actor")
    check.add_argument("--now")

    verify = sub.add_parser("verify")
    verify.add_argument("--input", required=True)

    transition = sub.add_parser("transition")
    transition.add_argument("--input", required=True)
    transition.add_argument("--action", required=True, choices=["commit", "sent", "release", "takeover"])
    transition.add_argument("--actor", required=True)
    transition.add_argument("--now")
    transition.add_argument("--draft-sha256")
    transition.add_argument("--evidence")
    transition.add_argument("--reason")
    transition.add_argument("--hold-seconds", type=int, default=120)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.cmd == "fingerprint":
            cid = claim_id(args.source_ref, args.scope, args.intent)
            _dump({"claim_id": cid, "path": claim_path(cid), "scope": normalize_scope(args.scope), "intent": normalize_intent(args.intent)})
        elif args.cmd == "new":
            rec = new_claim(source_ref=args.source_ref, actor=args.actor, scope=args.scope, intent=args.intent,
                            now=args.now, hold_seconds=args.hold_seconds)
            _dump({"path": claim_path(rec["claim_id"]), "record": rec})
        elif args.cmd == "verify":
            rec = load_record(args.input)
            _dump({"ok": True, "claim_id": rec["claim_id"], "state": rec["state"], "generation": rec["generation"]})
        elif args.cmd == "check":
            _dump(decision(load_record(args.input), actor=args.actor, now=args.now))
        elif args.cmd == "transition":
            rec = load_record(args.input)
            if args.action == "commit":
                if not args.draft_sha256:
                    raise ClaimError("--draft-sha256 is required for commit")
                rec = commit_claim(rec, actor=args.actor, draft_sha256=args.draft_sha256, now=args.now)
            elif args.action == "sent":
                if not args.evidence:
                    raise ClaimError("--evidence is required for sent")
                rec = mark_sent(rec, actor=args.actor, evidence=args.evidence, now=args.now)
            elif args.action == "release":
                if not args.reason:
                    raise ClaimError("--reason is required for release")
                rec = release_claim(rec, actor=args.actor, reason=args.reason, now=args.now)
            else:
                rec = takeover_claim(rec, new_actor=args.actor, now=args.now, hold_seconds=args.hold_seconds)
            _dump({"path": claim_path(rec["claim_id"]), "record": rec})
        return 0
    except ClaimError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
