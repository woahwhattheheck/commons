"""Fail-closed authority facade for the opportunity qualification core.

The core remains the deterministic packet compiler. This facade adds:
- buyer-official negative-authority fences for deadline / teaming claims; and
- a separate package-completeness trust root before READY or gate-derived
  NO_BID can be asserted.
"""
from __future__ import annotations

import argparse
import json
from typing import Any

import engine_core as _core
from engine_core import *  # noqa: F401,F403 - preserve the public v1 surface

COMPLETENESS_CONTRACT = "tjlabs.opportunity-qualification-completeness/v1"
_COMPLETENESS_KEYS = {
    "contract", "opportunity_id", "controlling_source_id",
    "controlling_source_sha256", "extracted_at", "extraction_evidence_sha256",
    "complete", "gate_count", "gate_set_sha256", "gates",
}
_COMPLETENESS_GATE_KEYS = {
    "gate_id", "category", "mandatory", "route", "cure", "buyer_source_id",
    "buyer_source_sha256", "description_sha256",
}

_original_compile = _core.compile_qualification


def _evaluate_team(requirements, sources, teaming, teaming_source_id):
    if teaming == "UNKNOWN" or not _core._buyer_official(teaming_source_id, sources):
        return False, True, ["TEAMING_NOT_OFFICIALLY_EVIDENCED"]
    if teaming == "PROHIBITED":
        return False, False, ["TEAMING_PROHIBITED"]
    return _core._evaluate_team_official_allowed(requirements, sources)


def _evaluate_team_official_allowed(requirements, sources):
    ready = True
    possible = True
    reasons = []
    for req in requirements:
        if not req["mandatory"]:
            continue
        prefix = req["gate_id"]
        if not _core._buyer_official(req["buyer_source_id"], sources):
            ready = False
            reasons.append(f"{prefix}:MANDATORY_SOURCE_NOT_OFFICIAL")
            continue

        route = req["route"]
        prime_state = req["prime_state"]
        team_state = req["team_state"]
        cure = req["cure"]

        if route == "PRIME":
            if prime_state == "PASS":
                continue
            if cure == "PARTNER" and team_state == "PASS":
                continue
            ready = False
            if prime_state == "FAIL" and cure == "NONE":
                possible = False
                reasons.append(f"{prefix}:NONCURABLE_PRIME_FAILURE")
            elif cure == "PARTNER" and team_state == "FAIL":
                possible = False
                reasons.append(f"{prefix}:PARTNER_CURE_FAILED")
            else:
                reasons.append(f"{prefix}:TEAM_ROUTE_MISSING_CURE")
            continue

        if route == "TEAM":
            if team_state == "PASS":
                continue
            ready = False
            if team_state == "FAIL":
                possible = False
                reasons.append(f"{prefix}:TEAM_FAILED")
            else:
                reasons.append(f"{prefix}:TEAM_MISSING")
            continue

        side_fail = False
        if prime_state != "PASS":
            ready = False
            side_fail = side_fail or prime_state == "FAIL"
            reasons.append(f"{prefix}:PRIME_{'FAILED' if prime_state == 'FAIL' else 'MISSING'}")
        if team_state != "PASS":
            ready = False
            side_fail = side_fail or team_state == "FAIL"
            reasons.append(f"{prefix}:TEAM_{'FAILED' if team_state == 'FAIL' else 'MISSING'}")
        if side_fail:
            possible = False
    return ready, possible, sorted(set(reasons))


_core._evaluate_team_official_allowed = _evaluate_team_official_allowed
_core._evaluate_team = _evaluate_team


def _normalize_completeness_gate(raw: Any, index: int) -> dict[str, Any]:
    path = f"trusted_completeness.gates[{index}]"
    gate = _core._expect_object(raw, path, _COMPLETENESS_GATE_KEYS, _COMPLETENESS_GATE_KEYS)
    return {
        "gate_id": _core._expect_id(gate["gate_id"], f"{path}.gate_id"),
        "category": _core._expect_enum(gate["category"], f"{path}.category", _core._CATEGORIES),
        "mandatory": _core._expect_bool(gate["mandatory"], f"{path}.mandatory"),
        "route": _core._expect_enum(gate["route"], f"{path}.route", _core._ROUTES),
        "cure": _core._expect_enum(gate["cure"], f"{path}.cure", _core._CURES),
        "buyer_source_id": _core._expect_id(gate["buyer_source_id"], f"{path}.buyer_source_id"),
        "buyer_source_sha256": _core._expect_sha(gate["buyer_source_sha256"], f"{path}.buyer_source_sha256"),
        "description_sha256": _core._expect_sha(gate["description_sha256"], f"{path}.description_sha256"),
    }


