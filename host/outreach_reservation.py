#!/usr/bin/env python3
"""Collision-safe outreach reservation ledger helpers.

This module intentionally does not send outreach and does not claim that a local
file write reserves anything. The authority boundary is a successful
compare-and-swap update of the canonical ledger on GitHub ``main`` using the
blob SHA returned by the prior read.

Two senders that read the same ledger SHA may both prepare a reservation, but
only one can update that exact blob revision. A failed/stale update is STOP:
refresh the canonical ledger, re-run conflict checks, and do not transport.
"""
from __future__ import annotations

import argparse
import copy
import datetime as _dt
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

KIND = "OUTREACH_RESERVATION_LEDGER"
SCHEMA_VERSION = 1
ACTIVE_STATES = frozenset({"RESERVED", "SENT_DNR"})
TERMINAL_DNR_STATE = "SENT_DNR"
RELEASED_STATE = "RELEASED"
VALID_STATES = ACTIVE_STATES | {RELEASED_STATE}
FINGERPRINT_KINDS = frozenset({"org", "recipient", "lead"})
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ReservationError(ValueError):
    """Malformed ledger or invalid state transition."""


class ReservationConflict(ReservationError):
    """A live or permanent reservation already covers this identity."""

    def __init__(self, conflicts):
        self.conflicts = tuple(conflicts)
        ids = ", ".join(str(item.get("reservation_id") or "?") for item in conflicts)
        super().__init__(f"outreach identity is already reserved/DNR: {ids}")


def _text(value):
    return unicodedata.normalize("NFKC", str(value or "")).strip()


def normalize_org(value):
    value = _text(value).casefold()
    value = re.sub(r"[\W_]+", "-", value, flags=re.UNICODE).strip("-")
    if not value:
        raise ReservationError("organization key must contain a visible token")
    return value


def normalize_recipient(value):
    value = _text(value).casefold()
    if not value or value.count("@") != 1:
        raise ReservationError("recipient must be one email address")
    local, domain = value.rsplit("@", 1)
    if not local or not domain or "." not in domain:
        raise ReservationError("recipient must be one email address")
    return value


def normalize_lead_ref(value):
    value = _text(value).casefold()
    if not value:
        raise ReservationError("lead reference must not be empty")
    return value


def _digest(kind, normalized):
    if kind not in FINGERPRINT_KINDS:
        raise ReservationError(f"unsupported fingerprint kind: {kind}")
    return f"{kind}:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"


def identity_fingerprints(org_key, recipient=None, lead_ref=None, org_aliases=()):
    """Return sorted, secret-absent hashes for every collision identity.

    Organization collisions are intentional even when two agents choose
    different people at the same company. Recipient and lead fingerprints give
    additional protection against organization spelling drift.
    """
    values = {_digest("org", normalize_org(org_key))}
    for alias in org_aliases or ():
        values.add(_digest("org", normalize_org(alias)))
    if recipient:
        values.add(_digest("recipient", normalize_recipient(recipient)))
    if lead_ref:
        values.add(_digest("lead", normalize_lead_ref(lead_ref)))
    return sorted(values)


