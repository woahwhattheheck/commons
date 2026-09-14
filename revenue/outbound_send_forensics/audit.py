#!/usr/bin/env python3
"""Offline, fail-closed audit of outbound sends against connector-native lease evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from revenue.outbound_connector_lease.key import (
    BRANCH_PREFIX,
    LeaseKeyError,
    SUPPORTED_REPLY_PROVIDERS,
    compile_document as compile_lease_document,
)

LEGACY_INPUT_SCHEMA = "outbound-send-forensics/v1"
INPUT_SCHEMA = "outbound-send-forensics/v2"
RECEIPT_SCHEMA = "outbound-send-forensics-receipt/v2"
BATCH_SCHEMA = "outbound-send-forensics-batch/v2"
CANONICAL_LEASE_REPOSITORY = "woahwhattheheck/commons"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9._:/+\-]{0,190}$")
_BRANCH_RE = re.compile(r"^outbound-connector-lease/v1/[0-9a-f]{64}$")
_RFC3339_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$")
_REPOSITORY_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,99}/[a-z0-9][a-z0-9._-]{0,99}$")

CLASS_PROTECTED = "PROTECTED_PRE_SEND"
CLASS_POST_SEND = "POST_SEND_LEASE_VIOLATION"
CLASS_MISSING = "MISSING_LEASE"
CLASS_MISMATCH = "SEAM_MISMATCH"
CLASS_UNTRUSTED = "AMBIGUOUS_UNTRUSTED_EVIDENCE"
DUPLICATE_FLAG = "DUPLICATE_SEND_SAME_SEAM"
CLASSIFICATIONS = (
    CLASS_PROTECTED,
    CLASS_POST_SEND,
    CLASS_MISSING,
    CLASS_MISMATCH,
    CLASS_UNTRUSTED,
)


class ForensicsError(ValueError):
    pass


def _strict_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ForensicsError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def strict_loads(raw):
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_strict_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ForensicsError(f"non-finite JSON number: {token}")
            ),
        )
    except json.JSONDecodeError as exc:
        raise ForensicsError("invalid JSON") from exc
    if type(value) is not dict:
        raise ForensicsError("input must be a JSON object")
    return value


def _exact(value, fields, name):
    if type(value) is not dict:
        raise ForensicsError(f"{name} must be an object")
    actual = set(value)
    if actual != fields:
        missing = sorted(fields - actual)
        extra = sorted(actual - fields)
        bits = []
        if missing:
            bits.append("missing=" + ",".join(missing))
        if extra:
            bits.append("extra=" + ",".join(extra))
        raise ForensicsError(f"{name} requires exact fields ({'; '.join(bits)})")
    return value


def _token(value, field):
    if type(value) is not str:
        raise ForensicsError(f"{field} must be a string")
    token = value.strip().casefold()
    if not token or len(token) > 191 or _TOKEN_RE.fullmatch(token) is None:
        raise ForensicsError(f"{field} must use 1..191 lowercase-token chars [a-z0-9._:/+-]")
    return token


def _enum(value, allowed, field):
    if type(value) is not str:
        raise ForensicsError(f"{field} must be a string")
    normalized = value.strip().casefold()
    if normalized not in allowed:
        raise ForensicsError(f"{field} must be one of: {','.join(sorted(allowed))}")
    return normalized


def _sha256(value, field):
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise ForensicsError(f"{field} must be exactly 64 lowercase hex characters")
    return value


def _sha1(value, field):
    if type(value) is not str or _SHA1_RE.fullmatch(value) is None:
        raise ForensicsError(f"{field} must be exactly 40 lowercase hex characters")
    return value


def _branch(value, field):
    if type(value) is not str or _BRANCH_RE.fullmatch(value) is None:
        raise ForensicsError(f"{field} must be {BRANCH_PREFIX}<64-lowercase-hex>")
    return value


def _repository(value, field):
    if type(value) is not str:
        raise ForensicsError(f"{field} must be a string")
    normalized = value.strip().casefold()
    if _REPOSITORY_RE.fullmatch(normalized) is None:
        raise ForensicsError(f"{field} must be owner/repository using GitHub-name characters")
    return normalized


def _timestamp(value, field):
    if type(value) is not str or not value.strip():
        raise ForensicsError(f"{field} must be a non-empty RFC3339 timestamp")
    raw = value.strip()
    if _RFC3339_RE.fullmatch(raw) is None:
        raise ForensicsError(f"{field} must be strict RFC3339 with T, seconds, and timezone")
    candidate = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ForensicsError(f"{field} must be a valid RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ForensicsError(f"{field} must include an explicit timezone offset")
    utc = parsed.astimezone(timezone.utc)
    canonical = utc.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return utc, canonical


def _digest(value):
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    ).hexdigest()


def _normalize_send(raw):
    send = _exact(
        raw,
        {"provider", "event_id", "sent_at", "authority", "status", "receipt_sha256"},
        "record.send",
    )
    provider = _enum(send["provider"], set(SUPPORTED_REPLY_PROVIDERS), "record.send.provider")
    event_id = _token(send["event_id"], "record.send.event_id")
    sent_dt, sent_at = _timestamp(send["sent_at"], "record.send.sent_at")
    authority = _enum(
        send["authority"], {"provider-receipt", "caller-assertion"}, "record.send.authority"
    )
    status = _enum(send["status"], {"sent", "ambiguous"}, "record.send.status")
    receipt_sha256 = _sha256(send["receipt_sha256"], "record.send.receipt_sha256")
    return {
        "provider": provider,
        "event_id": event_id,
        "sent_dt": sent_dt,
        "sent_at": sent_at,
        "authority": authority,
        "status": status,
        "receipt_sha256": receipt_sha256,
    }


def _normalize_lease(raw, input_schema):
    if raw is None:
        return None
    common_fields = {
        "branch",
        "created_at",
        "authority",
        "result",
        "base_sha",
        "receipt_sha256",
    }
    if input_schema == LEGACY_INPUT_SCHEMA:
        lease = _exact(raw, common_fields, "record.lease_create")
        repository_full_name = None
    else:
        lease = _exact(
            raw,
            common_fields | {"repository_full_name"},
            "record.lease_create",
        )
        repository_full_name = _repository(
            lease["repository_full_name"], "record.lease_create.repository_full_name"
        )
    branch = _branch(lease["branch"], "record.lease_create.branch")
    created_dt, created_at = _timestamp(lease["created_at"], "record.lease_create.created_at")
    authority = _enum(
        lease["authority"],
        {"github-create-result", "caller-assertion"},
        "record.lease_create.authority",
    )
    result = _enum(
        lease["result"],
        {"created", "exists", "ambiguous", "failed"},
        "record.lease_create.result",
    )
    base_sha = _sha1(lease["base_sha"], "record.lease_create.base_sha")
    receipt_sha256 = _sha256(lease["receipt_sha256"], "record.lease_create.receipt_sha256")
    return {
        "repository_full_name": repository_full_name,
        "branch": branch,
        "created_dt": created_dt,
        "created_at": created_at,
        "authority": authority,
        "result": result,
        "base_sha": base_sha,
        "receipt_sha256": receipt_sha256,
    }

def _normalize_record(raw, input_schema):
    record = _exact(raw, {"record_id", "seam", "send", "lease_create"}, "record")
    record_id = _token(record["record_id"], "record.record_id")
    try:
        compiled = compile_lease_document(record["seam"])
    except LeaseKeyError as exc:
        raise ForensicsError(f"record.seam invalid: {exc}") from exc
    return {
        "record_id": record_id,
        "compiled": compiled,
        "send": _normalize_send(record["send"]),
        "lease": _normalize_lease(record["lease_create"], input_schema),
        "input_schema": input_schema,
    }


def _classify(record):
    send = record["send"]
    lease = record["lease"]
    expected_branch = record["compiled"]["branch"]
    if send["authority"] != "provider-receipt" or send["status"] != "sent":
        return CLASS_UNTRUSTED, ["provider send is not backed by an authoritative SENT receipt"]
    if lease is None:
        return CLASS_MISSING, ["provider SENT exists but no lease-create evidence was supplied"]
    if lease["authority"] != "github-create-result" or lease["result"] != "created":
        return CLASS_UNTRUSTED, [
            "lease evidence does not prove an exact successful GitHub create-branch result"
        ]
    if lease["repository_full_name"] is None:
        return CLASS_UNTRUSTED, [
            "legacy v1 lease evidence lacks repository identity and cannot prove the canonical mutex"
        ]
    if lease["repository_full_name"] != CANONICAL_LEASE_REPOSITORY:
        return CLASS_UNTRUSTED, [
            f"lease create evidence is not from canonical repository {CANONICAL_LEASE_REPOSITORY}"
        ]
    if lease["branch"] != expected_branch:
        return CLASS_MISMATCH, ["successful lease evidence is for a different canonical seam branch"]
    if lease["created_dt"] >= send["sent_dt"]:
        return CLASS_POST_SEND, ["lease create was not strictly earlier than the provider SENT event"]
    return CLASS_PROTECTED, [
        "authoritative matching lease create in the canonical repository is strictly earlier than provider SENT"
    ]


def _payload(record):
    classification, reasons = _classify(record)
    send = record["send"]
    lease = record["lease"]
    return {
        "schema": RECEIPT_SCHEMA,
        "record_id": record["record_id"],
        "source_input_schema": record["input_schema"],
        "classification": classification,
        "reasons": reasons,
        "dnr": True,
        "expected_lease_repository": CANONICAL_LEASE_REPOSITORY,
        "expected_branch": record["compiled"]["branch"],
        "seam_sha256": record["compiled"]["seam_sha256"],
        "send_provider": send["provider"],
        "send_event_id": send["event_id"],
        "send_at_utc": send["sent_at"],
        "send_receipt_sha256": send["receipt_sha256"],
        "lease_repository_full_name": None if lease is None else lease["repository_full_name"],
        "lease_branch": None if lease is None else lease["branch"],
        "lease_created_at_utc": None if lease is None else lease["created_at"],
        "lease_receipt_sha256": None if lease is None else lease["receipt_sha256"],
        "batch_flags": [],
        "same_seam_send_count": 1,
    }


def _seal(payload):
    bare = dict(payload)
    bare.pop("receipt_sha256", None)
    return {**bare, "receipt_sha256": _digest(bare)}


def audit_document(document):
    top = _exact(document, {"schema", "records"}, "input")
    if top["schema"] not in {LEGACY_INPUT_SCHEMA, INPUT_SCHEMA}:
        raise ForensicsError(
            f"input.schema must be one of: {LEGACY_INPUT_SCHEMA},{INPUT_SCHEMA}"
        )
    input_schema = top["schema"]
    if type(top["records"]) is not list or not top["records"]:
        raise ForensicsError("input.records must be a non-empty array")
    records = [_normalize_record(item, input_schema) for item in top["records"]]
    ids = [record["record_id"] for record in records]
    duplicate_ids = sorted(key for key, count in Counter(ids).items() if count > 1)
    if duplicate_ids:
        raise ForensicsError("duplicate record_id: " + ",".join(duplicate_ids))

    seen = {}
    for record in records:
        key = (record["send"]["provider"], record["send"]["event_id"])
        if key in seen:
            previous = seen[key]
            if (
                previous["send"]["sent_at"] != record["send"]["sent_at"]
                or previous["send"]["receipt_sha256"] != record["send"]["receipt_sha256"]
                or previous["compiled"]["branch"] != record["compiled"]["branch"]
            ):
                raise ForensicsError("contradictory duplicate provider event: " + ":".join(key))
            raise ForensicsError("duplicate provider event: " + ":".join(key))
        seen[key] = record

    receipts = [_payload(record) for record in records]
    by_branch = defaultdict(list)
    for receipt in receipts:
        by_branch[receipt["expected_branch"]].append(receipt)
    incidents = []
    for branch, group in sorted(by_branch.items()):
        if len(group) <= 1:
            continue
        for receipt in group:
            receipt["batch_flags"] = [DUPLICATE_FLAG]
            receipt["same_seam_send_count"] = len(group)
        incidents.append(
            {
                "expected_branch": branch,
                "send_count": len(group),
                "record_ids": sorted(item["record_id"] for item in group),
                "provider_events": sorted(
                    f"{item['send_provider']}:{item['send_event_id']}" for item in group
                ),
            }
        )

    sealed = sorted((_seal(receipt) for receipt in receipts), key=lambda item: item["record_id"])
    counts = Counter(item["classification"] for item in sealed)
    summary = {
        "records": len(sealed),
        "dnr_records": sum(1 for item in sealed if item["dnr"]),
        "duplicate_seams": len(incidents),
        "duplicate_send_records": sum(
            1 for item in sealed if DUPLICATE_FLAG in item["batch_flags"]
        ),
        **{name: counts.get(name, 0) for name in CLASSIFICATIONS},
    }
    payload = {
        "schema": BATCH_SCHEMA,
        "summary": summary,
        "incident_seams": incidents,
        "receipts": sealed,
    }
    return {**payload, "batch_sha256": _digest(payload)}


def audit_json(raw):
    return audit_document(strict_loads(raw))


def main(argv: Sequence[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Audit provider sends against canonical pre-send lease evidence"
    )
    parser.add_argument("input", nargs="?", default="-", help="input JSON path, or '-' for stdin")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        result = audit_json(raw)
    except (ForensicsError, OSError) as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            result,
            sort_keys=True,
            indent=2 if args.pretty else None,
            separators=None if args.pretty else (",", ":"),
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
