#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

INTENT_SCHEMA = "outbound-send-authority-intent/v1"
RECEIPT_SCHEMA = "outbound-send-authority-receipt/v1"
GUARD_SCHEMA = "outbound-send-guard-receipt/v1"
LEASE_SCHEMA = "outbound-send-lease-receipt/v1"
LEASE_SEAM_SCHEMA = "outbound-send-lease/v1"
DEFAULT_MAX_AGE_SECONDS = 300
DEFAULT_MAX_FUTURE_SKEW_SECONDS = 30
MAX_INPUT_BYTES = 2 * 1024 * 1024
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_MACHINE = re.compile(r"^[a-z0-9][a-z0-9._:@/+\-]{2,191}$")


class AuthorityError(ValueError):
    pass


class DuplicateKeyError(AuthorityError):
    pass


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise AuthorityError(f"{label} must be an object")
    return value


def _require_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise AuthorityError(f"{label} must be a boolean")
    return value


def _require_int(value: Any, label: str, lo: int, hi: int) -> int:
    if type(value) is not int or not lo <= value <= hi:
        raise AuthorityError(f"{label} must be an integer in [{lo},{hi}]")
    return value


def _require_text(value: Any, label: str, max_len: int = 256) -> str:
    if type(value) is not str or not value or len(value) > max_len:
        raise AuthorityError(f"{label} must be non-empty text <= {max_len} chars")
    if any(ord(ch) < 0x20 or ch == "\x7f" for ch in value):
        raise AuthorityError(f"{label} contains control characters")
    return value


def _require_machine(value: Any, label: str) -> str:
    text = _require_text(value, label, 192)
    if not text.isascii() or text != text.casefold() or _MACHINE.fullmatch(text) is None:
        raise AuthorityError(f"{label} must be a lowercase ASCII machine token")
    return text


def _require_hex64(value: Any, label: str) -> str:
    text = _require_text(value, label, 64)
    if _HEX64.fullmatch(text) is None:
        raise AuthorityError(f"{label} must be lowercase sha256 hex")
    return text


def _time(value: Any, label: str) -> datetime:
    text = _require_text(value, label, 64)
    raw = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise AuthorityError(f"{label} must be RFC3339") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise AuthorityError(f"{label} must include timezone")
    return dt.astimezone(timezone.utc)


def _fmt(dt: datetime) -> str:
    dt = dt.astimezone(timezone.utc)
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def _loads(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_INPUT_BYTES:
        raise AuthorityError(f"{label} must be 1..{MAX_INPUT_BYTES} bytes")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise AuthorityError(f"{label} must be UTF-8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                AuthorityError(f"{label} contains non-finite number {token}")
            ),
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise AuthorityError(f"{label} is invalid JSON") from exc
    return _require_dict(value, label)


def _canon(value: Any, *, newline: bool = False, ascii_only: bool = False) -> bytes:
    try:
        body = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=ascii_only,
            allow_nan=False,
        ).encode("ascii" if ascii_only else "utf-8")
    except (TypeError, ValueError) as exc:
        raise AuthorityError("value is not canonical JSON") from exc
    return body + (b"\n" if newline else b"")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha_object(value: Any, *, newline: bool = False, ascii_only: bool = False) -> str:
    return _sha(_canon(value, newline=newline, ascii_only=ascii_only))