def _parse_time(value, field):
    text = _text(value)
    if not text:
        raise ReservationError(f"{field} must be an RFC3339 timestamp")
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = _dt.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ReservationError(f"{field} must be an RFC3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise ReservationError(f"{field} must include an offset")
    return parsed.astimezone(_dt.timezone.utc)


def utc_now():
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate_fingerprint(value):
    text = str(value or "")
    if ":" not in text:
        raise ReservationError("fingerprint must be kind:sha256")
    kind, digest = text.split(":", 1)
    if kind not in FINGERPRINT_KINDS or not _HEX64.fullmatch(digest):
        raise ReservationError(f"invalid fingerprint: {text!r}")
    return text


def validate_ledger(ledger):
    if not isinstance(ledger, dict):
        raise ReservationError("ledger must be a JSON object")
    if ledger.get("schema_version") != SCHEMA_VERSION or ledger.get("kind") != KIND:
        raise ReservationError("unsupported outreach reservation ledger")
    claims = ledger.get("claims")
    if not isinstance(claims, list):
        raise ReservationError("claims must be an array")

    seen_ids = set()
    active_by_fp = {}
    for claim in claims:
        if not isinstance(claim, dict):
            raise ReservationError("claim entries must be objects")
        reservation_id = _text(claim.get("reservation_id"))
        if not reservation_id or reservation_id in seen_ids:
            raise ReservationError("reservation_id must be present and unique")
        seen_ids.add(reservation_id)
        state = _text(claim.get("state")).upper()
        if state not in VALID_STATES:
            raise ReservationError(f"{reservation_id}: invalid state {state!r}")
        if not _text(claim.get("owner")):
            raise ReservationError(f"{reservation_id}: owner is required")
        fps = claim.get("fingerprints")
        if not isinstance(fps, list) or not fps:
            raise ReservationError(f"{reservation_id}: fingerprints must be non-empty")
        normalized_fps = [_validate_fingerprint(item) for item in fps]
        if len(set(normalized_fps)) != len(normalized_fps):
            raise ReservationError(f"{reservation_id}: duplicate fingerprint")
        _parse_time(claim.get("claimed_at"), f"{reservation_id}.claimed_at")
        sent_at = claim.get("sent_at")
        released_at = claim.get("released_at")
        if state == TERMINAL_DNR_STATE:
            if not sent_at:
                raise ReservationError(f"{reservation_id}: SENT_DNR requires sent_at")
            _parse_time(sent_at, f"{reservation_id}.sent_at")
            if released_at is not None:
                raise ReservationError(f"{reservation_id}: SENT_DNR cannot be released")
        elif state == RELEASED_STATE:
            if not released_at:
                raise ReservationError(f"{reservation_id}: RELEASED requires released_at")
            _parse_time(released_at, f"{reservation_id}.released_at")
            if sent_at is not None:
                raise ReservationError(f"{reservation_id}: RELEASED cannot have sent_at")
        else:
            if sent_at is not None or released_at is not None:
                raise ReservationError(f"{reservation_id}: RESERVED cannot have sent/released time")

        if state in ACTIVE_STATES:
            for fingerprint in normalized_fps:
                prior = active_by_fp.get(fingerprint)
                if prior is not None:
                    raise ReservationError(
                        f"active identity collision inside ledger: {prior} and {reservation_id}"
                    )
                active_by_fp[fingerprint] = reservation_id
    return ledger


def load_ledger(path):
    with open(path, encoding="utf-8") as handle:
        ledger = json.load(handle)
    return validate_ledger(ledger)


def conflicts_for(ledger, fingerprints, exclude_id=None):
    validate_ledger(ledger)
    wanted = set(fingerprints)
    matches = []
    for claim in ledger["claims"]:
        if claim.get("reservation_id") == exclude_id:
            continue
        if str(claim.get("state") or "").upper() not in ACTIVE_STATES:
            continue
        if wanted.intersection(claim.get("fingerprints") or []):
            matches.append(claim)
    return matches


def _new_reservation_id(owner, fingerprints, claimed_at):
    material = "\0".join([_text(owner), claimed_at] + sorted(fingerprints))
    return "outreach-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def prepare_reservation(
    ledger,
    *,
    org_key,
    owner,
    recipient=None,
    lead_ref=None,
    org_aliases=(),
    claimed_at=None,
):
    """Prepare a replacement ledger; this is NOT authority to send.

    The returned replacement gains authority only after a successful canonical
    GitHub ``main`` update against the blob SHA used to read ``ledger``.
    """
    validate_ledger(ledger)
    owner = _text(owner)
    if not owner:
        raise ReservationError("owner is required")
    claimed_at = claimed_at or utc_now()
    _parse_time(claimed_at, "claimed_at")
    fingerprints = identity_fingerprints(
        org_key, recipient=recipient, lead_ref=lead_ref, org_aliases=org_aliases
    )
    conflicts = conflicts_for(ledger, fingerprints)
    if conflicts:
        raise ReservationConflict(conflicts)

    result = copy.deepcopy(ledger)
    reservation_id = _new_reservation_id(owner, fingerprints, claimed_at)
    if any(item.get("reservation_id") == reservation_id for item in result["claims"]):
        raise ReservationError("reservation id collision; refresh or use a later claimed_at")
    result["claims"].append(
        {
            "reservation_id": reservation_id,
            "state": "RESERVED",
            "owner": owner,
            "fingerprints": fingerprints,
            "claimed_at": claimed_at,
            "sent_at": None,
            "released_at": None,
            "source_ref": "github-main-cas",
        }
    )
    validate_ledger(result)
    return result, reservation_id


