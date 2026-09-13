# SPDX-License-Identifier: MIT
"""Fail-closed qualification gate for Hamilton County OH RFP 065-26/JW.

Only evidence from the controlling solicitation packet/addenda may satisfy buyer
requirements. Secondary mirrors can support discovery, never qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

SCHEMA = "hamilton-oh-065-26-jw-pursuit/v1"
RESULT_SCHEMA = "hamilton-oh-065-26-jw-pursuit-result/v1"

BUYER_REQUIREMENTS = (
    "response_deadline",
    "submission_mechanics",
    "question_deadline_and_process",
    "addenda_complete",
    "scope_and_deliverables",
    "interfaces_and_connectivity",
    "data_standards_and_schemas",
    "security_identity_and_access",
    "audit_logging_and_retention",
    "data_quality_and_validation",
    "monitoring_alerting_and_operations",
    "migration_cutover_and_acceptance",
    "availability_backup_and_disaster_recovery",
    "privacy_records_and_justice_data",
    "implementation_support_and_slas",
    "mandatory_qualifications_and_references",
    "insurance_legal_and_contract_terms",
    "pricing_structure",
    "teaming_and_subcontracting_rules",
)
AUTHORITIES = {"CONTROLLING_OFFICIAL", "OFFICIAL_GENERAL", "SECONDARY_MIRROR", "INTERNAL_EVIDENCE"}
SOURCE_STATUSES = {"AVAILABLE", "BLOCKED", "UNVERIFIED"}
REQ_STATUSES = {"SATISFIED", "UNRESOLVED", "DISQUALIFIER"}
FIT_STATUSES = {"EVIDENCED", "GAP", "UNKNOWN"}
_MAX_BYTES = 2 * 1024 * 1024


class PursuitInputError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PursuitInputError("input must be canonical JSON") from exc
    if len(raw) > _MAX_BYTES:
        raise PursuitInputError("input too large")
    return raw


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, field: str, max_len: int = 2048) -> str:
    if type(value) is not str or not value or value != value.strip() or len(value) > max_len:
        raise PursuitInputError(f"{field} must be bounded non-empty text without edge whitespace")
    if any(ord(ch) < 32 for ch in value):
        raise PursuitInputError(f"{field} contains control characters")
    return value


def _https(value: Any, field: str) -> str:
    text = _text(value, field)
    parsed = urlsplit(text)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise PursuitInputError(f"{field} must be credential-free HTTPS")
    return text


def _exact(obj: Any, keys: set[str], field: str) -> dict[str, Any]:
    if not isinstance(obj, dict) or set(obj) != keys:
        raise PursuitInputError(f"{field} must contain exactly {sorted(keys)}")
    return obj


def _validate(payload: Any) -> dict[str, Any]:
    root = _exact(
        payload,
        {"schema", "opportunity", "sources", "requirements", "capability_fit"},
        "input",
    )
    if root["schema"] != SCHEMA:
        raise PursuitInputError(f"schema must be {SCHEMA}")

    opp = _exact(root["opportunity"], {"buyer", "solicitation_id", "title"}, "opportunity")
    if _text(opp["buyer"], "opportunity.buyer", 200) != "Hamilton County, Ohio":
        raise PursuitInputError("buyer must be Hamilton County, Ohio")
    if _text(opp["solicitation_id"], "opportunity.solicitation_id", 40) != "065-26/JW":
        raise PursuitInputError("solicitation_id must be 065-26/JW")
    _text(opp["title"], "opportunity.title", 200)

    if not isinstance(root["sources"], list) or not root["sources"]:
        raise PursuitInputError("sources must be a non-empty list")
    sources: dict[str, dict[str, Any]] = {}
    normalized_sources = []
    for idx, raw in enumerate(root["sources"]):
        src = _exact(raw, {"id", "authority", "url", "status", "retrieved_at", "sha256"}, f"sources[{idx}]")
        sid = _text(src["id"], f"sources[{idx}].id", 120)
        if sid in sources:
            raise PursuitInputError(f"duplicate source id: {sid}")
        authority = _text(src["authority"], f"sources[{idx}].authority", 40)
        if authority not in AUTHORITIES:
            raise PursuitInputError(f"invalid source authority: {authority}")
        status = _text(src["status"], f"sources[{idx}].status", 20)
        if status not in SOURCE_STATUSES:
            raise PursuitInputError(f"invalid source status: {status}")
        url = _https(src["url"], f"sources[{idx}].url")
        retrieved_at = _text(src["retrieved_at"], f"sources[{idx}].retrieved_at", 40)
        digest = src["sha256"]
        if digest is not None:
            digest = _text(digest, f"sources[{idx}].sha256", 64)
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise PursuitInputError("source sha256 must be lowercase 64-hex")
        if status == "AVAILABLE" and authority == "CONTROLLING_OFFICIAL" and digest is None:
            raise PursuitInputError("available controlling source requires sha256")
        n = {
            "id": sid, "authority": authority, "url": url, "status": status,
            "retrieved_at": retrieved_at, "sha256": digest,
        }
        sources[sid] = n
        normalized_sources.append(n)

    if not isinstance(root["requirements"], list):
        raise PursuitInputError("requirements must be a list")
    reqs: dict[str, dict[str, Any]] = {}
    normalized_reqs = []
    for idx, raw in enumerate(root["requirements"]):
        req = _exact(raw, {"key", "status", "value", "evidence_source_ids", "note"}, f"requirements[{idx}]")
        key = _text(req["key"], f"requirements[{idx}].key", 100)
        if key not in BUYER_REQUIREMENTS:
            raise PursuitInputError(f"unknown requirement key: {key}")
        if key in reqs:
            raise PursuitInputError(f"duplicate requirement key: {key}")
        status = _text(req["status"], f"requirements[{idx}].status", 20)
        if status not in REQ_STATUSES:
            raise PursuitInputError(f"invalid requirement status: {status}")
        ids = req["evidence_source_ids"]
        if not isinstance(ids, list) or any(type(x) is not str for x in ids) or len(set(ids)) != len(ids):
            raise PursuitInputError(f"{key}.evidence_source_ids must be unique strings")
        for sid in ids:
            if sid not in sources:
                raise PursuitInputError(f"{key} references unknown source {sid}")
        note = _text(req["note"], f"requirements[{idx}].note", 1000)
        _canonical(req["value"])
        n = {"key": key, "status": status, "value": req["value"], "evidence_source_ids": ids, "note": note}
        reqs[key] = n
        normalized_reqs.append(n)

    missing = sorted(set(BUYER_REQUIREMENTS) - set(reqs))
    if missing:
        raise PursuitInputError(f"missing buyer requirement rows: {missing}")

    fit = _exact(root["capability_fit"], {"prime", "teaming", "evidence_source_ids", "note"}, "capability_fit")
    prime = _text(fit["prime"], "capability_fit.prime", 20)
    teaming = _text(fit["teaming"], "capability_fit.teaming", 20)
    if prime not in FIT_STATUSES or teaming not in FIT_STATUSES:
        raise PursuitInputError("capability fit must be EVIDENCED, GAP, or UNKNOWN")
    fit_ids = fit["evidence_source_ids"]
    if not isinstance(fit_ids, list) or any(type(x) is not str for x in fit_ids) or len(set(fit_ids)) != len(fit_ids):
        raise PursuitInputError("capability_fit.evidence_source_ids must be unique strings")
    for sid in fit_ids:
        if sid not in sources:
            raise PursuitInputError(f"capability fit references unknown source {sid}")
        if sources[sid]["authority"] != "INTERNAL_EVIDENCE":
            raise PursuitInputError("capability fit may cite only INTERNAL_EVIDENCE")
    fit_note = _text(fit["note"], "capability_fit.note", 1000)

    return {
        "schema": SCHEMA,
        "opportunity": dict(opp),
        "sources": normalized_sources,
        "requirements": normalized_reqs,
        "capability_fit": {"prime": prime, "teaming": teaming, "evidence_source_ids": fit_ids, "note": fit_note},
    }


def evaluate(payload: Any) -> dict[str, Any]:
    normalized = _validate(payload)
    sources = {x["id"]: x for x in normalized["sources"]}
    reqs = {x["key"]: x for x in normalized["requirements"]}

    controlling_available = {
        sid for sid, src in sources.items()
        if src["authority"] == "CONTROLLING_OFFICIAL" and src["status"] == "AVAILABLE" and src["sha256"]
    }
    blockers: list[str] = []
    unsupported: list[str] = []
    hard_disqualifiers: list[str] = []

    for key in BUYER_REQUIREMENTS:
        req = reqs[key]
        controlling_refs = [sid for sid in req["evidence_source_ids"] if sid in controlling_available]
        if req["status"] == "DISQUALIFIER":
            if controlling_refs:
                hard_disqualifiers.append(key)
            else:
                unsupported.append(key)
        elif req["status"] == "SATISFIED":
            if not controlling_refs:
                unsupported.append(key)
        else:
            blockers.append(key)

    if not controlling_available:
        blockers.insert(0, "controlling_solicitation_packet")
    blockers.extend(f"unbound:{key}" for key in unsupported)

    fit = normalized["capability_fit"]
    fit_evidence_ok = bool(fit["evidence_source_ids"]) and all(
        sources[sid]["status"] == "AVAILABLE" for sid in fit["evidence_source_ids"]
    )
    if not fit_evidence_ok:
        blockers.append("capability_evidence")

    decision = "HOLD"
    reason = "critical evidence is incomplete or not bound to controlling official sources"
    if hard_disqualifiers:
        decision = "NO_BID"
        reason = "controlling official evidence proves a hard disqualifier"
    elif not blockers:
        teaming_value = reqs["teaming_and_subcontracting_rules"]["value"]
        teaming_allowed = teaming_value is True
        if fit["prime"] == "EVIDENCED":
            decision = "PRIME"
            reason = "all critical buyer requirements are controlling-source-bound and prime fit is evidenced"
        elif fit["prime"] == "GAP" and fit["teaming"] == "EVIDENCED" and teaming_allowed:
            decision = "TEAMING"
            reason = "prime fit has a gap, teaming fit is evidenced, and controlling terms permit teaming"
        elif fit["prime"] == "GAP" and fit["teaming"] == "GAP":
            decision = "NO_BID"
            reason = "controlling terms are resolved but both prime and teaming fit are evidenced gaps"
        else:
            decision = "HOLD"
            reason = "buyer requirements are resolved but delivery-fit evidence is not decisive"
            blockers.append("delivery_strategy")

    next_actions = []
    if "controlling_solicitation_packet" in blockers:
        next_actions.append("recover the controlling solicitation packet and all addenda from the County procurement system")
    if any(x == "addenda_complete" or x == "unbound:addenda_complete" for x in blockers):
        next_actions.append("establish an addenda-as-of receipt before any go/no-go or submission decision")
    if any(x.startswith("unbound:") or x in BUYER_REQUIREMENTS for x in blockers):
        next_actions.append("bind every critical buyer requirement to controlling official evidence; mirror text is discovery-only")
    if "capability_evidence" in blockers:
        next_actions.append("bind prime/team capability claims to internal evidence; do not invent deployments, certifications, or references")
    if decision == "HOLD":
        next_actions.append("do not contact the buyer, price, sign, or submit from this evaluator; use a separately authorized deduped action after packet recovery")

    core = {
        "schema": RESULT_SCHEMA,
        "opportunity": normalized["opportunity"],
        "decision": decision,
        "reason": reason,
        "controlling_source_ids": sorted(controlling_available),
        "hard_disqualifiers": sorted(hard_disqualifiers),
        "blockers": sorted(set(blockers)),
        "next_actions": next_actions,
        "authority": {
            "secondary_mirror_satisfies_buyer_requirement": False,
            "official_general_satisfies_solicitation_requirement": False,
            "buyer_contact_authorized": False,
            "portal_terms_acceptance_authorized": False,
            "pricing_commitment_authorized": False,
            "proposal_submission_authorized": False,
            "signature_authorized": False,
            "spend_authorized": False,
            "partner_representation_authorized": False,
            "award_or_revenue_claim_authorized": False,
        },
        "source_input_sha256": _sha(normalized),
    }
    result = dict(core)
    result["receipt_sha256"] = _sha(core)
    return result


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise PursuitInputError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load_json(path: Path) -> Any:
    raw = path.read_bytes()
    if len(raw) > _MAX_BYTES:
        raise PursuitInputError("input file too large")
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=lambda x: (_ for _ in ()).throw(PursuitInputError(f"non-finite JSON constant: {x}")),
        )
    except UnicodeDecodeError as exc:
        raise PursuitInputError("input must be UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise PursuitInputError("input must be valid JSON") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(evaluate(load_json(args.input)), indent=2, sort_keys=True))
        return 0
    except (PursuitInputError, OSError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
