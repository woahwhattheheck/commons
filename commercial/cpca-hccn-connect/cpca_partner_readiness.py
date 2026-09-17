#!/usr/bin/env python3
"""Truth-narrowed healthcare-prime readiness for CPCA HCCN Connect.

The legacy qualifier's subcontract ``TEAMING_READY`` value proves only that a
named prime, relationship flag, and selected TJLabs support gates are present.
It does not by itself prove the complete applicant/application gate set.  This
module preserves that useful workshare signal while independently holding CPCA
application readiness until every mandatory gate and its retained source
manifest are complete.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

SCHEMA = "cpca-partner-readiness/v1"
MAX_JSON_BYTES = 1_048_576
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SOURCE_KEYS = {"source_id", "sha256"}
AUTHORITY = {
    "buyer_contact_authorized": False,
    "credential_use_authorized": False,
    "price_committed": False,
    "staff_committed": False,
    "attestation_signed": False,
    "proposal_submitted": False,
    "award_claimed": False,
    "payment_claimed": False,
    "revenue_claimed": False,
}


def _pairs_no_duplicates(pairs: Sequence[tuple[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _load(path: Path) -> Dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError(f"{path}: JSON exceeds {MAX_JSON_BYTES} bytes")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs_no_duplicates)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top-level JSON must be an object")
    return value


def canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def canonical_digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _required_gate_ids(spec: Mapping[str, Any], service_type: str) -> List[str]:
    service_map = spec.get("service_type_specific_gate_ids")
    gates = spec.get("mandatory_direct_prime_gates")
    if not isinstance(service_map, dict) or service_type not in service_map:
        raise ValueError(f"unsupported service_type: {service_type!r}")
    if not isinstance(gates, list):
        raise ValueError("mandatory_direct_prime_gates must be a list")
    specific_raw = service_map[service_type]
    if not isinstance(specific_raw, list) or not all(isinstance(x, str) for x in specific_raw):
        raise ValueError(f"service_type {service_type!r} has malformed gate list")
    specific = set(specific_raw)
    track_ids = {"technical_assistance_track_record", "group_training_track_record"}
    out: List[str] = []
    for row in gates:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise ValueError("mandatory gate row missing string id")
        gate_id = row["id"]
        if gate_id not in track_ids or gate_id in specific:
            out.append(gate_id)
    if not out or len(out) != len(set(out)):
        raise ValueError("required gate ids must be nonempty and unique")
    return out


def _source_object(value: Any, label: str) -> Dict[str, str]:
    if not isinstance(value, dict) or set(value) != SOURCE_KEYS:
        raise ValueError(f"{label} must contain exactly source_id and sha256")
    source_id = value.get("source_id")
    digest = value.get("sha256")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError(f"{label}.source_id must be a nonempty string")
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        raise ValueError(f"{label}.sha256 must be lowercase 64-hex")
    return {"source_id": source_id.strip(), "sha256": digest}


def _application_manifest_blockers(
    spec: Mapping[str, Any], evidence: Mapping[str, Any], required_ids: Sequence[str]
) -> List[str]:
    manifest = evidence.get("partner_application_evidence")
    if manifest is None:
        return ["partner_application_evidence"]
    if not isinstance(manifest, dict):
        raise ValueError("partner_application_evidence must be an object")

    blockers: List[str] = []
    expected_spec_sha = canonical_digest(spec)
    if manifest.get("qualification_spec_sha256") != expected_spec_sha:
        blockers.append("qualification_spec_sha256")

    prime = evidence.get("healthcare_prime")
    prime_name = prime.get("name") if isinstance(prime, dict) else None
    if not isinstance(prime_name, str) or not prime_name.strip():
        blockers.append("healthcare_prime.name")
    elif manifest.get("prime_legal_name") != prime_name.strip():
        blockers.append("prime_legal_name")

    if manifest.get("domain") != evidence.get("domain"):
        blockers.append("domain")
    if manifest.get("service_type") != evidence.get("service_type"):
        blockers.append("service_type")

    for key in (
        "prime_identity_source",
        "relationship_authority_source",
        "submission_authority_source",
        "application_package_source",
    ):
        value = manifest.get(key)
        if value is None:
            blockers.append(key)
        else:
            _source_object(value, f"partner_application_evidence.{key}")

    gate_sources = manifest.get("gate_sources")
    if not isinstance(gate_sources, dict):
        blockers.append("gate_sources")
        gate_sources = {}
    unknown = sorted(set(gate_sources) - set(required_ids))
    if unknown:
        raise ValueError(f"unknown partner application gate source ids: {unknown}")
    for gate_id in required_ids:
        rows = gate_sources.get(gate_id)
        if not isinstance(rows, list) or not rows:
            blockers.append(f"gate_source:{gate_id}")
            continue
        seen: set[tuple[str, str]] = set()
        for index, row in enumerate(rows):
            normalized = _source_object(row, f"gate_sources.{gate_id}[{index}]")
            identity = (normalized["source_id"], normalized["sha256"])
            if identity in seen:
                raise ValueError(f"duplicate source object for gate {gate_id}: {identity[0]}")
            seen.add(identity)
    return blockers


def _load_legacy_module(path: Path):
    spec = importlib.util.spec_from_file_location("cpca_qualify_legacy_runtime", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load legacy qualifier: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "evaluate", None)):
        raise ValueError("legacy qualifier does not expose evaluate")
    return module


def compile_partner_readiness(
    spec: Mapping[str, Any],
    evidence: Mapping[str, Any],
    legacy_result: Mapping[str, Any],
) -> Dict[str, Any]:
    if evidence.get("bid_model") != "healthcare_prime_subcontract":
        raise ValueError("partner readiness requires bid_model=healthcare_prime_subcontract")
    if not isinstance(legacy_result, dict):
        raise ValueError("legacy_result must be an object")

    legacy_state = legacy_result.get("state")
    legacy_reason = legacy_result.get("reason")
    raw_blockers = legacy_result.get("blockers", [])
    if not isinstance(raw_blockers, list) or not all(isinstance(x, str) and x for x in raw_blockers):
        raise ValueError("legacy blockers must be a list of nonempty strings")
    legacy_blockers = sorted(set(raw_blockers))

    required_ids = _required_gate_ids(spec, str(evidence.get("service_type")))
    gate_status = legacy_result.get("gate_status", {})
    if not isinstance(gate_status, dict):
        gate_status = {}
    non_proven = sorted(gate_id for gate_id in required_ids if gate_status.get(gate_id) != "PROVEN")

    if legacy_state == "NO_BID":
        workshare_state = "NO_BID"
        application_state = "NO_BID"
        application_blockers: List[str] = []
        state = "NO_BID"
        reason = "legacy_deadline_or_hard_stop"
    else:
        discussion_ready = legacy_state == "TEAMING_READY"
        workshare_state = "DISCUSSION_READY" if discussion_ready else "HOLD"
        manifest_blockers = _application_manifest_blockers(spec, evidence, required_ids)
        manifest_complete = not manifest_blockers
        application_blockers = sorted(
            set(
                legacy_blockers
                + non_proven
                + manifest_blockers
                + ["provider_authenticated_prime_application_evidence"]
            )
        )
        # This generation has no provider-authenticated private evidence adapter.
        # A caller-supplied manifest may show what has been assembled, but it can
        # never authorize application readiness by itself.
        application_state = "HOLD"
        if discussion_ready:
            state = "WORKSHARE_DISCUSSION_READY"
            reason = (
                "workshare_signal_and_manifest_complete_but_application_evidence_unauthenticated"
                if manifest_complete and not legacy_blockers and not non_proven
                else "workshare_signal_only_application_gates_unresolved"
            )
        else:
            state = "HOLD"
            reason = "workshare_or_prime_signal_unresolved"

    result: Dict[str, Any] = {
        "schema": SCHEMA,
        "state": state,
        "reason": reason,
        "domain": evidence.get("domain"),
        "service_type": evidence.get("service_type"),
        "bid_model": evidence.get("bid_model"),
        "legacy_workshare_signal": {
            "state": legacy_state,
            "reason": legacy_reason,
            "blockers": legacy_blockers,
            "application_authority": False,
        },
        "workshare": {
            "state": workshare_state,
            "discussion_artifact_only": workshare_state == "DISCUSSION_READY",
        },
        "application": {
            "state": application_state,
            "blockers": application_blockers,
            "source_manifest_required": True,
            "provider_authenticated_evidence_available": False,
            "caller_manifest_can_authorize_readiness": False,
        },
        "authority": dict(AUTHORITY),
    }
    if result["application"]["state"] == "TEAMING_READY" and result["application"]["blockers"]:
        raise ValueError("internal invariant: application readiness cannot carry blockers")
    return result


def compile_from_evidence(
    spec: Mapping[str, Any], evidence: Mapping[str, Any], legacy_path: Path | None = None
) -> Dict[str, Any]:
    path = legacy_path or Path(__file__).with_name("cpca_qualify.py")
    legacy = _load_legacy_module(path)
    legacy_result = legacy.evaluate(dict(spec), dict(evidence))
    return compile_partner_readiness(spec, evidence, legacy_result)


def make_receipt(spec: Mapping[str, Any], evidence: Mapping[str, Any], legacy_path: Path | None = None) -> Dict[str, Any]:
    result = compile_from_evidence(spec, evidence, legacy_path)
    result["receipt_sha256"] = canonical_digest(result)
    return result


def verify_receipt(
    spec: Mapping[str, Any], evidence: Mapping[str, Any], receipt: Mapping[str, Any], legacy_path: Path | None = None
) -> bool:
    if not isinstance(receipt, dict) or not isinstance(receipt.get("receipt_sha256"), str):
        return False
    supplied = dict(receipt)
    supplied_digest = supplied.pop("receipt_sha256", None)
    if supplied_digest != canonical_digest(supplied):
        return False
    expected = make_receipt(spec, evidence, legacy_path)
    return canonical_bytes(expected) == canonical_bytes(receipt)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--spec", type=Path, default=Path(__file__).with_name("qualification_spec.json"))
    parser.add_argument("--legacy", type=Path, default=Path(__file__).with_name("cpca_qualify.py"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)

    spec = _load(args.spec)
    evidence = _load(args.evidence)
    receipt = make_receipt(spec, evidence, args.legacy)
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