def assert_send_authority(
    ledger,
    *,
    reservation_id,
    owner,
    org_key,
    recipient=None,
    lead_ref=None,
    org_aliases=(),
):
    """Fail closed unless canonical main still contains this exact reservation."""
    validate_ledger(ledger)
    wanted = set(
        identity_fingerprints(
            org_key, recipient=recipient, lead_ref=lead_ref, org_aliases=org_aliases
        )
    )
    owner = _text(owner)
    matches = [c for c in ledger["claims"] if c.get("reservation_id") == reservation_id]
    if len(matches) != 1:
        raise ReservationError("reservation is absent from canonical ledger")
    claim = matches[0]
    if claim.get("state") != "RESERVED":
        raise ReservationError(f"reservation is not sendable: state={claim.get('state')}")
    if claim.get("owner") != owner:
        raise ReservationError("reservation owner mismatch")
    if set(claim.get("fingerprints") or []) != wanted:
        raise ReservationError("reservation identity mismatch")
    other = conflicts_for(ledger, wanted, exclude_id=reservation_id)
    if other:
        raise ReservationConflict(other)
    return claim


def mark_sent(ledger, *, reservation_id, owner, sent_at=None, source_ref=None):
    validate_ledger(ledger)
    result = copy.deepcopy(ledger)
    owner = _text(owner)
    sent_at = sent_at or utc_now()
    _parse_time(sent_at, "sent_at")
    found = None
    for claim in result["claims"]:
        if claim.get("reservation_id") == reservation_id:
            found = claim
            break
    if found is None:
        raise ReservationError("reservation not found")
    if found.get("owner") != owner:
        raise ReservationError("only the reservation owner may mark sent")
    if found.get("state") != "RESERVED":
        raise ReservationError("only RESERVED may transition to SENT_DNR")
    if _parse_time(sent_at, "sent_at") < _parse_time(found["claimed_at"], "claimed_at"):
        raise ReservationError("sent_at cannot precede claimed_at")
    found["state"] = TERMINAL_DNR_STATE
    found["sent_at"] = sent_at
    found["released_at"] = None
    if source_ref:
        found["source_ref"] = _text(source_ref)
    validate_ledger(result)
    return result


def release_reservation(ledger, *, reservation_id, owner, released_at=None, reason=None):
    validate_ledger(ledger)
    result = copy.deepcopy(ledger)
    owner = _text(owner)
    released_at = released_at or utc_now()
    _parse_time(released_at, "released_at")
    found = None
    for claim in result["claims"]:
        if claim.get("reservation_id") == reservation_id:
            found = claim
            break
    if found is None:
        raise ReservationError("reservation not found")
    if found.get("owner") != owner:
        raise ReservationError("only the reservation owner may release")
    if found.get("state") != "RESERVED":
        raise ReservationError("only an unsent RESERVED claim may be released")
    if _parse_time(released_at, "released_at") < _parse_time(found["claimed_at"], "claimed_at"):
        raise ReservationError("released_at cannot precede claimed_at")
    found["state"] = RELEASED_STATE
    found["released_at"] = released_at
    found["sent_at"] = None
    if reason:
        found["release_reason"] = _text(reason)
    validate_ledger(result)
    return result


def dumps(ledger):
    validate_ledger(ledger)
    return json.dumps(ledger, indent=2, sort_keys=True) + "\n"