def _normalize_trusted_completeness(raw: Any, *, trusted_as_of: str) -> dict[str, Any]:
    manifest = _core._expect_object(
        raw, "trusted_completeness", _COMPLETENESS_KEYS, _COMPLETENESS_KEYS
    )
    if _core._expect_text(manifest["contract"], "trusted_completeness.contract", max_len=96) != COMPLETENESS_CONTRACT:
        raise QualificationError("trusted_completeness.contract: unsupported contract")

    extracted_at = _core._parse_utc(manifest["extracted_at"], "trusted_completeness.extracted_at")
    if extracted_at > _core._parse_utc(trusted_as_of, "trusted_as_of"):
        raise QualificationError("trusted_completeness.extracted_at: future extraction evidence")

    complete = _core._expect_bool(manifest["complete"], "trusted_completeness.complete")
    gate_count = manifest["gate_count"]
    if type(gate_count) is not int or gate_count < 0:
        raise QualificationError("trusted_completeness.gate_count: expected non-negative integer")

    raw_gates = _core._expect_list(manifest["gates"], "trusted_completeness.gates")
    normalized = [_normalize_completeness_gate(gate, i) for i, gate in enumerate(raw_gates)]
    by_id: dict[str, dict[str, Any]] = {}
    for gate in normalized:
        if gate["gate_id"] in by_id:
            raise QualificationError(f"trusted_completeness.gates: duplicate gate_id {gate['gate_id']}")
        by_id[gate["gate_id"]] = gate
    gates = [by_id[key] for key in sorted(by_id)]
    if gate_count != len(gates):
        raise QualificationError("trusted_completeness.gate_count: does not match gates")

    gate_set_sha256 = _core._expect_sha(
        manifest["gate_set_sha256"], "trusted_completeness.gate_set_sha256"
    )
    if gate_set_sha256 != _core.digest(gates):
        raise QualificationError("trusted_completeness.gate_set_sha256: does not match gates")

    return {
        "contract": COMPLETENESS_CONTRACT,
        "opportunity_id": _core._expect_id(manifest["opportunity_id"], "trusted_completeness.opportunity_id"),
        "controlling_source_id": _core._expect_id(manifest["controlling_source_id"], "trusted_completeness.controlling_source_id"),
        "controlling_source_sha256": _core._expect_sha(manifest["controlling_source_sha256"], "trusted_completeness.controlling_source_sha256"),
        "extracted_at": manifest["extracted_at"],
        "extraction_evidence_sha256": _core._expect_sha(manifest["extraction_evidence_sha256"], "trusted_completeness.extraction_evidence_sha256"),
        "complete": complete,
        "gate_count": gate_count,
        "gate_set_sha256": gate_set_sha256,
        "gates": gates,
    }


def _observed_gate_descriptors(packet: dict[str, Any]) -> list[dict[str, Any]]:
    sources = {source["source_id"]: source for source in packet["sources"]}
    gates = []
    for requirement in packet["requirements"]:
        source = sources[requirement["buyer_source_id"]]
        gates.append({
            "gate_id": requirement["gate_id"],
            "category": requirement["category"],
            "mandatory": requirement["mandatory"],
            "route": requirement["route"],
            "cure": requirement["cure"],
            "buyer_source_id": requirement["buyer_source_id"],
            "buyer_source_sha256": source["sha256"],
            "description_sha256": _core.digest(requirement["description"]),
        })
    return sorted(gates, key=lambda gate: gate["gate_id"])


def _assess_completeness(
    packet: dict[str, Any],
    *,
    trusted_as_of: str,
    trusted_completeness: Any,
    trusted_completeness_sha256: Any,
) -> dict[str, Any]:
    observed_gates = _observed_gate_descriptors(packet)
    observed_gate_digest = _core.digest(observed_gates)

    if trusted_completeness is None:
        return {
            "provided": False,
            "trust_root_provided": trusted_completeness_sha256 is not None,
            "verified": False,
            "trusted_manifest_sha256": None,
            "manifest_digest": None,
            "extraction_evidence_sha256": None,
            "expected_gate_count": None,
            "observed_gate_count": len(observed_gates),
            "expected_gate_set_sha256": None,
            "observed_gate_set_sha256": observed_gate_digest,
            "reasons": ["PACKAGE_COMPLETENESS_NOT_PROVIDED"],
        }

    manifest = _normalize_trusted_completeness(trusted_completeness, trusted_as_of=trusted_as_of)
    manifest_digest = _core.digest(manifest)
    trusted_manifest_digest = None
    reasons: list[str] = []

    if trusted_completeness_sha256 is None:
        reasons.append("COMPLETENESS_TRUST_ROOT_NOT_PROVIDED")
    else:
        trusted_manifest_digest = _core._expect_sha(
            trusted_completeness_sha256, "trusted_completeness_sha256"
        )
        if trusted_manifest_digest != manifest_digest:
            reasons.append("COMPLETENESS_TRUST_ROOT_MISMATCH")

    opportunity = packet["opportunity"]
    sources = {source["source_id"]: source for source in packet["sources"]}
    if manifest["opportunity_id"] != opportunity["opportunity_id"]:
        reasons.append("COMPLETENESS_OPPORTUNITY_MISMATCH")

    controlling_id = opportunity["controlling_source_id"]
    controlling = sources.get(controlling_id) if controlling_id is not None else None
    if (
        manifest["controlling_source_id"] != controlling_id
        or controlling is None
        or manifest["controlling_source_sha256"] != controlling["sha256"]
    ):
        reasons.append("COMPLETENESS_CONTROLLING_SOURCE_MISMATCH")

    if not manifest["complete"]:
        reasons.append("PACKAGE_EXTRACTION_INCOMPLETE")
    if manifest["gate_count"] != len(observed_gates) or manifest["gate_set_sha256"] != observed_gate_digest:
        reasons.append("PACKAGE_GATE_SET_MISMATCH")

    return {
        "provided": True,
        "trust_root_provided": trusted_manifest_digest is not None,
        "verified": not reasons,
        "trusted_manifest_sha256": trusted_manifest_digest,
        "manifest_digest": manifest_digest,
        "extraction_evidence_sha256": manifest["extraction_evidence_sha256"],
        "expected_gate_count": manifest["gate_count"],
        "observed_gate_count": len(observed_gates),
        "expected_gate_set_sha256": manifest["gate_set_sha256"],
        "observed_gate_set_sha256": observed_gate_digest,
        "reasons": sorted(set(reasons)),
    }


