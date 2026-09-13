#!/usr/bin/env python3
"""Deterministic evidence compiler for the UIOWA RFQ 18649 TJLabs workshare.

No network access. No buyer/prime writes. This module only compiles bounded
evidence into a review packet and receipt.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
SOLICITATION_ID = "18649"
BUYER = "University of Iowa"
SUBCONTRACTOR = "TJLabs"
BASE_FEE_USD = 24_000
OPTIONAL_READOUT_USD = 4_000
PAYMENT_SCHEDULE = [
    {"milestone": "written authorization / kickoff", "percent": 40, "amount_usd": 9_600},
    {"milestone": "draft technical work package", "percent": 40, "amount_usd": 9_600},
    {"milestone": "accepted final technical work package", "percent": 20, "amount_usd": 4_800},
]
MAX_EVIDENCE_AGE_DAYS = 120

GROUPS = ("ESS", "RIS", "IAM")
DIMENSIONS = ("software", "security", "deployment", "ai_readiness")
EVIDENCE_KINDS = ("artifact", "demo", "interview", "metric")
EXPECTED_ROOT_KEYS = {
    "schema_version",
    "evaluation_date",
    "engagement",
    "observations",
}
EXPECTED_ENGAGEMENT_KEYS = {
    "solicitation_id",
    "buyer",
    "prime_candidate",
    "subcontractor",
    "base_fee_usd",
    "optional_readout_usd",
}
EXPECTED_OBSERVATION_KEYS = {
    "group",
    "dimension",
    "evidence_id",
    "evidence_kind",
    "observed_date",
    "claim",
    "maturity",
    "confidence_bp",
    "scope_commitment",
    "evidence_sha256",
}
AUTHORITY = {
    "contact_buyer": False,
    "submit_university_response": False,
    "sign_teaming_or_prime_contract": False,
    "accept_contract_or_award": False,
    "commit_travel_or_spend": False,
    "claim_payment_or_cash": False,
    "recognize_revenue": False,
}
DELIVERABLES = [
    {
        "id": "D1",
        "name": "Evidence map and interview/artifact register",
        "acceptance": "Every observation is source-committed to exactly one AIS group and assessment dimension.",
    },
    {
        "id": "D2",
        "name": "Technical maturity and gap matrix",
        "acceptance": "All 12 ESS/RIS/IAM × software/security/deployment/AI-readiness cells are classified; no evidence-free score exists.",
    },
    {
        "id": "D3",
        "name": "Draft finding and phased-roadmap production support",
        "acceptance": "Only clean evidence produces a maturity finding; holds remain explicit for the prime's professional judgment.",
    },
    {
        "id": "D4",
        "name": "Reproducibility and consistency receipt",
        "acceptance": "Canonical report and receipt are stable under input reordering; tampering fails verification.",
    },
]
PRIME_RETAINS = [
    "University relationship and all bidder communications",
    "proposal submission and bidder-of-record responsibility",
    "three comparable client references and reference permissions",
    "insurance and contracting qualifications",
    "final professional judgments, benchmarking conclusions, and recommendations",
    "onsite commitments, travel authorization, staffing promises, and final readout",
]


class ContractError(ValueError):
    """Input or report violates the bounded workshare contract."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ContractError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def loads_strict(text: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ContractError(f"non-finite JSON token: {token}")
            ),
        )
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid JSON: {exc.msg}") from exc