def _write_result(ledger, output):
    text = dumps(ledger)
    if output:
        Path(output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def _add_identity_args(parser):
    parser.add_argument("--org", required=True, help="canonical organization key from the lead record")
    parser.add_argument("--recipient", default=None, help="exact recipient email; hashed in ledger")
    parser.add_argument("--lead-ref", default=None, help="stable lead/provider record id; hashed in ledger")
    parser.add_argument("--org-alias", action="append", default=[], help="additional organization spelling")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Prepare/verify collision-safe outreach ledger mutations; GitHub main CAS is authority."
    )
    parser.add_argument(
        "--ledger",
        default="revenue/payment_ready/outreach_reservations.json",
        help="canonical ledger copy that was read from GitHub main",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="check an identity against active/DNR claims")
    _add_identity_args(check)

    reserve = sub.add_parser(
        "prepare-reservation",
        help="prepare replacement JSON; does NOT reserve until GitHub main CAS update succeeds",
    )
    _add_identity_args(reserve)
    reserve.add_argument("--owner", required=True)
    reserve.add_argument("--claimed-at", default=None)
    reserve.add_argument("--output", default=None)

    verify = sub.add_parser("verify-send-authority", help="re-read main and verify authority before send")
    _add_identity_args(verify)
    verify.add_argument("--owner", required=True)
    verify.add_argument("--reservation-id", required=True)

    sent = sub.add_parser("prepare-sent", help="prepare RESERVED -> SENT_DNR replacement")
    sent.add_argument("--owner", required=True)
    sent.add_argument("--reservation-id", required=True)
    sent.add_argument("--sent-at", default=None)
    sent.add_argument("--source-ref", default=None)
    sent.add_argument("--output", default=None)

    release = sub.add_parser("prepare-release", help="prepare unsent RESERVED -> RELEASED replacement")
    release.add_argument("--owner", required=True)
    release.add_argument("--reservation-id", required=True)
    release.add_argument("--released-at", default=None)
    release.add_argument("--reason", default=None)
    release.add_argument("--output", default=None)

    sub.add_parser("lint", help="validate the ledger and prove no active fingerprint collisions")

    args = parser.parse_args(argv)
    ledger = load_ledger(args.ledger)

    if args.command == "lint":
        print(f"OK {len(ledger['claims'])} claims; no active fingerprint collisions")
        return 0
    if args.command == "check":
        fingerprints = identity_fingerprints(
            args.org, args.recipient, args.lead_ref, args.org_alias
        )
        conflicts = conflicts_for(ledger, fingerprints)
        if conflicts:
            print("STOP_CONFLICT " + ",".join(c["reservation_id"] for c in conflicts))
            return 3
        print("AVAILABLE (not reserved; GitHub main CAS still required)")
        return 0
    if args.command == "prepare-reservation":
        try:
            replacement, reservation_id = prepare_reservation(
                ledger,
                org_key=args.org,
                owner=args.owner,
                recipient=args.recipient,
                lead_ref=args.lead_ref,
                org_aliases=args.org_alias,
                claimed_at=args.claimed_at,
            )
        except ReservationConflict as exc:
            print("STOP_CONFLICT " + ",".join(c["reservation_id"] for c in exc.conflicts), file=sys.stderr)
            return 3
        _write_result(replacement, args.output)
        print(
            f"PREPARED {reservation_id}; NOT AUTHORITY UNTIL CANONICAL MAIN CAS SUCCEEDS",
            file=sys.stderr,
        )
        return 0
    if args.command == "verify-send-authority":
        try:
            claim = assert_send_authority(
                ledger,
                reservation_id=args.reservation_id,
                owner=args.owner,
                org_key=args.org,
                recipient=args.recipient,
                lead_ref=args.lead_ref,
                org_aliases=args.org_alias,
            )
        except ReservationError as exc:
            print(f"STOP {exc}", file=sys.stderr)
            return 4
        print(f"AUTHORIZED {claim['reservation_id']} (canonical-main reservation verified)")
        return 0
    if args.command == "prepare-sent":
        replacement = mark_sent(
            ledger,
            reservation_id=args.reservation_id,
            owner=args.owner,
            sent_at=args.sent_at,
            source_ref=args.source_ref,
        )
        _write_result(replacement, args.output)
        return 0
    if args.command == "prepare-release":
        replacement = release_reservation(
            ledger,
            reservation_id=args.reservation_id,
            owner=args.owner,
            released_at=args.released_at,
            reason=args.reason,
        )
        _write_result(replacement, args.output)
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
