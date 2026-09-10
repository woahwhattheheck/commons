"""Already-spent disabled-arm trace identity validation."""
from __future__ import annotations

from typing import Any

from gate_common import (
    GATE_NAME, SCHEMA_VERSION, GateError, _DIGEST, _require_exact_keys,
    _require_nonempty_string, _require_object, _require_verdict,
    _validate_finite_json, canonical_bytes, sha256_bytes,
)

def _require_digest(value: Any, label: str) -> str:
    digest = _require_nonempty_string(value, label)
    if not _DIGEST.fullmatch(digest):
        raise GateError(f"{label} must be sha256: followed by 64 lowercase hex characters")
    return digest


def _validate_arm(raw: Any, label: str) -> dict[str, Any]:
    arm = _require_object(raw, label)
    required = {"action_digest", "transition_digest", "banks"}
    missing = sorted(required - set(arm))
    if missing:
        raise GateError(f"{label} missing keys: {', '.join(missing)}")
    _validate_finite_json(arm, label)
    _require_digest(arm["action_digest"], f"{label}.action_digest")
    _require_digest(arm["transition_digest"], f"{label}.transition_digest")
    banks = arm["banks"]
    if (
        not isinstance(banks, list)
        or len(banks) != 2
        or any(not isinstance(item, int) or isinstance(item, bool) for item in banks)
    ):
        raise GateError(f"{label}.banks must be a two-integer list")
    if "reward" in arm and (
        not isinstance(arm["reward"], (int, float)) or isinstance(arm["reward"], bool)
    ):
        raise GateError(f"{label}.reward must be a finite number when present")
    return arm


def _diff_json(left: Any, right: Any, path: str = "$", limit: int = 64) -> list[str]:
    differences: list[str] = []

    def visit(a: Any, b: Any, current: str) -> None:
        if len(differences) >= limit:
            return
        if type(a) is not type(b):
            differences.append(current)
            return
        if isinstance(a, dict):
            keys = sorted(set(a) | set(b))
            for key in keys:
                child = f"{current}.{key}"
                if key not in a or key not in b:
                    differences.append(child)
                else:
                    visit(a[key], b[key], child)
            return
        if isinstance(a, list):
            if len(a) != len(b):
                differences.append(f"{current}.length")
            for index, (item_a, item_b) in enumerate(zip(a, b)):
                visit(item_a, item_b, f"{current}[{index}]")
            return
        if a != b or canonical_bytes(a) != canonical_bytes(b):
            differences.append(current)

    visit(left, right, path)
    return differences


def validate_trace_evidence(raw: Any) -> dict[str, Any]:
    evidence = _require_object(raw, "trace evidence")
    _require_exact_keys(
        evidence,
        required={
            "schema_version",
            "claim_id",
            "expected_verdict",
            "expected_case_ids",
            "cases",
        },
        optional=set(),
        label="trace evidence",
    )
    if evidence["schema_version"] != SCHEMA_VERSION:
        raise GateError(f"trace evidence schema_version must be {SCHEMA_VERSION}")
    claim_id = _require_nonempty_string(evidence["claim_id"], "claim_id")
    expected = _require_verdict(evidence["expected_verdict"], "expected_verdict")
    expected_ids = evidence["expected_case_ids"]
    if not isinstance(expected_ids, list) or not expected_ids:
        raise GateError("expected_case_ids must be a non-empty list")
    normalized_expected: list[str] = []
    for index, case_id in enumerate(expected_ids):
        normalized_expected.append(
            _require_nonempty_string(case_id, f"expected_case_ids[{index}]")
        )
    if len(set(normalized_expected)) != len(normalized_expected):
        raise GateError("expected_case_ids contains duplicates")

    cases = evidence["cases"]
    if not isinstance(cases, list):
        raise GateError("cases must be a list")
    normalized_cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw_case in enumerate(cases):
        case = _require_object(raw_case, f"cases[{index}]")
        _require_exact_keys(
            case,
            required={"case_id", "baseline", "disabled"},
            optional=set(),
            label=f"cases[{index}]",
        )
        case_id = _require_nonempty_string(case["case_id"], f"cases[{index}].case_id")
        if case_id in seen:
            raise GateError(f"duplicate case_id: {case_id}")
        seen.add(case_id)
        baseline = _validate_arm(case["baseline"], f"cases[{index}].baseline")
        disabled = _validate_arm(case["disabled"], f"cases[{index}].disabled")
        normalized_cases.append(
            {"case_id": case_id, "baseline": baseline, "disabled": disabled}
        )

    expected_set = set(normalized_expected)
    observed_set = {item["case_id"] for item in normalized_cases}
    missing = sorted(expected_set - observed_set)
    extra = sorted(observed_set - expected_set)
    if missing or extra:
        pieces = []
        if missing:
            pieces.append(f"missing cases: {', '.join(missing)}")
        if extra:
            pieces.append(f"unexpected cases: {', '.join(extra)}")
        raise GateError("; ".join(pieces))

    return {
        "schema_version": SCHEMA_VERSION,
        "claim_id": claim_id,
        "expected_verdict": expected,
        "expected_case_ids": sorted(normalized_expected),
        "cases": sorted(normalized_cases, key=lambda item: item["case_id"]),
    }


def audit_trace(raw_evidence: Any) -> dict[str, Any]:
    evidence = validate_trace_evidence(raw_evidence)
    findings: list[dict[str, Any]] = []
    case_receipts: list[dict[str, Any]] = []
    for case in evidence["cases"]:
        baseline_bytes = canonical_bytes(case["baseline"])
        disabled_bytes = canonical_bytes(case["disabled"])
        differences = _diff_json(case["baseline"], case["disabled"])
        if differences:
            findings.append(
                {
                    "code": "DISABLED_ARM_DIVERGENCE",
                    "case_id": case["case_id"],
                    "paths": differences,
                    "detail": "baseline and disabled-arm evidence are not byte-canonical identical",
                }
            )
        case_receipts.append(
            {
                "case_id": case["case_id"],
                "baseline_sha256": sha256_bytes(baseline_bytes),
                "disabled_sha256": sha256_bytes(disabled_bytes),
                "identical": not differences,
            }
        )
    observed = "PASS" if not findings else "BLOCK"
    expected = evidence["expected_verdict"]
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "gate": GATE_NAME,
        "mode": "trace",
        "claim_id": evidence["claim_id"],
        "expected_verdict": expected,
        "observed_verdict": observed,
        "expectation_met": observed == expected,
        "evidence_sha256": sha256_bytes(canonical_bytes(evidence)),
        "case_count": len(evidence["cases"]),
        "cases": case_receipts,
        "findings": findings,
    }
    receipt["receipt_sha256"] = sha256_bytes(canonical_bytes(receipt))
    return receipt
