from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from .canonical import (
    BidVeilError,
    canonical_time,
    digest_json,
    domain_hash,
    parse_time,
    require_bool,
    require_hex64,
    require_id,
    require_int,
    require_list,
    require_object,
    require_str,
)

OPPORTUNITY_SCHEMA = "bidveil.opportunity.v1"
PROFILE_SCHEMA = "bidveil.private-profile.v1"
RECEIPT_SCHEMA = "bidveil.receipt.v1"
MODE = "LOCAL_SEMANTIC_SIMULATION_NOT_ZK"


def _check_exact_keys(obj: dict[str, Any], allowed: set[str], name: str) -> None:
    extra = set(obj) - allowed
    if extra:
        raise BidVeilError(f"{name} has unknown fields: {', '.join(sorted(extra))}")


def normalize_opportunity(raw: Any) -> dict[str, Any]:
    obj = require_object(raw, "opportunity")
    _check_exact_keys(
        obj,
        {"schema", "opportunity_id", "generation", "issued_at", "valid_until", "requirements"},
        "opportunity",
    )
    if require_str(obj.get("schema"), "opportunity.schema") != OPPORTUNITY_SCHEMA:
        raise BidVeilError("unsupported opportunity schema")
    opportunity_id = require_id(obj.get("opportunity_id"), "opportunity.opportunity_id")
    generation = require_int(obj.get("generation"), "opportunity.generation", minimum=1)
    issued = parse_time(obj.get("issued_at"), "opportunity.issued_at")
    valid_until = parse_time(obj.get("valid_until"), "opportunity.valid_until")
    if valid_until <= issued:
        raise BidVeilError("opportunity.valid_until must be after issued_at")

    requirements = require_list(obj.get("requirements"), "opportunity.requirements")
    if not requirements or len(requirements) > 64:
        raise BidVeilError("opportunity.requirements must contain 1..64 rows")

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row_raw in enumerate(requirements):
        row = require_object(row_raw, f"requirement[{index}]")
        _check_exact_keys(
            row,
            {"id", "kind", "expected", "minimum", "allowed", "issuer_allowlist", "max_age_seconds"},
            f"requirement[{index}]",
        )
        rid = require_id(row.get("id"), f"requirement[{index}].id")
        if rid in seen:
            raise BidVeilError(f"duplicate requirement id: {rid}")
        seen.add(rid)
        kind = require_str(row.get("kind"), f"requirement[{index}].kind")
        if kind not in {"boolean", "minimum", "enum"}:
            raise BidVeilError(f"unsupported requirement kind: {kind}")

        issuers = require_list(row.get("issuer_allowlist"), f"requirement[{index}].issuer_allowlist")
        if not issuers:
            raise BidVeilError(f"requirement {rid} requires at least one allowed issuer")
        norm_issuers = sorted({require_id(v, f"requirement[{index}].issuer") for v in issuers})
        if len(norm_issuers) != len(issuers):
            raise BidVeilError(f"requirement {rid} contains duplicate issuers")

        out: dict[str, Any] = {
            "id": rid,
            "kind": kind,
            "issuer_allowlist": norm_issuers,
        }
        if "max_age_seconds" in row:
            out["max_age_seconds"] = require_int(
                row["max_age_seconds"], f"requirement[{index}].max_age_seconds", minimum=1
            )
        if kind == "boolean":
            if set(row) & {"minimum", "allowed"}:
                raise BidVeilError(f"boolean requirement {rid} cannot define minimum/allowed")
            out["expected"] = require_bool(row.get("expected"), f"requirement[{index}].expected")
        elif kind == "minimum":
            if set(row) & {"expected", "allowed"}:
                raise BidVeilError(f"minimum requirement {rid} cannot define expected/allowed")
            out["minimum"] = require_int(row.get("minimum"), f"requirement[{index}].minimum", minimum=0)
        else:
            if set(row) & {"expected", "minimum"}:
                raise BidVeilError(f"enum requirement {rid} cannot define expected/minimum")
            allowed = require_list(row.get("allowed"), f"requirement[{index}].allowed")
            if not allowed:
                raise BidVeilError(f"enum requirement {rid} must have allowed values")
            norm_allowed = sorted({require_id(v, f"requirement[{index}].allowed") for v in allowed})
            if len(norm_allowed) != len(allowed):
                raise BidVeilError(f"enum requirement {rid} contains duplicate allowed values")
            out["allowed"] = norm_allowed
        normalized.append(out)

    normalized.sort(key=lambda row: row["id"])
    return {
        "schema": OPPORTUNITY_SCHEMA,
        "opportunity_id": opportunity_id,
        "generation": generation,
        "issued_at": canonical_time(issued),
        "valid_until": canonical_time(valid_until),
        "requirements": normalized,
    }


