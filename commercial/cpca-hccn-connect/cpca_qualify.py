#!/usr/bin/env python3
"""Deterministic truth-bound qualifier for CPCA HCCN Connect.

This tool never invents experience, pricing, signatures, references, or submission
state. It evaluates caller-supplied evidence against a source-bound gate spec.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

ALLOWED_GATE_STATUS = {"PROVEN", "PARTNER_CURABLE", "MISSING", "HOLD", "NOT_APPLICABLE"}
FINAL_STATES = {"PRIME_READY", "TEAMING_READY", "HOLD", "NO_BID"}


def _load(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top-level JSON must be an object")
    return value


def _parse_when(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("current_time must contain an explicit UTC offset")
    return parsed


def _required_gate_ids(spec: Dict[str, Any], service_type: str) -> List[str]:
    all_ids = [g["id"] for g in spec["mandatory_direct_prime_gates"]]
    specific = set(spec["service_type_specific_gate_ids"][service_type])
    track_ids = {"technical_assistance_track_record", "group_training_track_record"}
    return [gid for gid in all_ids if gid not in track_ids or gid in specific]


def _validate_source(spec: Dict[str, Any], evidence: Dict[str, Any]) -> None:
    source = evidence.get("source_packet", {})
    expected = spec["source_packet"]
    for key in ("gmail_message_id", "filename", "sha256"):
        if source.get(key) != expected.get(key):
            raise ValueError(
                f"source packet mismatch for {key}: expected {expected.get(key)!r}, "
                f"got {source.get(key)!r}"
            )


def _status_map(evidence: Dict[str, Any]) -> Dict[str, str]:
    raw = evidence.get("gate_status", {})
    if not isinstance(raw, dict):
        raise ValueError("gate_status must be an object")
    out: Dict[str, str] = {}
    for key, value in raw.items():
        if value not in ALLOWED_GATE_STATUS:
            raise ValueError(f"invalid gate status {value!r} for {key}")
        out[str(key)] = str(value)
    return out


def _derive_count_gates(status: Dict[str, str], evidence: Dict[str, Any], domain_meta: Dict[str, Any]) -> None:
    refs = evidence.get("client_references", [])
    if len(refs) >= 3 and all(isinstance(x, dict) and x.get("source") for x in refs):
        status["client_references"] = "PROVEN"
    elif status.get("client_references") == "PROVEN":
        raise ValueError("client_references cannot be PROVEN without >=3 source-bound references")

    engagements = evidence.get("comparable_engagements", [])
    if not isinstance(engagements, list):
        raise ValueError("comparable_engagements must be a list")
    completed = sum(1 for e in engagements if e.get("state") in {"COMPLETED", "SUBSTANTIALLY_COMPLETED"})
    total = len(engagements)
    if domain_meta.get("emerging"):
        recent_ok = completed >= 1 and total >= 2
    else:
        recent_ok = completed >= 3
    if recent_ok and all(e.get("source") for e in engagements):
        status["recent_domain_engagements"] = "PROVEN"
    elif status.get("recent_domain_engagements") == "PROVEN":
        raise ValueError("recent_domain_engagements cannot be PROVEN without source-bound minimum counts")

    safety_net = [e for e in engagements if e.get("safety_net_primary_care") is True and e.get("source")]
    if safety_net:
        status["safety_net_experience"] = "PROVEN"
    elif status.get("safety_net_experience") == "PROVEN":
        raise ValueError("safety_net_experience cannot be PROVEN without a source-bound comparable engagement")


def evaluate(spec: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
    _validate_source(spec, evidence)
    service_type = evidence.get("service_type")
    if service_type not in spec["service_type_specific_gate_ids"]:
        raise ValueError(f"unsupported service_type: {service_type!r}")
    domain = evidence.get("domain")
    if domain not in spec["domains"]:
        raise ValueError(f"unsupported domain: {domain!r}")

    now = _parse_when(evidence["current_time"])
    due = dt.datetime.fromisoformat(spec["opportunity"]["due_at"])
    if now > due:
        return {
            "schema": "cpca-hccn-qualification-result/v1",
            "state": "NO_BID",
            "reason": "deadline_passed",
            "due_at": due.isoformat(),
            "evaluated_at": now.isoformat(),
            "blockers": [],
        }

    status = _status_map(evidence)
    _derive_count_gates(status, evidence, spec["domains"][domain])
    required_ids = _required_gate_ids(spec, service_type)
    normalized = {gid: status.get(gid, "MISSING") for gid in required_ids}
    blockers = [gid for gid, st in normalized.items() if st != "PROVEN"]

    bid_model = evidence.get("bid_model", "direct_prime")
    if bid_model == "direct_prime":
        state = "PRIME_READY" if not blockers else "HOLD"
        reason = "all_direct_prime_gates_proven" if not blockers else "unproven_direct_prime_gates"
    elif bid_model == "healthcare_prime_subcontract":
        prime = evidence.get("healthcare_prime", {})
        prime_ok = bool(
            prime.get("name")
            and prime.get("eligibility_source")
            and prime.get("safety_net_experience_source")
            and prime.get("relationship_authority") is True
        )
        support_ids = set(evidence.get("tjlabs_support_gate_ids", []))
        unsupported = [gid for gid in support_ids if normalized.get(gid, "MISSING") != "PROVEN"]
        if prime_ok and support_ids and not unsupported:
            state = "TEAMING_READY"
            reason = "named_healthcare_prime_and_support_scope_proven"
        else:
            state = "HOLD"
            reason = "teaming_prime_or_support_scope_unproven"
            if not prime_ok:
                blockers.append("named_healthcare_prime")
            blockers.extend(f"support:{gid}" for gid in unsupported)
    else:
        raise ValueError(f"unsupported bid_model: {bid_model!r}")

    result = {
        "schema": "cpca-hccn-qualification-result/v1",
        "state": state,
        "reason": reason,
        "domain": domain,
        "service_type": service_type,
        "bid_model": bid_model,
        "due_at": due.isoformat(),
        "evaluated_at": now.isoformat(),
        "gate_status": normalized,
        "blockers": sorted(set(blockers)),
        "authority": {
            "buyer_contact_authorized": False,
            "price_committed": False,
            "attestation_signed": False,
            "proposal_submitted": False,
            "award_claimed": False,
            "payment_claimed": False,
            "revenue_claimed": False
        }
    }
    assert result["state"] in FINAL_STATES
    return result


def canonical_digest(value: Dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--spec", type=Path, default=Path(__file__).with_name("qualification_spec.json"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)

    spec = _load(args.spec)
    evidence = _load(args.evidence)
    result = evaluate(spec, evidence)
    result["receipt_sha256"] = canonical_digest(result)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