def _require_exact_keys(value: dict[str, Any], expected: set[str], where: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ContractError(f"{where} keys mismatch: missing={missing} unknown={unknown}")


def _require_str(value: Any, where: str, *, nonempty: bool = True) -> str:
    if type(value) is not str:
        raise ContractError(f"{where} must be string")
    if nonempty and not value.strip():
        raise ContractError(f"{where} must be non-empty")
    return value


def _require_int(value: Any, where: str, *, low: int | None = None, high: int | None = None) -> int:
    if type(value) is not int:
        raise ContractError(f"{where} must be integer")
    if low is not None and value < low:
        raise ContractError(f"{where} must be >= {low}")
    if high is not None and value > high:
        raise ContractError(f"{where} must be <= {high}")
    return value


def _parse_date(value: Any, where: str) -> _dt.date:
    text = _require_str(value, where)
    if not __import__("re").fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ContractError(f"{where} must be YYYY-MM-DD")
    try:
        return _dt.date.fromisoformat(text)
    except ValueError as exc:
        raise ContractError(f"{where} is not a real calendar date") from exc


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def expected_scope_commitment(group: str, dimension: str, evidence_id: str) -> str:
    return "sha256:" + sha256_text(f"{group}|{dimension}|{evidence_id}")


def expected_evidence_sha256(claim: str) -> str:
    return "sha256:" + sha256_text(claim)


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def _validate_engagement(raw: Any) -> dict[str, Any]:
    if type(raw) is not dict:
        raise ContractError("engagement must be object")
    _require_exact_keys(raw, EXPECTED_ENGAGEMENT_KEYS, "engagement")
    if _require_str(raw["solicitation_id"], "engagement.solicitation_id") != SOLICITATION_ID:
        raise ContractError("engagement.solicitation_id drift")
    if _require_str(raw["buyer"], "engagement.buyer") != BUYER:
        raise ContractError("engagement.buyer drift")
    prime = _require_str(raw["prime_candidate"], "engagement.prime_candidate")
    if _require_str(raw["subcontractor"], "engagement.subcontractor") != SUBCONTRACTOR:
        raise ContractError("engagement.subcontractor drift")
    if _require_int(raw["base_fee_usd"], "engagement.base_fee_usd", low=0) != BASE_FEE_USD:
        raise ContractError("base fee drift")
    if _require_int(raw["optional_readout_usd"], "engagement.optional_readout_usd", low=0) != OPTIONAL_READOUT_USD:
        raise ContractError("optional readout fee drift")
    return {
        "solicitation_id": SOLICITATION_ID,
        "buyer": BUYER,
        "prime_candidate": prime,
        "subcontractor": SUBCONTRACTOR,
        "base_fee_usd": BASE_FEE_USD,
        "optional_readout_usd": OPTIONAL_READOUT_USD,
    }


def _validate_observation(raw: Any, index: int, eval_date: _dt.date) -> dict[str, Any]:
    where = f"observations[{index}]"
    if type(raw) is not dict:
        raise ContractError(f"{where} must be object")
    _require_exact_keys(raw, EXPECTED_OBSERVATION_KEYS, where)
    group = _require_str(raw["group"], f"{where}.group")
    dimension = _require_str(raw["dimension"], f"{where}.dimension")
    evidence_id = _require_str(raw["evidence_id"], f"{where}.evidence_id")
    kind = _require_str(raw["evidence_kind"], f"{where}.evidence_kind")
    observed_date = _parse_date(raw["observed_date"], f"{where}.observed_date")
    claim = _require_str(raw["claim"], f"{where}.claim")
    maturity = _require_int(raw["maturity"], f"{where}.maturity", low=0, high=4)
    confidence_bp = _require_int(raw["confidence_bp"], f"{where}.confidence_bp", low=0, high=10_000)
    scope_commitment = _require_str(raw["scope_commitment"], f"{where}.scope_commitment")
    evidence_sha256 = _require_str(raw["evidence_sha256"], f"{where}.evidence_sha256")

    if group not in GROUPS:
        raise ContractError(f"{where}.group unknown: {group}")
    if dimension not in DIMENSIONS:
        raise ContractError(f"{where}.dimension unknown: {dimension}")
    if kind not in EVIDENCE_KINDS:
        raise ContractError(f"{where}.evidence_kind unknown: {kind}")
    if observed_date > eval_date:
        raise ContractError(f"{where}.observed_date is in the future")
    if scope_commitment != expected_scope_commitment(group, dimension, evidence_id):
        raise ContractError(f"{where}.scope_commitment mismatch")
    if evidence_sha256 != expected_evidence_sha256(claim):
        raise ContractError(f"{where}.evidence_sha256 mismatch")

    return {
        "group": group,
        "dimension": dimension,
        "evidence_id": evidence_id,
        "evidence_kind": kind,
        "observed_date": observed_date.isoformat(),
        "claim": claim,
        "maturity": maturity,
        "confidence_bp": confidence_bp,
        "scope_commitment": scope_commitment,
        "evidence_sha256": evidence_sha256,
    }


def _cell(group: str, dimension: str, observations: list[dict[str, Any]], eval_date: _dt.date) -> dict[str, Any]:
    rows = [o for o in observations if o["group"] == group and o["dimension"] == dimension]
    rows.sort(key=lambda o: o["evidence_id"])
    base = {
        "group": group,
        "dimension": dimension,
        "evidence_ids": [o["evidence_id"] for o in rows],
        "evidence_commitments": [o["evidence_sha256"] for o in rows],
    }
    if not rows:
        return {
            **base,
            "status": "HOLD_MISSING_EVIDENCE",
            "maturity": None,
            "confidence_bp": None,
            "reason_codes": ["NO_BOUND_EVIDENCE"],
        }

    ages = [(eval_date - _dt.date.fromisoformat(o["observed_date"])).days for o in rows]
    stale_ids = [o["evidence_id"] for o, age in zip(rows, ages) if age > MAX_EVIDENCE_AGE_DAYS]
    maturity_values = sorted({o["maturity"] for o in rows})

    if len(maturity_values) > 1:
        return {
            **base,
            "status": "HOLD_CONFLICT",
            "maturity": None,
            "confidence_bp": None,
            "reason_codes": ["MATURITY_EVIDENCE_CONFLICT"],
        }
    if stale_ids:
        return {
            **base,
            "status": "HOLD_STALE_EVIDENCE",
            "maturity": None,
            "confidence_bp": None,
            "reason_codes": ["STALE_EVIDENCE:" + ",".join(stale_ids)],
        }

    confidence_bp = min(o["confidence_bp"] for o in rows)
    return {
        **base,
        "status": "READY",
        "maturity": maturity_values[0],
        "confidence_bp": confidence_bp,
        "reason_codes": [],
    }


def compile_packet(packet: Any) -> dict[str, Any]:
    if type(packet) is not dict:
        raise ContractError("root must be object")
    _require_exact_keys(packet, EXPECTED_ROOT_KEYS, "root")
    if _require_int(packet["schema_version"], "schema_version") != SCHEMA_VERSION:
        raise ContractError("schema_version drift")
    eval_date = _parse_date(packet["evaluation_date"], "evaluation_date")
    engagement = _validate_engagement(packet["engagement"])

    raw_observations = packet["observations"]
    if type(raw_observations) is not list:
        raise ContractError("observations must be array")
    observations = [_validate_observation(item, i, eval_date) for i, item in enumerate(raw_observations)]
    ids = [o["evidence_id"] for o in observations]
    if len(ids) != len(set(ids)):
        raise ContractError("duplicate evidence_id")
    observations.sort(key=lambda o: (o["group"], o["dimension"], o["evidence_id"]))

    matrix = [
        _cell(group, dimension, observations, eval_date)
        for group in GROUPS
        for dimension in DIMENSIONS
    ]
    counts: dict[str, int] = {}
    for row in matrix:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    aggregate_state = (
        "READY_FOR_PRIME_TEAMING_REVIEW"
        if counts.get("READY", 0) == len(GROUPS) * len(DIMENSIONS)
        else "HOLD_FOR_PRIME_EVIDENCE_RECONCILIATION"
    )
    report_without_receipt = {
        "schema_version": SCHEMA_VERSION,
        "operation": "UIOWA-RFQ18649-PAID-TECHNICAL-WORKSHARE-ZSOL13-20260913",
        "evaluation_date": eval_date.isoformat(),
        "engagement": engagement,
        "commercial_terms": {
            "base_fee_usd": BASE_FEE_USD,
            "optional_readout_support_usd": OPTIONAL_READOUT_USD,
            "total_if_option_authorized_usd": BASE_FEE_USD + OPTIONAL_READOUT_USD,
            "payment_schedule": PAYMENT_SCHEDULE,
            "travel": "excluded; any travel requires separate written authorization",
            "status": "PROPOSED_NOT_ACCEPTED",
        },
        "deliverables": DELIVERABLES,
        "prime_retains": PRIME_RETAINS,
        "authority": AUTHORITY,
        "assessment_matrix": matrix,
        "status_counts": dict(sorted(counts.items())),
        "aggregate_state": aggregate_state,
        "observations": observations,
    }
    receipt = hashlib.sha256(canonical_json_bytes(report_without_receipt)).hexdigest()
    return {**report_without_receipt, "receipt_sha256": receipt}


def verify_report(report: Any) -> bool:
    if type(report) is not dict:
        raise ContractError("report must be object")
    if "receipt_sha256" not in report:
        raise ContractError("report missing receipt_sha256")
    receipt = report["receipt_sha256"]
    _require_str(receipt, "receipt_sha256")
    if not __import__("re").fullmatch(r"[0-9a-f]{64}", receipt):
        raise ContractError("receipt_sha256 must be 64 lowercase hex")
    unsigned = dict(report)
    del unsigned["receipt_sha256"]
    expected = hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest()
    if not hmac.compare_digest(receipt, expected):
        raise ContractError("receipt mismatch")
    return True


def render_markdown(report: dict[str, Any]) -> str:
    verify_report(report)
    lines = [
        "# University of Iowa RFQ 18649 — TJLabs technical workshare",
        "",
        f"- State: `{report['aggregate_state']}`",
        f"- Base fixed fee: **${report['commercial_terms']['base_fee_usd']:,}**",
        f"- Optional final-readout support: **${report['commercial_terms']['optional_readout_support_usd']:,}**",
        f"- Receipt: `{report['receipt_sha256']}`",
        "",
        "## Assessment matrix",
        "",
        "| Group | Dimension | State | Maturity | Confidence (bp) |",
        "|---|---|---|---:|---:|",
    ]
    for row in report["assessment_matrix"]:
        maturity = "—" if row["maturity"] is None else str(row["maturity"])
        confidence = "—" if row["confidence_bp"] is None else str(row["confidence_bp"])
        lines.append(
            f"| {row['group']} | {row['dimension']} | {row['status']} | {maturity} | {confidence} |"
        )
    lines.extend(
        [
            "",
            "## Authority boundary",
            "",
            "TJLabs prepares bounded technical evidence and synthesis support. The prime retains University communication, proposal submission, references, insurance, contracting, final professional judgment, staffing/travel commitments, and final recommendations.",
            "",
            "No award, buyer acceptance, payment, cash, or recognized revenue is claimed by this packet.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_exclusive(path: Path, data: bytes) -> None:
    parent = path.parent
    if not parent.exists() or not parent.is_dir():
        raise ContractError(f"output parent missing or not directory: {parent}")
    if path.exists() or path.is_symlink():
        raise ContractError(f"refusing existing output path: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
    except Exception:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def _load_file(path: Path) -> Any:
    if not path.is_file() or path.is_symlink():
        raise ContractError(f"input must be ordinary file: {path}")
    return loads_strict(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_compile = sub.add_parser("compile")
    p_compile.add_argument("input")
    p_compile.add_argument("output")

    p_verify = sub.add_parser("verify")
    p_verify.add_argument("report")

    p_render = sub.add_parser("render")
    p_render.add_argument("report")
    p_render.add_argument("output")

    args = parser.parse_args(argv)
    try:
        if args.command == "compile":
            packet = _load_file(Path(args.input))
            report = compile_packet(packet)
            _write_exclusive(Path(args.output), canonical_json_bytes(report))
            print(report["receipt_sha256"])
            return 0
        if args.command == "verify":
            report = _load_file(Path(args.report))
            verify_report(report)
            print(report["receipt_sha256"])
            return 0
        if args.command == "render":
            report = _load_file(Path(args.report))
            text = render_markdown(report).encode("utf-8")
            _write_exclusive(Path(args.output), text)
            print(report["receipt_sha256"])
            return 0
    except (ContractError, OSError) as exc:
        print(f"ERROR: {exc}", file=__import__("sys").stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