def compile_qualification(
    packet,
    *,
    trusted_as_of,
    trusted_completeness=None,
    trusted_completeness_sha256=None,
):
    receipt = _original_compile(packet, trusted_as_of=trusted_as_of)
    package = receipt["package"]

    # A timestamp has negative commercial authority only when the controlling
    # package and deadline source are buyer-official.
    if package["proposal_expired"] and (
        not package["controlling_source_official"]
        or not package["proposal_deadline_source_official"]
    ):
        reasons = []
        if not package["controlling_source_official"]:
            reasons.append("CONTROLLING_PACKAGE_NOT_OFFICIALLY_EVIDENCED")
        if not package["proposal_deadline_source_official"]:
            reasons.append("PROPOSAL_DEADLINE_NOT_OFFICIALLY_EVIDENCED")
        if not package["question_deadline_source_official"]:
            reasons.append("QUESTION_DEADLINE_SOURCE_NOT_OFFICIAL")
        receipt["disposition"] = HOLD
        receipt["reasons"] = sorted(reasons)

    completeness = _assess_completeness(
        packet,
        trusted_as_of=trusted_as_of,
        trusted_completeness=trusted_completeness,
        trusted_completeness_sha256=trusted_completeness_sha256,
    )
    receipt["completeness"] = completeness
    receipt["package"]["completeness_verified"] = completeness["verified"]

    for route_name in ("prime", "team"):
        requirements_ready = receipt[route_name]["ready"]
        receipt[route_name]["requirements_ready"] = requirements_ready
        receipt[route_name]["ready"] = bool(requirements_ready and completeness["verified"])

    gate_derived_no_bid = (
        receipt["disposition"] == NO_BID
        and receipt["reasons"] != ["PROPOSAL_DEADLINE_EXPIRED"]
    )
    if not completeness["verified"] and (
        receipt["disposition"] in {PRIME_READY, TEAMING_READY} or gate_derived_no_bid
    ):
        receipt["disposition"] = HOLD
        receipt["reasons"] = sorted(set(receipt["reasons"] + completeness["reasons"]))

    receipt.pop("receipt_digest", None)
    receipt["receipt_digest"] = _core.digest(receipt)
    return receipt


def verify_receipt_against_inputs(
    receipt: Any,
    packet: dict[str, Any],
    *,
    trusted_as_of: str,
    trusted_completeness: Any,
    trusted_completeness_sha256: Any,
) -> bool:
    if not _core.verify_receipt(receipt):
        return False
    try:
        expected = compile_qualification(
            packet,
            trusted_as_of=trusted_as_of,
            trusted_completeness=trusted_completeness,
            trusted_completeness_sha256=trusted_completeness_sha256,
        )
        return _core.canonical_bytes(expected) == _core.canonical_bytes(receipt)
    except QualificationError:
        return False


# Core callers that omit the independently retained trust root fail closed.
_core.compile_qualification = compile_qualification


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Compile opportunity qualification receipts.")
    parser.add_argument("packet", help="qualification packet JSON")
    parser.add_argument("--completeness", required=True, help="independent completeness manifest JSON")
    parser.add_argument(
        "--completeness-sha256",
        required=True,
        help="independently retained canonical SHA-256 of the completeness manifest",
    )
    parser.add_argument("--as-of", required=True, help="trusted UTC time, YYYY-MM-DDTHH:MM:SSZ")
    parser.add_argument("--markdown", help="optional Markdown output path")
    args = parser.parse_args()

    with open(args.packet, "r", encoding="utf-8") as handle:
        packet = _core.loads_strict(handle.read())
    with open(args.completeness, "r", encoding="utf-8") as handle:
        completeness = _core.loads_strict(handle.read())
    receipt = compile_qualification(
        packet,
        trusted_as_of=args.as_of,
        trusted_completeness=completeness,
        trusted_completeness_sha256=args.completeness_sha256,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False))
    if args.markdown:
        with open(args.markdown, "x", encoding="utf-8", newline="\n") as handle:
            handle.write(_core.render_markdown(receipt) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