def _exact_keys(obj: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(obj)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise AuthorityError(f"{label} keys mismatch missing={missing} extra={extra}")


def _parse_intent(raw: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "schema_version", "buyer_scope", "offer_scope", "recipient_sha256",
        "claimant", "claim_id", "requested_at", "route_kind",
        "guard_receipt_sha256", "lease_receipt_sha256",
    }
    _exact_keys(raw, expected, "intent")
    if raw["schema_version"] != INTENT_SCHEMA:
        raise AuthorityError(f"intent.schema_version must be {INTENT_SCHEMA}")
    route = _require_machine(raw["route_kind"], "intent.route_kind")
    if route != "email":
        raise AuthorityError("intent.route_kind must be email")
    return {
        "schema_version": INTENT_SCHEMA,
        "buyer_scope": _require_machine(raw["buyer_scope"], "intent.buyer_scope"),
        "offer_scope": _require_machine(raw["offer_scope"], "intent.offer_scope"),
        "recipient_sha256": _require_hex64(raw["recipient_sha256"], "intent.recipient_sha256"),
        "claimant": _require_text(raw["claimant"], "intent.claimant", 192),
        "claim_id": _require_machine(raw["claim_id"], "intent.claim_id"),
        "requested_at": _time(raw["requested_at"], "intent.requested_at"),
        "route_kind": "email",
        "guard_receipt_sha256": _require_hex64(raw["guard_receipt_sha256"], "intent.guard_receipt_sha256"),
        "lease_receipt_sha256": _require_hex64(raw["lease_receipt_sha256"], "intent.lease_receipt_sha256"),
    }


def _parse_guard(raw: dict[str, Any]) -> dict[str, Any]:
    _exact_keys(raw, {"payload", "receipt_sha256"}, "guard receipt")
    payload = _require_dict(raw["payload"], "guard receipt.payload")
    receipt_sha = _require_hex64(raw["receipt_sha256"], "guard receipt.receipt_sha256")
    if _sha_object(payload, newline=True, ascii_only=False) != receipt_sha:
        raise AuthorityError("guard receipt digest mismatch")
    required_payload = {
        "schema_version", "intent", "evidence", "policy", "decision", "authority",
        "reasons", "latest_outbound_at", "latest_inbound_at", "reply_message_id",
        "side_effects_authorized",
    }
    _exact_keys(payload, required_payload, "guard receipt.payload")
    if payload["schema_version"] != GUARD_SCHEMA:
        raise AuthorityError("unsupported guard receipt schema")
    intent = _require_dict(payload["intent"], "guard receipt.payload.intent")
    _exact_keys(intent, {"intent_id", "recipient", "offer_id", "requested_at", "route_kind"}, "guard receipt.payload.intent")
    evidence = _require_dict(payload["evidence"], "guard receipt.payload.evidence")
    _exact_keys(
        evidence,
        {"generated_at", "mailbox_complete", "mailbox_query_id", "slack_complete", "slack_query_id", "intent_sha256", "evidence_sha256", "matched_refs"},
        "guard receipt.payload.evidence",
    )
    if payload["decision"] not in {"ALLOW_NEW", "REPLY_ONLY", "HOLD", "DO_NOT_RESEND"}:
        raise AuthorityError("guard receipt decision invalid")
    if payload["authority"] not in {"complete", "partial", "unknown"}:
        raise AuthorityError("guard receipt authority invalid")
    _require_bool(payload["side_effects_authorized"], "guard receipt.payload.side_effects_authorized")
    _require_bool(evidence["mailbox_complete"], "guard receipt.payload.evidence.mailbox_complete")
    _require_bool(evidence["slack_complete"], "guard receipt.payload.evidence.slack_complete")
    if type(payload["reasons"]) is not list or type(evidence["matched_refs"]) is not list:
        raise AuthorityError("guard receipt list fields malformed")
    recipient = _require_text(intent["recipient"], "guard receipt.payload.intent.recipient", 320).casefold()
    return {
        "receipt_sha256": receipt_sha,
        "decision": payload["decision"],
        "authority": payload["authority"],
        "side_effects_authorized": payload["side_effects_authorized"],
        "mailbox_complete": evidence["mailbox_complete"],
        "slack_complete": evidence["slack_complete"],
        "recipient_sha256": _sha(recipient.encode("utf-8")),
        "offer_id": _require_text(intent["offer_id"], "guard receipt.payload.intent.offer_id", 200),
        "requested_at": _time(intent["requested_at"], "guard receipt.payload.intent.requested_at"),
        "generated_at": _time(evidence["generated_at"], "guard receipt.payload.evidence.generated_at"),
        "route_kind": _require_text(intent["route_kind"], "guard receipt.payload.intent.route_kind", 32),
    }


def _parse_lease(raw: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "schema", "seam_sha256", "lease_ref", "claim_id", "claimant",
        "claim_started_at", "preflight_sha256", "tag_object_sha", "observed_ref_sha",
        "lease_held_by_claimant", "decision", "reason", "external_send_authorized",
        "receipt_sha256",
    }
    _exact_keys(raw, expected, "lease receipt")
    if raw["schema"] != LEASE_SCHEMA:
        raise AuthorityError("unsupported lease receipt schema")
    digest = _require_hex64(raw["receipt_sha256"], "lease receipt.receipt_sha256")
    material = dict(raw)
    del material["receipt_sha256"]
    if _sha_object(material, newline=False, ascii_only=True) != digest:
        raise AuthorityError("lease receipt digest mismatch")
    seam_sha = _require_hex64(raw["seam_sha256"], "lease receipt.seam_sha256")
    if raw["lease_ref"] != f"refs/tags/outbound-lease-v1/{seam_sha}":
        raise AuthorityError("lease ref/seam mismatch")
    held = _require_bool(raw["lease_held_by_claimant"], "lease receipt.lease_held_by_claimant")
    ext = _require_bool(raw["external_send_authorized"], "lease receipt.external_send_authorized")
    observed = raw["observed_ref_sha"]
    tag_sha = _require_text(raw["tag_object_sha"], "lease receipt.tag_object_sha", 64).lower()
    if not re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", tag_sha):
        raise AuthorityError("lease receipt tag_object_sha invalid")
    if observed is not None:
        observed = _require_text(observed, "lease receipt.observed_ref_sha", 64).lower()
        if not re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", observed):
            raise AuthorityError("lease receipt observed_ref_sha invalid")
    if held and observed != tag_sha:
        raise AuthorityError("held lease does not prove exact ref object")
    return {
        "receipt_sha256": digest,
        "seam_sha256": seam_sha,
        "claim_id": _require_machine(raw["claim_id"], "lease receipt.claim_id"),
        "claimant": _require_text(raw["claimant"], "lease receipt.claimant", 192),
        "claim_started_at": _time(raw["claim_started_at"], "lease receipt.claim_started_at"),
        "preflight_sha256": _require_hex64(raw["preflight_sha256"], "lease receipt.preflight_sha256"),
        "held": held,
        "decision": _require_text(raw["decision"], "lease receipt.decision", 32),
        "external_send_authorized": ext,
    }


def _seam_sha(buyer_scope: str, offer_scope: str) -> str:
    seam = {"schema": LEASE_SEAM_SCHEMA, "buyer_scope": buyer_scope, "offer_scope": offer_scope}
    return _sha_object(seam, newline=False, ascii_only=True)


def evaluate_bytes(
    intent_bytes: bytes,
    guard_receipt_bytes: bytes,
    lease_receipt_bytes: bytes,
    *,
    as_of: datetime,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    max_future_skew_seconds: int = DEFAULT_MAX_FUTURE_SKEW_SECONDS,
) -> dict[str, Any]:
    if type(as_of) is not datetime or as_of.tzinfo is None or as_of.utcoffset() is None:
        raise AuthorityError("as_of must be timezone-aware datetime")
    as_of = as_of.astimezone(timezone.utc)
    max_age_seconds = _require_int(max_age_seconds, "max_age_seconds", 0, 86400)
    max_future_skew_seconds = _require_int(max_future_skew_seconds, "max_future_skew_seconds", 0, 3600)

    intent = _parse_intent(_loads(intent_bytes, "intent"))
    guard = _parse_guard(_loads(guard_receipt_bytes, "guard receipt"))
    lease = _parse_lease(_loads(lease_receipt_bytes, "lease receipt"))

    reasons: list[str] = []
    if _sha(guard_receipt_bytes) != intent["guard_receipt_sha256"]:
        reasons.append("GUARD_RECEIPT_BYTES_MISMATCH")
    if _sha(lease_receipt_bytes) != intent["lease_receipt_sha256"]:
        reasons.append("LEASE_RECEIPT_BYTES_MISMATCH")
    if guard["decision"] != "ALLOW_NEW":
        reasons.append("GUARD_NOT_ALLOW_NEW")
    if guard["authority"] != "complete" or not guard["mailbox_complete"] or not guard["slack_complete"]:
        reasons.append("GUARD_AUTHORITY_INCOMPLETE")
    if guard["side_effects_authorized"] is not False:
        reasons.append("GUARD_AUTHORITY_BIT_INVALID")
    if guard["route_kind"] != "email":
        reasons.append("GUARD_ROUTE_MISMATCH")
    if guard["offer_id"] != intent["offer_scope"]:
        reasons.append("GUARD_OFFER_MISMATCH")
    if guard["recipient_sha256"] != intent["recipient_sha256"]:
        reasons.append("GUARD_RECIPIENT_MISMATCH")
    if guard["requested_at"] != intent["requested_at"]:
        reasons.append("GUARD_REQUEST_TIME_MISMATCH")
    if lease["decision"] != "LEASE_HELD" or not lease["held"]:
        reasons.append("LEASE_NOT_HELD")
    if lease["external_send_authorized"] is not False:
        reasons.append("LEASE_AUTHORITY_BIT_INVALID")
    if lease["claimant"] != intent["claimant"]:
        reasons.append("LEASE_CLAIMANT_MISMATCH")
    if lease["claim_id"] != intent["claim_id"]:
        reasons.append("LEASE_CLAIM_ID_MISMATCH")
    if lease["seam_sha256"] != _seam_sha(intent["buyer_scope"], intent["offer_scope"]):
        reasons.append("LEASE_SEAM_MISMATCH")
    if lease["preflight_sha256"] != guard["receipt_sha256"]:
        reasons.append("PREFLIGHT_RECEIPT_MISMATCH")

    skew = timedelta(seconds=max_future_skew_seconds)
    age = timedelta(seconds=max_age_seconds)
    for label, ts in (
        ("REQUEST", intent["requested_at"]),
        ("GUARD", guard["generated_at"]),
        ("LEASE", lease["claim_started_at"]),
    ):
        if ts - as_of > skew:
            reasons.append(f"{label}_FUTURE")
        elif as_of - ts > age:
            reasons.append(f"{label}_STALE")
    if lease["claim_started_at"] < guard["generated_at"] - skew:
        reasons.append("LEASE_PREDATES_PREFLIGHT")

    reasons = sorted(set(reasons))
    decision = "SEND_READY" if not reasons else "HOLD"
    payload = {
        "schema_version": RECEIPT_SCHEMA,
        "decision": decision,
        "external_send_authorized": decision == "SEND_READY",
        "buyer_scope": intent["buyer_scope"],
        "offer_scope": intent["offer_scope"],
        "recipient_sha256": intent["recipient_sha256"],
        "claimant": intent["claimant"],
        "claim_id": intent["claim_id"],
        "requested_at": _fmt(intent["requested_at"]),
        "as_of": _fmt(as_of),
        "guard_receipt_sha256": intent["guard_receipt_sha256"],
        "guard_payload_receipt_sha256": guard["receipt_sha256"],
        "lease_receipt_sha256": intent["lease_receipt_sha256"],
        "lease_payload_receipt_sha256": lease["receipt_sha256"],
        "lease_seam_sha256": lease["seam_sha256"],
        "reasons": reasons,
        "policy": {
            "max_age_seconds": max_age_seconds,
            "max_future_skew_seconds": max_future_skew_seconds,
        },
    }
    return {"payload": payload, "receipt_sha256": _sha_object(payload, newline=True, ascii_only=False)}


def verify_receipt_bytes(
    receipt_bytes: bytes,
    intent_bytes: bytes,
    guard_receipt_bytes: bytes,
    lease_receipt_bytes: bytes,
    *,
    as_of: datetime,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    max_future_skew_seconds: int = DEFAULT_MAX_FUTURE_SKEW_SECONDS,
) -> bool:
    supplied = _loads(receipt_bytes, "authority receipt")
    _exact_keys(supplied, {"payload", "receipt_sha256"}, "authority receipt")
    _require_hex64(supplied["receipt_sha256"], "authority receipt.receipt_sha256")
    if _sha_object(_require_dict(supplied["payload"], "authority receipt.payload"), newline=True) != supplied["receipt_sha256"]:
        raise AuthorityError("authority receipt digest mismatch")
    expected = evaluate_bytes(
        intent_bytes, guard_receipt_bytes, lease_receipt_bytes,
        as_of=as_of,
        max_age_seconds=max_age_seconds,
        max_future_skew_seconds=max_future_skew_seconds,
    )
    if supplied != expected:
        raise AuthorityError("authority receipt does not recompile from exact inputs/policy/time")
    return True


def _read_regular(path: Path, label: str) -> bytes:
    try:
        st = os.lstat(path)
    except OSError as exc:
        raise AuthorityError(f"{label}: cannot stat input") from exc
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise AuthorityError(f"{label}: input must be a regular non-symlink file")
    if st.st_size <= 0 or st.st_size > MAX_INPUT_BYTES:
        raise AuthorityError(f"{label}: invalid input size")
    return path.read_bytes()


def _publish_exclusive(path: Path, raw: bytes) -> None:
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise AuthorityError("output already exists")
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(raw)
            fh.flush()
            os.fsync(fh.fileno())
        if path.exists() or path.is_symlink():
            raise AuthorityError("output appeared during publication")
        os.link(temp_name, path)
        dir_fd = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile one atomic pre-send authority receipt")
    parser.add_argument("--intent", type=Path, required=True)
    parser.add_argument("--guard-receipt", type=Path, required=True)
    parser.add_argument("--lease-receipt", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--as-of", help="trusted RFC3339 current time; default: process UTC now")
    parser.add_argument("--max-age-seconds", type=int, default=DEFAULT_MAX_AGE_SECONDS)
    parser.add_argument("--max-future-skew-seconds", type=int, default=DEFAULT_MAX_FUTURE_SKEW_SECONDS)
    args = parser.parse_args(argv)
    try:
        as_of = _time(args.as_of, "as_of") if args.as_of else datetime.now(timezone.utc)
        intent_bytes = _read_regular(args.intent, "intent")
        guard_bytes = _read_regular(args.guard_receipt, "guard receipt")
        lease_bytes = _read_regular(args.lease_receipt, "lease receipt")
        receipt = evaluate_bytes(
            intent_bytes, guard_bytes, lease_bytes,
            as_of=as_of,
            max_age_seconds=args.max_age_seconds,
            max_future_skew_seconds=args.max_future_skew_seconds,
        )
        encoded = json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
        if args.out is None:
            sys.stdout.buffer.write(encoded)
        else:
            for input_path in (args.intent, args.guard_receipt, args.lease_receipt):
                try:
                    if os.path.samefile(args.out, input_path):
                        raise AuthorityError("output aliases an input")
                except FileNotFoundError:
                    pass
            _publish_exclusive(args.out, encoded)
        return 0 if receipt["payload"]["decision"] == "SEND_READY" else 4
    except (OSError, AuthorityError) as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
