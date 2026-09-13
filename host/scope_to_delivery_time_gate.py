#!/usr/bin/env python3
"""Trusted-time prerequisite for Commons accepted-scope-to-delivery authority.

The legacy scope_to_delivery composer is a deterministic historical projection. This
module adds the time/chronology authority it intentionally lacks. It never grants
external action, payment, delivery, acceptance, or revenue authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_AGREEMENT = "commons-scope-agreement/v1"
SCHEMA_OBSERVATIONS = "commons-scope-observations/v1"
SCHEMA_RECEIPT = "commons-scope-time-authority/v1"
MAX_INPUT_BYTES = 2_000_000
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class TemporalAuthorityError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value or not (
        value.endswith("Z") or re.search(r"[+-]\d\d:\d\d$", value)
    ):
        raise TemporalAuthorityError(f"{field} must be an offset-aware ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise TemporalAuthorityError(f"{field} must be a real timestamp") from exc
    if parsed.utcoffset() is None:
        raise TemporalAuthorityError(f"{field} must include an offset")
    return parsed.astimezone(timezone.utc)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise TemporalAuthorityError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def strict_loads(raw: bytes, field: str) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TemporalAuthorityError(f"{field} must be UTF-8 JSON") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                TemporalAuthorityError(f"{field} contains non-finite JSON number {value}")
            ),
        )
    except TemporalAuthorityError:
        raise
    except json.JSONDecodeError as exc:
        raise TemporalAuthorityError(f"{field} is not valid JSON") from exc


def read_plain_json(path: str | Path, field: str) -> tuple[Any, str]:
    target = os.fspath(path)
    flags = os.O_RDONLY
    if not hasattr(os, "O_NOFOLLOW"):
        raise TemporalAuthorityError("platform lacks O_NOFOLLOW; plain-file custody cannot be proven")
    flags |= os.O_NOFOLLOW
    try:
        fd = os.open(target, flags)
    except OSError as exc:
        raise TemporalAuthorityError(f"{field} must be a readable non-symlink file") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise TemporalAuthorityError(f"{field} must be a regular file")
        if info.st_size > MAX_INPUT_BYTES:
            raise TemporalAuthorityError(f"{field} exceeds {MAX_INPUT_BYTES} bytes")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, min(65536, MAX_INPUT_BYTES + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_INPUT_BYTES:
                raise TemporalAuthorityError(f"{field} exceeds {MAX_INPUT_BYTES} bytes")
            chunks.append(chunk)
        raw = b"".join(chunks)
    finally:
        os.close(fd)
    return strict_loads(raw, field), hashlib.sha256(raw).hexdigest()


def _require_dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TemporalAuthorityError(f"{field} must be an object")
    return value


def _agreement_times(agreement: Any) -> tuple[dict[str, Any], datetime, datetime, datetime | None]:
    agreement = _require_dict(agreement, "agreement")
    agreement_id = agreement.get("agreement_id")
    if not isinstance(agreement_id, str) or not agreement_id.strip():
        raise TemporalAuthorityError("agreement.agreement_id must be a nonempty string")
    if agreement_id != agreement_id.strip():
        raise TemporalAuthorityError("agreement.agreement_id must not have surrounding whitespace")
    if agreement.get("schema_version") != SCHEMA_AGREEMENT:
        raise TemporalAuthorityError(f"agreement.schema_version must be {SCHEMA_AGREEMENT}")
    if agreement.get("kind") != "SCOPE_AGREEMENT":
        raise TemporalAuthorityError("agreement.kind must be SCOPE_AGREEMENT")
    window = _require_dict(agreement.get("window"), "agreement.window")
    start = parse_time(window.get("start"), "agreement.window.start")
    end = parse_time(window.get("end"), "agreement.window.end")
    if end <= start:
        raise TemporalAuthorityError("agreement.window.end must be after start")
    written = _require_dict(agreement.get("written_acceptance"), "agreement.written_acceptance")
    status = written.get("status")
    accepted_at = None
    if status == "PRESENT":
        accepted_at = parse_time(written.get("accepted_at"), "agreement.written_acceptance.accepted_at")
        if accepted_at > end:
            raise TemporalAuthorityError("PRESENT acceptance occurs after the contracted window ended")
    elif written.get("accepted_at") is not None:
        raise TemporalAuthorityError("non-PRESENT acceptance must not carry accepted_at")
    return agreement, start, end, accepted_at


def _validate_observations(
    observations: Any | None,
    agreement: dict[str, Any],
    *,
    accepted_at: datetime | None,
    start: datetime,
    end: datetime,
    as_of: datetime,
) -> tuple[list[dict[str, Any]], str | None]:
    if observations is None:
        return [], None
    observations = _require_dict(observations, "observations")
    if observations.get("schema_version") != SCHEMA_OBSERVATIONS:
        raise TemporalAuthorityError(f"observations.schema_version must be {SCHEMA_OBSERVATIONS}")
    if observations.get("kind") != "EXECUTION_OBSERVATIONS":
        raise TemporalAuthorityError("observations.kind must be EXECUTION_OBSERVATIONS")
    if observations.get("agreement_id") != agreement.get("agreement_id"):
        raise TemporalAuthorityError("observations.agreement_id does not match agreement")
    items = observations.get("observations")
    if not isinstance(items, list):
        raise TemporalAuthorityError("observations.observations must be a list")
    if items and accepted_at is None:
        raise TemporalAuthorityError("execution observations exist without PRESENT acceptance")
    seen: set[str] = set()
    parsed: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        item = _require_dict(item, f"observations[{index}]")
        observation_id = item.get("observation_id")
        if not isinstance(observation_id, str) or not observation_id:
            raise TemporalAuthorityError(f"observations[{index}].observation_id must be a nonempty string")
        if observation_id in seen:
            raise TemporalAuthorityError(f"duplicate observation_id: {observation_id}")
        seen.add(observation_id)
        when = parse_time(item.get("observed_at"), f"observations[{index}].observed_at")
        assert accepted_at is not None
        if when < accepted_at:
            raise TemporalAuthorityError(f"observation {observation_id} predates written acceptance")
        if when < start:
            raise TemporalAuthorityError(f"observation {observation_id} predates contracted work window")
        if when > end:
            raise TemporalAuthorityError(f"observation {observation_id} occurs after contracted work window")
        if when > as_of:
            raise TemporalAuthorityError(f"observation {observation_id} is in the trusted verifier's future")
        parsed.append({"observation_id": observation_id, "observed_at": when})
    return parsed, digest(observations)


def evaluate(
    agreement: Any,
    observations: Any | None,
    *,
    as_of: datetime,
    agreement_raw_sha256: str | None = None,
    observations_raw_sha256: str | None = None,
) -> dict[str, Any]:
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise TemporalAuthorityError("as_of must be timezone-aware")
    as_of = as_of.astimezone(timezone.utc)
    agreement, start, end, accepted_at = _agreement_times(agreement)
    written = agreement["written_acceptance"]
    if accepted_at is not None and accepted_at > as_of:
        raise TemporalAuthorityError("PRESENT acceptance is in the trusted verifier's future")
    parsed_observations, observations_digest = _validate_observations(
        observations,
        agreement,
        accepted_at=accepted_at,
        start=start,
        end=end,
        as_of=as_of,
    )

    status = written.get("status")
    if status != "PRESENT":
        state = "HOLD_NO_PRESENT_ACCEPTANCE"
        current_work_authorized = False
    elif as_of < start:
        state = "HOLD_WINDOW_NOT_STARTED"
        current_work_authorized = False
    elif as_of > end:
        state = "HOLD_WINDOW_EXPIRED"
        current_work_authorized = False
    else:
        state = "TEMPORAL_PREREQUISITE_READY"
        current_work_authorized = True

    agreement_digest = digest(agreement)
    if agreement_raw_sha256 is not None and not SHA256_RE.fullmatch(agreement_raw_sha256):
        raise TemporalAuthorityError("agreement_raw_sha256 must be lowercase sha256")
    if observations_raw_sha256 is not None and not SHA256_RE.fullmatch(observations_raw_sha256):
        raise TemporalAuthorityError("observations_raw_sha256 must be lowercase sha256")

    receipt_core = {
        "schema_version": SCHEMA_RECEIPT,
        "kind": "SCOPE_TO_DELIVERY_TEMPORAL_AUTHORITY",
        "agreement_id": agreement.get("agreement_id"),
        "state": state,
        "trusted_as_of": as_of.isoformat().replace("+00:00", "Z"),
        "window_start": start.isoformat().replace("+00:00", "Z"),
        "window_end": end.isoformat().replace("+00:00", "Z"),
        "accepted_at": accepted_at.isoformat().replace("+00:00", "Z") if accepted_at else None,
        "agreement_canonical_sha256": agreement_digest,
        "agreement_raw_sha256": agreement_raw_sha256,
        "observations_canonical_sha256": observations_digest,
        "observations_raw_sha256": observations_raw_sha256,
        "observation_count": len(parsed_observations),
        "temporal_prerequisite_only": True,
        "canonical_scope_validation_still_required": True,
        "current_work_authorized": current_work_authorized,
        "historical_evidence_temporally_admissible": bool(parsed_observations),
        "external_action_authorized": False,
        "payment_authorized": False,
        "delivery_claim_authorized": False,
        "revenue_authorized": False,
        "authority_boundary": (
            "This gate proves only trusted-time chronology. Canonical scope, buyer, evidence, "
            "delivery, payment, provider, and cash gates remain independently mandatory."
        ),
    }
    receipt_core["receipt_sha256"] = digest(receipt_core)
    return receipt_core


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Trusted-time prerequisite for Commons scope-to-delivery.")
    parser.add_argument("--agreement", required=True)
    parser.add_argument("--observations")
    args = parser.parse_args(argv)
    try:
        agreement, agreement_raw_sha256 = read_plain_json(args.agreement, "agreement")
        observations = None
        observations_raw_sha256 = None
        if args.observations:
            observations, observations_raw_sha256 = read_plain_json(args.observations, "observations")
        receipt = evaluate(
            agreement,
            observations,
            as_of=datetime.now(timezone.utc),
            agreement_raw_sha256=agreement_raw_sha256,
            observations_raw_sha256=observations_raw_sha256,
        )
    except (OSError, TemporalAuthorityError) as exc:
        print(json.dumps({"state": "HOLD_INVALID_TEMPORAL_EVIDENCE", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["current_work_authorized"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
