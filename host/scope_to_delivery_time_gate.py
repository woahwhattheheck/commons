#!/usr/bin/env python3
"""Trusted-time prerequisite for Commons accepted-scope-to-delivery authority.

The legacy scope_to_delivery composer is a deterministic historical projection. This
module adds the time/chronology authority it intentionally lacks. It never grants
external action, payment, delivery, acceptance, or revenue authority.

Exact raw-byte provenance is granted only by ``evaluate_bytes`` (or the CLI), which
parses and hashes the same bounded bytes internally. Parsed-object helpers compute
chronology/canonical facts only and have no authority toggle. The byte-authority path
also runs the canonical scope composer on those same parsed inputs and binds the
supplied canonical project before current-work authority can become true.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from host import scope_to_delivery as canonical_scope
except ModuleNotFoundError:  # direct ``python host/...`` execution
    import scope_to_delivery as canonical_scope

SCHEMA_AGREEMENT = "commons-scope-agreement/v1"
SCHEMA_OBSERVATIONS = "commons-scope-observations/v1"
SCHEMA_RECEIPT = "commons-scope-time-authority/v1"
MAX_INPUT_BYTES = 2_000_000


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
    if type(raw) is not bytes:
        raise TemporalAuthorityError(f"{field} must be exact bytes")
    if len(raw) > MAX_INPUT_BYTES:
        raise TemporalAuthorityError(f"{field} exceeds {MAX_INPUT_BYTES} bytes")
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


def read_plain_bytes(path: str | Path, field: str) -> bytes:
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
        return b"".join(chunks)
    finally:
        os.close(fd)


def read_plain_json(path: str | Path, field: str) -> tuple[Any, str]:
    """Compatibility reader; the returned hash is informational, not authority."""
    raw = read_plain_bytes(path, field)
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


def _canonical_project(agreement: Any, observations: Any | None) -> dict[str, Any]:
    """Run the canonical scope composer on the same parsed temporal inputs."""
    try:
        catalog = canonical_scope.load_json(canonical_scope.DEFAULT_CATALOG)
        bindings = canonical_scope.load_bindings(canonical_scope.DEFAULT_BINDINGS)
        return canonical_scope.compose_project(agreement, catalog, bindings, observations, None)
    except canonical_scope.PipelineError as exc:
        raise TemporalAuthorityError("exact temporal inputs fail canonical scope validation") from exc


def _bind_project(supplied: Any | None, expected: dict[str, Any], agreement_id: str) -> tuple[bool, str]:
    expected_sha = digest(expected)
    if supplied is None:
        return False, expected_sha
    supplied = _require_dict(supplied, "canonical_project")
    if supplied.get("schema_version") != canonical_scope.SCHEMA_PROJECT:
        raise TemporalAuthorityError("canonical_project schema_version is invalid")
    if supplied.get("kind") != "SCOPE_TO_DELIVERY_PROJECT":
        raise TemporalAuthorityError("canonical_project kind is invalid")
    if supplied.get("agreement_id") != agreement_id:
        raise TemporalAuthorityError("canonical_project agreement_id does not match temporal agreement")
    supplied_sha = digest(supplied)
    if not hmac.compare_digest(supplied_sha, expected_sha):
        raise TemporalAuthorityError("canonical_project does not bind the exact temporal agreement/observations")
    return True, expected_sha


def verify_project_binding(project: Any, receipt: Any) -> dict[str, Any]:
    """Fail closed unless one canonical project is exactly the project time-authorized by receipt."""
    project = _require_dict(project, "canonical_project")
    receipt = _require_dict(receipt, "temporal_receipt")
    if receipt.get("schema_version") != SCHEMA_RECEIPT:
        raise TemporalAuthorityError("temporal_receipt schema_version is invalid")
    if receipt.get("canonical_scope_validated") is not True:
        raise TemporalAuthorityError("temporal_receipt lacks canonical scope validation")
    if receipt.get("canonical_project_bound") is not True:
        raise TemporalAuthorityError("temporal_receipt lacks canonical project binding")
    expected = receipt.get("canonical_project_sha256")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise TemporalAuthorityError("temporal_receipt canonical project digest is invalid")
    if project.get("agreement_id") != receipt.get("agreement_id"):
        raise TemporalAuthorityError("canonical project agreement_id does not match temporal receipt")
    actual = digest(project)
    if not hmac.compare_digest(actual, expected):
        raise TemporalAuthorityError("canonical project and temporal receipt are from different artifacts")
    return {"valid": True, "canonical_project_sha256": expected}


def _temporal_facts(agreement: Any, observations: Any | None, *, as_of: datetime) -> dict[str, Any]:
    """Compute chronology/canonical facts only; this helper cannot mint authority."""
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
        temporal_ready = False
    elif as_of < start:
        state = "HOLD_WINDOW_NOT_STARTED"
        temporal_ready = False
    elif as_of > end:
        state = "HOLD_WINDOW_EXPIRED"
        temporal_ready = False
    else:
        state = "TEMPORAL_PREREQUISITE_READY"
        temporal_ready = True
    return {
        "agreement_id": agreement.get("agreement_id"),
        "state": state,
        "temporal_ready": temporal_ready,
        "trusted_as_of": as_of.isoformat().replace("+00:00", "Z"),
        "window_start": start.isoformat().replace("+00:00", "Z"),
        "window_end": end.isoformat().replace("+00:00", "Z"),
        "accepted_at": accepted_at.isoformat().replace("+00:00", "Z") if accepted_at else None,
        "agreement_canonical_sha256": digest(agreement),
        "observations_canonical_sha256": observations_digest,
        "observation_count": len(parsed_observations),
        "historical_evidence_temporally_admissible": bool(parsed_observations),
    }


def _receipt_base(facts: dict[str, Any], *, state: str) -> dict[str, Any]:
    """Build non-authority receipt fields from chronology facts only."""
    return {
        "schema_version": SCHEMA_RECEIPT,
        "kind": "SCOPE_TO_DELIVERY_TEMPORAL_AUTHORITY",
        "agreement_id": facts["agreement_id"],
        "state": state,
        "trusted_as_of": facts["trusted_as_of"],
        "window_start": facts["window_start"],
        "window_end": facts["window_end"],
        "accepted_at": facts["accepted_at"],
        "agreement_canonical_sha256": facts["agreement_canonical_sha256"],
        "observations_canonical_sha256": facts["observations_canonical_sha256"],
        "observation_count": facts["observation_count"],
        "temporal_prerequisite_only": True,
        "canonical_scope_validation_still_required": True,
        "historical_evidence_temporally_admissible": facts["historical_evidence_temporally_admissible"],
        "external_action_authorized": False,
        "payment_authorized": False,
        "delivery_claim_authorized": False,
        "revenue_authorized": False,
    }


def evaluate(agreement: Any, observations: Any | None, *, as_of: datetime) -> dict[str, Any]:
    """Evaluate parsed objects without any raw-byte/canonical-project authority capability."""
    facts = _temporal_facts(agreement, observations, as_of=as_of)
    state = "HOLD_RAW_PROVENANCE_UNVERIFIED" if facts["temporal_ready"] else facts["state"]
    receipt = {
        **_receipt_base(facts, state=state),
        "agreement_raw_sha256": None,
        "observations_raw_sha256": None,
        "raw_byte_provenance_verified": False,
        "provenance_mode": "CANONICAL_OBJECT_ONLY",
        "canonical_scope_validated": False,
        "canonical_project_bound": False,
        "canonical_project_sha256": None,
        "canonical_binding_required": True,
        "current_work_authorized": False,
        "authority_boundary": (
            "Parsed-object evaluation proves chronology only. Exact-byte custody and same-input canonical "
            "project binding require evaluate_bytes()."
        ),
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def _bounded_bytes(raw: Any, field: str) -> bytes:
    if type(raw) is not bytes:
        raise TemporalAuthorityError(f"{field} must be exact bytes")
    if len(raw) > MAX_INPUT_BYTES:
        raise TemporalAuthorityError(f"{field} exceeds {MAX_INPUT_BYTES} bytes")
    return raw


def evaluate_bytes(
    agreement_raw: bytes,
    observations_raw: bytes | None,
    *,
    as_of: datetime,
    canonical_project: Any | None = None,
) -> dict[str, Any]:
    """Parse/hash/validate one exact byte pair and bind its canonical project."""
    agreement_raw = _bounded_bytes(agreement_raw, "agreement")
    agreement = strict_loads(agreement_raw, "agreement")
    observations = None
    observations_raw_sha256 = None
    if observations_raw is not None:
        observations_raw = _bounded_bytes(observations_raw, "observations")
        observations = strict_loads(observations_raw, "observations")
        observations_raw_sha256 = hashlib.sha256(observations_raw).hexdigest()

    expected_project = _canonical_project(agreement, observations)
    project_bound, project_sha = _bind_project(
        canonical_project, expected_project, agreement.get("agreement_id") if isinstance(agreement, dict) else ""
    )
    facts = _temporal_facts(agreement, observations, as_of=as_of)
    state = facts["state"]
    if facts["temporal_ready"] and not project_bound:
        state = "HOLD_CANONICAL_PROJECT_UNBOUND"
    current_work_authorized = facts["temporal_ready"] and project_bound
    receipt = {
        **_receipt_base(facts, state=state),
        "agreement_raw_sha256": hashlib.sha256(agreement_raw).hexdigest(),
        "observations_raw_sha256": observations_raw_sha256,
        "raw_byte_provenance_verified": True,
        "provenance_mode": "EXACT_RAW_BYTES_VERIFIED",
        "canonical_scope_validated": True,
        "canonical_project_bound": project_bound,
        "canonical_project_sha256": project_sha,
        "canonical_binding_required": True,
        "current_work_authorized": current_work_authorized,
        "authority_boundary": (
            "This gate proves trusted-time chronology and exact input-byte custody only when the same inputs "
            "also pass the canonical scope composer and the supplied canonical project digest is exactly bound. "
            "Buyer, delivery, payment, provider, and cash gates remain independently mandatory."
        ),
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Trusted-time prerequisite for Commons scope-to-delivery.")
    parser.add_argument("--agreement", required=True)
    parser.add_argument("--observations")
    parser.add_argument("--project", help="canonical scope_to_delivery.py project JSON for the same inputs")
    args = parser.parse_args(argv)
    try:
        agreement_raw = read_plain_bytes(args.agreement, "agreement")
        observations_raw = read_plain_bytes(args.observations, "observations") if args.observations else None
        project = None
        if args.project:
            project = strict_loads(read_plain_bytes(args.project, "canonical_project"), "canonical_project")
        receipt = evaluate_bytes(
            agreement_raw,
            observations_raw,
            as_of=datetime.now(timezone.utc),
            canonical_project=project,
        )
    except (OSError, TemporalAuthorityError) as exc:
        print(json.dumps({"state": "HOLD_INVALID_TEMPORAL_EVIDENCE", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["current_work_authorized"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
