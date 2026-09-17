#!/usr/bin/env python3
"""Source-bound healthcare-prime readiness wrapper for CPCA HCCN Connect.

The authorizing path executes only the exact reviewed repository qualification
specification and legacy qualifier bytes. Raw predecessor results are accepted
only by a private semantic helper used by retained unit tests; they cannot mint
a receipt or pass verification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

SCHEMA = "cpca-partner-readiness/v2"
MAX_JSON_BYTES = 1_048_576
SHA256_RE = __import__("re").compile(r"^[0-9a-f]{64}$")
SOURCE_KEYS = {"source_id", "sha256"}
CANONICAL_SPEC_GIT_BLOB_SHA1 = "8693e697c81521c34b24afe90fb9e3266f1af9fb"
CANONICAL_LEGACY_GIT_BLOB_SHA1 = "fbbd5abeaabc66d894612236bc6321226d4f848d"
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


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def _load_json_bytes(raw: bytes, label: str) -> Dict[str, Any]:
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError(f"{label}: JSON exceeds {MAX_JSON_BYTES} bytes")
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_pairs_no_duplicates,
        parse_constant=_reject_constant,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{label}: top-level JSON must be an object")
    return value


def _load(path: Path) -> Dict[str, Any]:
    return _load_json_bytes(path.read_bytes(), str(path))


def canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _git_blob_sha1(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def _read_pinned_sibling(filename: str, expected_git_blob_sha1: str) -> tuple[bytes, Path]:
    path = Path(__file__).resolve().with_name(filename)
    raw = path.read_bytes()
    actual = _git_blob_sha1(raw)
    if actual != expected_git_blob_sha1:
        raise ValueError(
            f"{filename}: reviewed source blob mismatch: "
            f"expected {expected_git_blob_sha1}, got {actual}"
        )
    return raw, path


def _canonical_spec() -> tuple[Dict[str, Any], Dict[str, str]]:
    raw, _ = _read_pinned_sibling("qualification_spec.json", CANONICAL_SPEC_GIT_BLOB_SHA1)
    spec = _load_json_bytes(raw, "qualification_spec.json")
    return spec, {
        "git_blob_sha1": CANONICAL_SPEC_GIT_BLOB_SHA1,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _canonical_legacy_evaluator():
    raw, path = _read_pinned_sibling("cpca_qualify.py", CANONICAL_LEGACY_GIT_BLOB_SHA1)
    namespace: Dict[str, Any] = {
        "__name__": "cpca_qualify_reviewed_runtime",
        "__file__": str(path),
        "__package__": None,
    }
    exec(compile(raw, str(path), "exec"), namespace, namespace)
    evaluate = namespace.get("evaluate")
    if not callable(evaluate):
        raise ValueError("reviewed legacy qualifier does not expose evaluate")
    return evaluate, {
        "git_blob_sha1": CANONICAL_LEGACY_GIT_BLOB_SHA1,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


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
    if manifest.get("qualification_spec_sha256") != canonical_digest(spec):
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


def _validate_legacy_result(
    legacy_result: Mapping[str, Any],
    evidence: Mapping[str, Any],
    required_ids: Sequence[str],
) -> None:
    if legacy_result.get("schema") != "cpca-hccn-qualification-result/v1":
        raise ValueError("legacy result schema mismatch")
    state = legacy_result.get("state")
    if state not in {"TEAMING_READY", "HOLD", "NO_BID"}:
        raise ValueError(f"unexpected legacy state for partner path: {state!r}")
    reason = legacy_result.get("reason")
    if not isinstance(reason, str) or not reason:
        raise ValueError("legacy result reason must be nonempty")
    blockers = legacy_result.get("blockers")
    if not isinstance(blockers, list) or not all(isinstance(x, str) and x for x in blockers):
        raise ValueError("legacy blockers must be a list of nonempty strings")
    if state == "NO_BID":
        return
    if legacy_result.get("domain") != evidence.get("domain"):
        raise ValueError("legacy result domain mismatch")
    if legacy_result.get("service_type") != evidence.get("service_type"):
        raise ValueError("legacy result service_type mismatch")
    if legacy_result.get("bid_model") != "healthcare_prime_subcontract":
        raise ValueError("legacy result bid_model mismatch")
    gate_status = legacy_result.get("gate_status")
    if not isinstance(gate_status, dict):
        raise ValueError("legacy gate_status must be an object")
    for gate_id in required_ids:
        if gate_id not in gate_status:
            raise ValueError(f"legacy result missing required gate status: {gate_id}")


def _compile_partner_readiness(
    spec: Mapping[str, Any],
    evidence: Mapping[str, Any],
    legacy_result: Mapping[str, Any],
) -> Dict[str, Any]:
    """Private semantic projection. It is not a receipt-authorizing API."""
    if evidence.get("bid_model") != "healthcare_prime_subcontract":
        raise ValueError("partner readiness requires bid_model=healthcare_prime_subcontract")
    if not isinstance(legacy_result, dict):
        raise ValueError("legacy_result must be an object")

    required_ids = _required_gate_ids(spec, str(evidence.get("service_type")))
    _validate_legacy_result(legacy_result, evidence, required_ids)

    legacy_state = legacy_result["state"]
    legacy_reason = legacy_result["reason"]
    legacy_blockers = sorted(set(legacy_result["blockers"]))

    gate_status = legacy_result.get("gate_status", {})
    non_proven = sorted(gate_id for gate_id in required_ids if gate_status.get(gate_id) != "PROVEN")

    if legacy_state == "NO_BID":
        workshare_state = "NO_BID"
        application_state = "NO_BID"
        application_blockers: List[str] = []
        state = "NO_BID"
        reason = "legacy_deadline_or_hard_stop"
    else:
        prime = evidence.get("healthcare_prime")
        prime_name = prime.get("name") if isinstance(prime, dict) else None
        if not isinstance(prime_name, str) or not prime_name.strip():
            raise ValueError("healthcare_prime.name must be a nonempty string")
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

    return {
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


def _source_manifest_projection(evidence: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "source_packet": evidence.get("source_packet"),
        "gate_sources": evidence.get("gate_sources"),
        "client_references": evidence.get("client_references"),
        "comparable_engagements": evidence.get("comparable_engagements"),
        "healthcare_prime": evidence.get("healthcare_prime"),
        "tjlabs_support_gate_ids": evidence.get("tjlabs_support_gate_ids"),
        "partner_application_evidence": evidence.get("partner_application_evidence"),
    }


def _bound_compile(evidence: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be an object")
    spec, spec_meta = _canonical_spec()
    evaluate, legacy_meta = _canonical_legacy_evaluator()
    legacy_result = evaluate(dict(spec), dict(evidence))
    result = _compile_partner_readiness(spec, evidence, legacy_result)

    prime = evidence.get("healthcare_prime")
    prime_name = prime.get("name") if isinstance(prime, dict) else None
    normalized_prime = prime_name.strip() if isinstance(prime_name, str) and prime_name.strip() else None
    result["bindings"] = {
        "qualification_spec_git_blob_sha1": spec_meta["git_blob_sha1"],
        "qualification_spec_sha256": spec_meta["sha256"],
        "evidence_sha256": canonical_digest(evidence),
        "source_manifest_sha256": canonical_digest(_source_manifest_projection(evidence)),
        "prime_legal_name": normalized_prime,
        "legacy_implementation_git_blob_sha1": legacy_meta["git_blob_sha1"],
        "legacy_implementation_sha256": legacy_meta["sha256"],
        "legacy_result_sha256": canonical_digest(legacy_result),
    }
    return result


def compile_from_evidence(evidence: Mapping[str, Any]) -> Dict[str, Any]:
    """Compile from caller evidence using only pinned repository spec/legacy bytes."""
    return _bound_compile(evidence)


def make_receipt(evidence: Mapping[str, Any]) -> Dict[str, Any]:
    result = _bound_compile(evidence)
    result["receipt_sha256"] = canonical_digest(result)
    return result


def verify_receipt(evidence: Mapping[str, Any], receipt: Mapping[str, Any]) -> bool:
    try:
        if not isinstance(receipt, dict) or not isinstance(receipt.get("receipt_sha256"), str):
            return False
        supplied = dict(receipt)
        supplied_digest = supplied.pop("receipt_sha256", None)
        if supplied_digest != canonical_digest(supplied):
            return False
        expected = make_receipt(evidence)
        return canonical_bytes(expected) == canonical_bytes(receipt)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        return False


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)

    evidence = _load(args.evidence)
    receipt = make_receipt(evidence)
    rendered = json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