def normalize_profile(raw: Any) -> dict[str, Any]:
    obj = require_object(raw, "private_profile")
    _check_exact_keys(obj, {"schema", "subject_secret_hex", "claim_salt_hex", "claims"}, "private_profile")
    if require_str(obj.get("schema"), "private_profile.schema") != PROFILE_SCHEMA:
        raise BidVeilError("unsupported private profile schema")
    subject_secret = require_hex64(obj.get("subject_secret_hex"), "private_profile.subject_secret_hex")
    salt = require_hex64(obj.get("claim_salt_hex"), "private_profile.claim_salt_hex")
    claims = require_list(obj.get("claims"), "private_profile.claims")
    if len(claims) > 64:
        raise BidVeilError("private_profile.claims may contain at most 64 rows")

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row_raw in enumerate(claims):
        row = require_object(row_raw, f"claim[{index}]")
        _check_exact_keys(
            row,
            {"requirement_id", "issuer_id", "observed_at", "expires_at", "evidence_sha256", "value"},
            f"claim[{index}]",
        )
        rid = require_id(row.get("requirement_id"), f"claim[{index}].requirement_id")
        if rid in seen:
            raise BidVeilError(f"duplicate claim for requirement: {rid}")
        seen.add(rid)
        issuer = require_id(row.get("issuer_id"), f"claim[{index}].issuer_id")
        observed = parse_time(row.get("observed_at"), f"claim[{index}].observed_at")
        expires = parse_time(row.get("expires_at"), f"claim[{index}].expires_at")
        if expires <= observed:
            raise BidVeilError(f"claim {rid} expires_at must be after observed_at")
        evidence = require_hex64(row.get("evidence_sha256"), f"claim[{index}].evidence_sha256")
        value = row.get("value")
        if isinstance(value, float) or value is None or isinstance(value, (dict, list)):
            raise BidVeilError(f"claim {rid} value must be boolean, integer, or identifier string")
        if isinstance(value, str):
            value = require_id(value, f"claim[{index}].value")
        elif isinstance(value, bool):
            pass
        elif isinstance(value, int):
            value = require_int(value, f"claim[{index}].value", minimum=0)
        else:
            raise BidVeilError(f"claim {rid} value has unsupported type")
        normalized.append(
            {
                "requirement_id": rid,
                "issuer_id": issuer,
                "observed_at": canonical_time(observed),
                "expires_at": canonical_time(expires),
                "evidence_sha256": evidence,
                "value": value,
            }
        )
    normalized.sort(key=lambda row: row["requirement_id"])
    return {
        "schema": PROFILE_SCHEMA,
        "subject_secret_hex": subject_secret,
        "claim_salt_hex": salt,
        "claims": normalized,
    }


def _evaluate_requirement(requirement: dict[str, Any], claim: dict[str, Any] | None, at: datetime) -> str:
    if claim is None:
        return "MISSING"
    if claim["issuer_id"] not in requirement["issuer_allowlist"]:
        return "HOLD_WRONG_ISSUER"
    observed = parse_time(claim["observed_at"], "claim.observed_at")
    expires = parse_time(claim["expires_at"], "claim.expires_at")
    if observed > at:
        return "HOLD_FUTURE_EVIDENCE"
    if expires <= at:
        return "UNSATISFIED_EXPIRED"
    max_age = requirement.get("max_age_seconds")
    if max_age is not None and int((at - observed).total_seconds()) > max_age:
        return "UNSATISFIED_STALE"

    kind = requirement["kind"]
    value = claim["value"]
    if kind == "boolean":
        if not isinstance(value, bool):
            return "HOLD_TYPE_MISMATCH"
        return "SATISFIED" if value is requirement["expected"] else "UNSATISFIED"
    if kind == "minimum":
        if isinstance(value, bool) or not isinstance(value, int):
            return "HOLD_TYPE_MISMATCH"
        return "SATISFIED" if value >= requirement["minimum"] else "UNSATISFIED"
    if not isinstance(value, str):
        return "HOLD_TYPE_MISMATCH"
    return "SATISFIED" if value in requirement["allowed"] else "UNSATISFIED"


