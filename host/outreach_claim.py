#!/usr/bin/env python3
"""Privacy-preserving, CAS-friendly outreach lease records.

This module does not send mail and does not talk to GitHub. It turns a private
route into an opaque deterministic path and validates lease state transitions.

The cross-harness atomicity primitive is GitHub Contents API compare-and-swap:
- first claim: create the computed path on current main; only one create wins;
- transition/reclaim: fetch current blob SHA, generate replacement JSON here,
  then update that exact path with the fetched SHA; a stale writer loses.

Raw addresses/routes and free-form purpose/evidence strings are hashed and are
never persisted by this module.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA = "commons-outreach-lease/v1"
NAMESPACE = b"commons-outreach-route-v1\0"
PURPOSE_NAMESPACE = b"commons-outreach-purpose-v1\0"
EVIDENCE_NAMESPACE = b"commons-outreach-evidence-v1\0"
ROOT_REL = "revenue/outreach_claims"
ACTIVE = "ACTIVE"
CONSUMED = "CONSUMED"
RELEASED = "RELEASED"
STATUSES = {ACTIVE, CONSUMED, RELEASED}
CLAIMANT_RE = re.compile(r"^[A-Za-z0-9._:/-]{2,96}$")
TTL_MIN = 1
TTL_MAX = 240
DEFAULT_TTL_MINUTES = 30


class LeaseError(ValueError):
    pass


def iso_z(value: dt.datetime) -> str:
    if value.tzinfo is None:
        raise LeaseError("timestamp must include a timezone")
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: str) -> dt.datetime:
    if not isinstance(value, str) or not value:
        raise LeaseError("timestamp must be a non-empty string")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError as exc:
        raise LeaseError(f"invalid timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise LeaseError("timestamp must include a timezone")
    return parsed.astimezone(dt.timezone.utc)


def normalize_route(route: str) -> str:
    """Normalize only enough to make identical routes collide."""
    if not isinstance(route, str) or not route.strip():
        raise LeaseError("route is required")
    value = route.strip()
    lower = value.casefold()
    if lower.startswith("mailto:"):
        value = value[7:].strip()
        if not value:
            raise LeaseError("mailto route is empty")
        return value.casefold()
    if lower.startswith("http://") or lower.startswith("https://"):
        from urllib.parse import urlsplit, urlunsplit
        parts = urlsplit(value)
        if not parts.hostname:
            raise LeaseError("URL route has no host")
        host = parts.hostname.casefold()
        if parts.port:
            host = f"{host}:{parts.port}"
        path = parts.path or "/"
        if path != "/":
            path = path.rstrip("/") or "/"
        return urlunsplit((parts.scheme.casefold(), host, path, parts.query, ""))
    return value.casefold()


def _digest(namespace: bytes, value: str) -> str:
    return hashlib.sha256(namespace + value.encode("utf-8")).hexdigest()


def route_digest(route: str) -> str:
    return _digest(NAMESPACE, normalize_route(route))


def claim_path(route: str) -> str:
    return f"{ROOT_REL}/{route_digest(route)}.json"


def opaque_digest(namespace: bytes, value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    return _digest(namespace, text)


def validate_claimant(value: str) -> str:
    claimant = (value or "").strip()
    if not CLAIMANT_RE.fullmatch(claimant):
        raise LeaseError("claimant must be 2-96 chars from A-Za-z0-9._:/-")
    return claimant


def validate_ttl(ttl_minutes: int) -> int:
    try:
        ttl = int(ttl_minutes)
    except (TypeError, ValueError) as exc:
        raise LeaseError("ttl must be an integer number of minutes") from exc
    if not TTL_MIN <= ttl <= TTL_MAX:
        raise LeaseError(f"ttl must be between {TTL_MIN} and {TTL_MAX} minutes")
    return ttl


def _now(value: str | None = None) -> dt.datetime:
    return parse_time(value) if value else dt.datetime.now(dt.timezone.utc)


def new_record(route: str, claimant: str, *, purpose: str | None = None,
               ttl_minutes: int = DEFAULT_TTL_MINUTES,
               now: dt.datetime | None = None) -> dict[str, Any]:
    actor = validate_claimant(claimant)
    ttl = validate_ttl(ttl_minutes)
    instant = now or dt.datetime.now(dt.timezone.utc)
    if instant.tzinfo is None:
        raise LeaseError("now must include a timezone")
    instant = instant.astimezone(dt.timezone.utc)
    digest = route_digest(route)
    record = {
        "schema": SCHEMA,
        "target_digest": digest,
        "generation": 1,
        "status": ACTIVE,
        "claimant": actor,
        "claimed_at": iso_z(instant),
        "expires_at": iso_z(instant + dt.timedelta(minutes=ttl)),
        "updated_at": iso_z(instant),
        "purpose_digest": opaque_digest(PURPOSE_NAMESPACE, purpose),
        "evidence_digest": None,
    }
    validate_record(record)
    return record


def validate_record(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise LeaseError("lease must be a JSON object")
    required = {"schema", "target_digest", "generation", "status", "claimant",
                "claimed_at", "expires_at", "updated_at", "purpose_digest", "evidence_digest"}
    if set(record) != required:
        missing = sorted(required - set(record))
        extra = sorted(set(record) - required)
        raise LeaseError(f"lease keys drifted; missing={missing} extra={extra}")
    if record["schema"] != SCHEMA:
        raise LeaseError(f"unsupported schema: {record['schema']}")
    digest = record["target_digest"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise LeaseError("target_digest must be lowercase sha256")
    if not isinstance(record["generation"], int) or record["generation"] < 1:
        raise LeaseError("generation must be a positive integer")
    if record["status"] not in STATUSES:
        raise LeaseError(f"invalid status: {record['status']}")
    validate_claimant(record["claimant"])
    claimed = parse_time(record["claimed_at"])
    expires = parse_time(record["expires_at"])
    updated = parse_time(record["updated_at"])
    if expires <= claimed:
        raise LeaseError("expires_at must be after claimed_at")
    if updated < claimed:
        raise LeaseError("updated_at cannot predate claimed_at")
    for field in ("purpose_digest", "evidence_digest"):
        value = record[field]
        if value is not None and (not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)):
            raise LeaseError(f"{field} must be null or lowercase sha256")
    return record


def effective_state(record: dict[str, Any], *, at: dt.datetime | None = None) -> str:
    validate_record(record)
    if record["status"] != ACTIVE:
        return str(record["status"])
    instant = (at or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    return "EXPIRED" if instant >= parse_time(record["expires_at"]) else ACTIVE


def _copy(record: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(record))


def consume(record: dict[str, Any], claimant: str, *, now: dt.datetime | None = None) -> dict[str, Any]:
    actor = validate_claimant(claimant)
    validate_record(record)
    instant = now or dt.datetime.now(dt.timezone.utc)
    state = effective_state(record, at=instant)
    if state != ACTIVE:
        raise LeaseError(f"consume requires ACTIVE lease; state={state}")
    if record["claimant"] != actor:
        raise LeaseError(f"lease is owned by {record['claimant']}; not {actor}")
    out = _copy(record)
    out["status"] = CONSUMED
    out["updated_at"] = iso_z(instant)
    validate_record(out)
    return out


def release(record: dict[str, Any], claimant: str, *, now: dt.datetime | None = None) -> dict[str, Any]:
    actor = validate_claimant(claimant)
    validate_record(record)
    instant = now or dt.datetime.now(dt.timezone.utc)
    state = effective_state(record, at=instant)
    if state != ACTIVE:
        raise LeaseError(f"release requires ACTIVE lease; state={state}")
    if record["claimant"] != actor:
        raise LeaseError(f"lease is owned by {record['claimant']}; not {actor}")
    out = _copy(record)
    out["status"] = RELEASED
    out["updated_at"] = iso_z(instant)
    validate_record(out)
    return out


def reclaim(record: dict[str, Any], claimant: str, *, purpose: str | None = None,
            ttl_minutes: int = DEFAULT_TTL_MINUTES,
            now: dt.datetime | None = None) -> dict[str, Any]:
    actor = validate_claimant(claimant)
    ttl = validate_ttl(ttl_minutes)
    validate_record(record)
    instant = now or dt.datetime.now(dt.timezone.utc)
    state = effective_state(record, at=instant)
    if state not in {"EXPIRED", RELEASED}:
        raise LeaseError(f"reclaim requires EXPIRED or RELEASED lease; state={state}")
    out = _copy(record)
    out["generation"] += 1
    out["status"] = ACTIVE
    out["claimant"] = actor
    out["claimed_at"] = iso_z(instant)
    out["expires_at"] = iso_z(instant + dt.timedelta(minutes=ttl))
    out["updated_at"] = iso_z(instant)
    out["purpose_digest"] = opaque_digest(PURPOSE_NAMESPACE, purpose)
    out["evidence_digest"] = None
    validate_record(out)
    return out


def reopen(record: dict[str, Any], claimant: str, *, evidence: str,
           purpose: str | None = None, ttl_minutes: int = DEFAULT_TTL_MINUTES,
           now: dt.datetime | None = None) -> dict[str, Any]:
    actor = validate_claimant(claimant)
    ttl = validate_ttl(ttl_minutes)
    validate_record(record)
    if record["status"] != CONSUMED:
        raise LeaseError(f"reopen requires CONSUMED lease; state={record['status']}")
    evidence_digest = opaque_digest(EVIDENCE_NAMESPACE, evidence)
    if evidence_digest is None:
        raise LeaseError("reopen requires non-empty evidence")
    instant = now or dt.datetime.now(dt.timezone.utc)
    out = _copy(record)
    out["generation"] += 1
    out["status"] = ACTIVE
    out["claimant"] = actor
    out["claimed_at"] = iso_z(instant)
    out["expires_at"] = iso_z(instant + dt.timedelta(minutes=ttl))
    out["updated_at"] = iso_z(instant)
    out["purpose_digest"] = opaque_digest(PURPOSE_NAMESPACE, purpose)
    out["evidence_digest"] = evidence_digest
    validate_record(out)
    return out


def public_view(record: dict[str, Any], *, at: dt.datetime | None = None) -> dict[str, Any]:
    validate_record(record)
    out = dict(record)
    out["effective_state"] = effective_state(record, at=at)
    out["path"] = f"{ROOT_REL}/{record['target_digest']}.json"
    return out


def dump(record: dict[str, Any]) -> str:
    validate_record(record)
    return json.dumps(record, sort_keys=True, indent=2) + "\n"


def load(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LeaseError(f"cannot read lease {path}: {exc}") from exc
    return validate_record(value)


def _write(path: str | Path, record: dict[str, Any]) -> None:
    Path(path).write_text(dump(record), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Opaque outreach lease record helper")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("key", help="print deterministic opaque key/path for a private route")
    p.add_argument("route")
    p = sub.add_parser("new", help="render a new ACTIVE lease record")
    p.add_argument("route")
    p.add_argument("--claimant", required=True)
    p.add_argument("--purpose")
    p.add_argument("--ttl", type=int, default=DEFAULT_TTL_MINUTES)
    p.add_argument("--at")
    for name in ("inspect", "consume", "release", "reclaim", "reopen"):
        p = sub.add_parser(name)
        p.add_argument("file")
        if name != "inspect":
            p.add_argument("--claimant", required=True)
        p.add_argument("--at")
        if name in {"reclaim", "reopen"}:
            p.add_argument("--purpose")
            p.add_argument("--ttl", type=int, default=DEFAULT_TTL_MINUTES)
        if name == "reopen":
            p.add_argument("--evidence", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "key":
            print(json.dumps({"target_digest": route_digest(args.route), "path": claim_path(args.route)}, sort_keys=True))
            return 0
        if args.command == "new":
            record = new_record(args.route, args.claimant, purpose=args.purpose,
                                ttl_minutes=args.ttl, now=_now(args.at))
            sys.stdout.write(dump(record))
            return 0
        record = load(args.file)
        instant = _now(args.at)
        if args.command == "inspect":
            print(json.dumps(public_view(record, at=instant), sort_keys=True, indent=2))
            return 0
        if args.command == "consume":
            result = consume(record, args.claimant, now=instant)
        elif args.command == "release":
            result = release(record, args.claimant, now=instant)
        elif args.command == "reclaim":
            result = reclaim(record, args.claimant, purpose=args.purpose, ttl_minutes=args.ttl, now=instant)
        elif args.command == "reopen":
            result = reopen(record, args.claimant, evidence=args.evidence, purpose=args.purpose,
                            ttl_minutes=args.ttl, now=instant)
        else:
            raise LeaseError(f"unsupported command: {args.command}")
        _write(args.file, result)
        sys.stdout.write(dump(result))
        return 0
    except LeaseError as exc:
        print(f"outreach-lease: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