def prove(opportunity_raw: Any, profile_raw: Any, at_raw: str) -> dict[str, Any]:
    opportunity = normalize_opportunity(opportunity_raw)
    profile = normalize_profile(profile_raw)
    at = parse_time(at_raw, "evaluation_time")
    issued = parse_time(opportunity["issued_at"], "opportunity.issued_at")
    valid_until = parse_time(opportunity["valid_until"], "opportunity.valid_until")
    if at < issued:
        raise BidVeilError("evaluation_time predates opportunity issuance")

    opportunity_digest = digest_json(opportunity)
    requirement_universe_digest = digest_json(opportunity["requirements"])
    claim_commitment = domain_hash(
        "bidveil:claim-commitment:v1",
        profile["claim_salt_hex"],
        digest_json(profile["claims"]),
    )
    subject_commitment = domain_hash(
        "bidveil:opportunity-subject:v1",
        opportunity_digest,
        profile["subject_secret_hex"],
    )
    nullifier = domain_hash(
        "bidveil:opportunity-nullifier:v1",
        opportunity_digest,
        profile["subject_secret_hex"],
    )

    claims_by_id = {row["requirement_id"]: row for row in profile["claims"]}
    unknown_claims = sorted(set(claims_by_id) - {row["id"] for row in opportunity["requirements"]})
    results: list[dict[str, str]] = []
    if at >= valid_until:
        results = [{"requirement_id": row["id"], "status": "HOLD_OPPORTUNITY_EXPIRED"} for row in opportunity["requirements"]]
    else:
        for requirement in opportunity["requirements"]:
            results.append(
                {
                    "requirement_id": requirement["id"],
                    "status": _evaluate_requirement(requirement, claims_by_id.get(requirement["id"]), at),
                }
            )
    if unknown_claims:
        results.append({"requirement_id": "__profile__", "status": "HOLD_UNKNOWN_CLAIMS"})

    statuses = [row["status"] for row in results]
    if any(status.startswith("HOLD_") for status in statuses):
        decision = "HOLD"
    elif all(status == "SATISFIED" for status in statuses):
        decision = "QUALIFIED"
    else:
        decision = "NOT_QUALIFIED"

    body = {
        "schema": RECEIPT_SCHEMA,
        "mode": MODE,
        "proof_authority": "LOCAL_REPLAY_ONLY",
        "opportunity_id": opportunity["opportunity_id"],
        "opportunity_generation": opportunity["generation"],
        "opportunity_digest": opportunity_digest,
        "requirement_universe_digest": requirement_universe_digest,
        "claim_commitment": claim_commitment,
        "subject_commitment": subject_commitment,
        "nullifier": nullifier,
        "evaluated_at": canonical_time(at),
        "decision": decision,
        "revealed_results": results,
        "private_values_revealed": False,
        "onchain_proof_verified": False,
    }
    body["receipt_sha256"] = digest_json(body)
    return body


def verify_receipt_integrity(receipt_raw: Any) -> bool:
    receipt = deepcopy(require_object(receipt_raw, "receipt"))
    supplied = require_hex64(receipt.pop("receipt_sha256", None), "receipt.receipt_sha256")
    if receipt.get("schema") != RECEIPT_SCHEMA or receipt.get("mode") != MODE:
        return False
    return digest_json(receipt) == supplied


def verify_replay(opportunity_raw: Any, profile_raw: Any, receipt_raw: Any, at_raw: str) -> bool:
    if not verify_receipt_integrity(receipt_raw):
        return False
    expected = prove(opportunity_raw, profile_raw, at_raw)
    return expected == receipt_raw
