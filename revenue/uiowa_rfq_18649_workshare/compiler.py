#!/usr/bin/env python3
"""Deterministic, fail-closed evidence compiler for UIOWA RFQ 18649 workshare.

The candidate packet is not an authority source. Evidence identity, provenance,
observation time, score, confidence, and scope are loaded from a source-controlled
trusted registry whose canonical SHA-256 is pinned in this module. Current-use
compile and verify sample process UTC; callers cannot provide the readiness clock.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import hmac
import json
import os
from pathlib import Path
import stat
from typing import Any

SCHEMA_VERSION = 2
REGISTRY_SCHEMA_VERSION = 1
SOLICITATION_ID = "18649"
BUYER = "University of Iowa"
SUBCONTRACTOR = "TJLabs"
BASE_FEE_USD = 24_000
OPTIONAL_READOUT_USD = 4_000
MAX_EVIDENCE_AGE_DAYS = 120
MAX_INPUT_BYTES = 2_000_000

TRUSTED_REGISTRY_PATH = Path(__file__).with_name("trusted_evidence_registry.json")
TRUSTED_REGISTRY_SHA256 = "b9e14496f43c4e445eba66a17daba4ab6131073af2bdcf2a40a450e737846e26"

PAYMENT_SCHEDULE = [
    {"milestone": "written authorization / kickoff", "percent": 40, "amount_usd": 9_600},
    {"milestone": "draft technical work package", "percent": 40, "amount_usd": 9_600},
    {"milestone": "accepted final technical work package", "percent": 20, "amount_usd": 4_800},
]
GROUPS = ("ESS", "RIS", "IAM")
DIMENSIONS = ("software", "security", "deployment", "ai_readiness")
EVIDENCE_KINDS = ("artifact", "demo", "interview", "metric")
DISPOSITIONS = ("ACCEPTED",)

EXPECTED_ROOT_KEYS = {"schema_version", "engagement", "observations"}
EXPECTED_ENGAGEMENT_KEYS = {
    "solicitation_id", "buyer", "prime_candidate", "subcontractor",
    "base_fee_usd", "optional_readout_usd",
}
EXPECTED_OBSERVATION_KEYS = {"evidence_id", "claim"}
EXPECTED_REGISTRY_KEYS = {
    "schema_version", "operation", "scope", "assessor_policy_id", "entries",
}
EXPECTED_REGISTRY_SCOPE_KEYS = {
    "solicitation_id", "buyer", "prime_candidate", "subcontractor",
}
EXPECTED_REGISTRY_ENTRY_KEYS = {
    "evidence_id", "group", "dimension", "evidence_kind", "source_id",
    "source_generation", "source_sha256", "observed_date", "claim_sha256",
    "maturity", "confidence_bp", "assessor_id", "disposition",
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
        "acceptance": "Every scored observation is bound to the pinned trusted registry and exact retained source generation.",
    },
    {
        "id": "D2",
        "name": "Technical maturity and gap matrix",
        "acceptance": "All 12 ESS/RIS/IAM × software/security/deployment/AI-readiness cells are classified; candidate data cannot choose scores.",
    },
    {
        "id": "D3",
        "name": "Draft finding and phased-roadmap production support",
        "acceptance": "Only currently fresh, trusted evidence produces a maturity finding; holds remain explicit.",
    },
    {
        "id": "D4",
        "name": "Reproducibility and consistency receipt",
        "acceptance": "Current verification recompiles against the pinned trust root and process UTC, not only the report receipt.",
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
    """Input, trusted registry, or report violates the bounded workshare contract."""


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


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _require_exact_keys(value: dict[str, Any], expected: set[str], where: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ContractError(
            f"{where} keys mismatch: missing={sorted(expected - actual)} unknown={sorted(actual - expected)}"
        )


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


def _require_sha256(value: Any, where: str) -> str:
    value = _require_str(value, where)
    if not __import__("re").fullmatch(r"[0-9a-f]{64}", value):
        raise ContractError(f"{where} must be 64 lowercase hex")
    return value


def _parse_date(value: Any, where: str) -> _dt.date:
    text = _require_str(value, where)
    if not __import__("re").fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ContractError(f"{where} must be YYYY-MM-DD")
    try:
        return _dt.date.fromisoformat(text)
    except ValueError as exc:
        raise ContractError(f"{where} is not a real calendar date") from exc


def _current_utc_date() -> _dt.date:
    return _dt.datetime.now(_dt.timezone.utc).date()


def _read_regular_bytes(path: Path) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ContractError(f"cannot open ordinary input file: {path}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ContractError(f"input must be ordinary file: {path}")
        if info.st_size > MAX_INPUT_BYTES:
            raise ContractError(f"input exceeds {MAX_INPUT_BYTES} bytes: {path}")
        chunks: list[bytes] = []
        remaining = MAX_INPUT_BYTES + 1
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > MAX_INPUT_BYTES:
            raise ContractError(f"input exceeds {MAX_INPUT_BYTES} bytes: {path}")
        return data
    finally:
        os.close(fd)


def _load_json_file(path: Path) -> Any:
    raw = _read_regular_bytes(path)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError(f"input must be UTF-8: {path}") from exc
    return loads_strict(text)


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


def _validate_registry(raw: Any) -> dict[str, Any]:
    if type(raw) is not dict:
        raise ContractError("trusted registry must be object")
    _require_exact_keys(raw, EXPECTED_REGISTRY_KEYS, "trusted registry")
    if _require_int(raw["schema_version"], "trusted registry.schema_version") != REGISTRY_SCHEMA_VERSION:
        raise ContractError("trusted registry schema_version drift")
    operation = _require_str(raw["operation"], "trusted registry.operation")
    policy = _require_str(raw["assessor_policy_id"], "trusted registry.assessor_policy_id")
    scope = raw["scope"]
    if type(scope) is not dict:
        raise ContractError("trusted registry.scope must be object")
    _require_exact_keys(scope, EXPECTED_REGISTRY_SCOPE_KEYS, "trusted registry.scope")
    validated_scope = {
        "solicitation_id": _require_str(scope["solicitation_id"], "trusted registry.scope.solicitation_id"),
        "buyer": _require_str(scope["buyer"], "trusted registry.scope.buyer"),
        "prime_candidate": _require_str(scope["prime_candidate"], "trusted registry.scope.prime_candidate"),
        "subcontractor": _require_str(scope["subcontractor"], "trusted registry.scope.subcontractor"),
    }
    if validated_scope["solicitation_id"] != SOLICITATION_ID or validated_scope["buyer"] != BUYER or validated_scope["subcontractor"] != SUBCONTRACTOR:
        raise ContractError("trusted registry scope drift")

    raw_entries = raw["entries"]
    if type(raw_entries) is not list:
        raise ContractError("trusted registry.entries must be array")
    entries: list[dict[str, Any]] = []
    for index, item in enumerate(raw_entries):
        where = f"trusted registry.entries[{index}]"
        if type(item) is not dict:
            raise ContractError(f"{where} must be object")
        _require_exact_keys(item, EXPECTED_REGISTRY_ENTRY_KEYS, where)
        entry = {
            "evidence_id": _require_str(item["evidence_id"], f"{where}.evidence_id"),
            "group": _require_str(item["group"], f"{where}.group"),
            "dimension": _require_str(item["dimension"], f"{where}.dimension"),
            "evidence_kind": _require_str(item["evidence_kind"], f"{where}.evidence_kind"),
            "source_id": _require_str(item["source_id"], f"{where}.source_id"),
            "source_generation": _require_str(item["source_generation"], f"{where}.source_generation"),
            "source_sha256": _require_sha256(item["source_sha256"], f"{where}.source_sha256"),
            "observed_date": _parse_date(item["observed_date"], f"{where}.observed_date").isoformat(),
            "claim_sha256": _require_sha256(item["claim_sha256"], f"{where}.claim_sha256"),
            "maturity": _require_int(item["maturity"], f"{where}.maturity", low=0, high=4),
            "confidence_bp": _require_int(item["confidence_bp"], f"{where}.confidence_bp", low=0, high=10_000),
            "assessor_id": _require_str(item["assessor_id"], f"{where}.assessor_id"),
            "disposition": _require_str(item["disposition"], f"{where}.disposition"),
        }
        if entry["group"] not in GROUPS:
            raise ContractError(f"{where}.group unknown: {entry['group']}")
        if entry["dimension"] not in DIMENSIONS:
            raise ContractError(f"{where}.dimension unknown: {entry['dimension']}")
        if entry["evidence_kind"] not in EVIDENCE_KINDS:
            raise ContractError(f"{where}.evidence_kind unknown: {entry['evidence_kind']}")
        if entry["disposition"] not in DISPOSITIONS:
            raise ContractError(f"{where}.disposition not accepted")
        entries.append(entry)
    ids = [entry["evidence_id"] for entry in entries]
    if len(ids) != len(set(ids)):
        raise ContractError("trusted registry duplicate evidence_id")
    entries.sort(key=lambda item: item["evidence_id"])
    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "operation": operation,
        "scope": validated_scope,
        "assessor_policy_id": policy,
        "entries": entries,
    }


def _load_trusted_registry() -> dict[str, Any]:
    registry = _validate_registry(_load_json_file(TRUSTED_REGISTRY_PATH))
    actual_root = _sha256_bytes(canonical_json_bytes(registry))
    if not hmac.compare_digest(actual_root, TRUSTED_REGISTRY_SHA256):
        raise ContractError("trusted registry root mismatch")
    return registry


def _validate_candidate_observations(raw: Any, registry: dict[str, Any], evaluation_date: _dt.date) -> list[dict[str, Any]]:
    if type(raw) is not list:
        raise ContractError("observations must be array")
    candidates: dict[str, str] = {}
    for index, item in enumerate(raw):
        where = f"observations[{index}]"
        if type(item) is not dict:
            raise ContractError(f"{where} must be object")
        _require_exact_keys(item, EXPECTED_OBSERVATION_KEYS, where)
        evidence_id = _require_str(item["evidence_id"], f"{where}.evidence_id")
        claim = _require_str(item["claim"], f"{where}.claim")
        if evidence_id in candidates:
            raise ContractError("duplicate evidence_id")
        candidates[evidence_id] = claim

    trusted = {entry["evidence_id"]: entry for entry in registry["entries"]}
    if set(candidates) != set(trusted):
        raise ContractError(
            f"candidate evidence set must exactly match trusted registry: missing={sorted(set(trusted)-set(candidates))} unknown={sorted(set(candidates)-set(trusted))}"
        )

    observations: list[dict[str, Any]] = []
    for evidence_id in sorted(trusted):
        entry = trusted[evidence_id]
        claim = candidates[evidence_id]
        if not hmac.compare_digest(_sha256_text(claim), entry["claim_sha256"]):
            raise ContractError(f"claim does not match trusted registry: {evidence_id}")
        observed = _dt.date.fromisoformat(entry["observed_date"])
        if observed > evaluation_date:
            raise ContractError(f"trusted evidence is in the future: {evidence_id}")
        observations.append({
            "evidence_id": evidence_id,
            "group": entry["group"],
            "dimension": entry["dimension"],
            "evidence_kind": entry["evidence_kind"],
            "source_id": entry["source_id"],
            "source_generation": entry["source_generation"],
            "source_sha256": entry["source_sha256"],
            "observed_date": entry["observed_date"],
            "claim": claim,
            "claim_sha256": entry["claim_sha256"],
            "maturity": entry["maturity"],
            "confidence_bp": entry["confidence_bp"],
            "assessor_id": entry["assessor_id"],
            "assessor_policy_id": registry["assessor_policy_id"],
            "disposition": entry["disposition"],
        })
    observations.sort(key=lambda item: (item["group"], item["dimension"], item["evidence_id"]))
    return observations


def _cell(group: str, dimension: str, observations: list[dict[str, Any]], evaluation_date: _dt.date) -> dict[str, Any]:
    rows = [item for item in observations if item["group"] == group and item["dimension"] == dimension]
    rows.sort(key=lambda item: item["evidence_id"])
    base = {
        "group": group,
        "dimension": dimension,
        "evidence_ids": [item["evidence_id"] for item in rows],
        "source_generations": [item["source_generation"] for item in rows],
        "source_sha256": [item["source_sha256"] for item in rows],
    }
    if not rows:
        return {**base, "status": "HOLD_MISSING_EVIDENCE", "maturity": None, "confidence_bp": None, "reason_codes": ["NO_TRUSTED_EVIDENCE"]}

    maturity_values = sorted({item["maturity"] for item in rows})
    if len(maturity_values) > 1:
        return {**base, "status": "HOLD_CONFLICT", "maturity": None, "confidence_bp": None, "reason_codes": ["TRUSTED_MATURITY_CONFLICT"]}

    stale_ids = [
        item["evidence_id"]
        for item in rows
        if (evaluation_date - _dt.date.fromisoformat(item["observed_date"])).days > MAX_EVIDENCE_AGE_DAYS
    ]
    if stale_ids:
        return {**base, "status": "HOLD_STALE_EVIDENCE", "maturity": None, "confidence_bp": None, "reason_codes": ["STALE_TRUSTED_EVIDENCE:" + ",".join(stale_ids)]}

    return {
        **base,
        "status": "READY",
        "maturity": maturity_values[0],
        "confidence_bp": min(item["confidence_bp"] for item in rows),
        "reason_codes": [],
    }


def _compile_with_registry(packet: Any, registry: dict[str, Any], evaluation_date: _dt.date) -> dict[str, Any]:
    if type(packet) is not dict:
        raise ContractError("root must be object")
    _require_exact_keys(packet, EXPECTED_ROOT_KEYS, "root")
    if _require_int(packet["schema_version"], "schema_version") != SCHEMA_VERSION:
        raise ContractError("schema_version drift")
    engagement = _validate_engagement(packet["engagement"])
    scope = registry["scope"]
    for field in ("solicitation_id", "buyer", "prime_candidate", "subcontractor"):
        if engagement[field] != scope[field]:
            raise ContractError(f"engagement does not match trusted registry scope: {field}")

    observations = _validate_candidate_observations(packet["observations"], registry, evaluation_date)
    matrix = [_cell(group, dimension, observations, evaluation_date) for group in GROUPS for dimension in DIMENSIONS]
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
        "evaluation_date_utc": evaluation_date.isoformat(),
        "trusted_registry_operation": registry["operation"],
        "trusted_registry_sha256": TRUSTED_REGISTRY_SHA256,
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
    receipt = _sha256_bytes(canonical_json_bytes(report_without_receipt))
    return {**report_without_receipt, "receipt_sha256": receipt}


def compile_packet(packet: Any) -> dict[str, Any]:
    """Compile against the pinned registry using process-owned current UTC."""
    return _compile_with_registry(packet, _load_trusted_registry(), _current_utc_date())


def _candidate_from_report(report: dict[str, Any]) -> dict[str, Any]:
    observations = report.get("observations")
    if type(observations) is not list:
        raise ContractError("report observations must be array")
    candidate_rows = []
    for index, item in enumerate(observations):
        if type(item) is not dict:
            raise ContractError(f"report observations[{index}] must be object")
        candidate_rows.append({
            "evidence_id": _require_str(item.get("evidence_id"), f"report observations[{index}].evidence_id"),
            "claim": _require_str(item.get("claim"), f"report observations[{index}].claim"),
        })
    engagement = report.get("engagement")
    if type(engagement) is not dict:
        raise ContractError("report engagement must be object")
    return {"schema_version": SCHEMA_VERSION, "engagement": {
        "solicitation_id": engagement.get("solicitation_id"),
        "buyer": engagement.get("buyer"),
        "prime_candidate": engagement.get("prime_candidate"),
        "subcontractor": engagement.get("subcontractor"),
        "base_fee_usd": engagement.get("base_fee_usd"),
        "optional_readout_usd": engagement.get("optional_readout_usd"),
    }, "observations": candidate_rows}


def verify_report(report: Any) -> bool:
    """Verify integrity *and* current semantic validity against pinned authority."""
    if type(report) is not dict:
        raise ContractError("report must be object")
    receipt = _require_sha256(report.get("receipt_sha256"), "receipt_sha256")
    unsigned = dict(report)
    del unsigned["receipt_sha256"]
    expected_receipt = _sha256_bytes(canonical_json_bytes(unsigned))
    if not hmac.compare_digest(receipt, expected_receipt):
        raise ContractError("receipt mismatch")
    if report.get("trusted_registry_sha256") != TRUSTED_REGISTRY_SHA256:
        raise ContractError("report trusted registry root mismatch")
    today = _current_utc_date()
    if report.get("evaluation_date_utc") != today.isoformat():
        raise ContractError("report is not current for process UTC date")
    registry = _load_trusted_registry()
    expected_report = _compile_with_registry(_candidate_from_report(report), registry, today)
    if not hmac.compare_digest(canonical_json_bytes(report), canonical_json_bytes(expected_report)):
        raise ContractError("report semantic recompile mismatch")
    return True


def render_markdown(report: dict[str, Any]) -> str:
    verify_report(report)
    lines = [
        "# University of Iowa RFQ 18649 — TJLabs technical workshare",
        "",
        f"- State: `{report['aggregate_state']}`",
        f"- Current UTC evidence date: `{report['evaluation_date_utc']}`",
        f"- Trusted registry: `{report['trusted_registry_sha256']}`",
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
        lines.append(f"| {row['group']} | {row['dimension']} | {row['status']} | {maturity} | {confidence} |")
    lines.extend([
        "",
        "## Authority boundary",
        "",
        "TJLabs prepares bounded technical evidence and synthesis support. The prime retains University communication, proposal submission, references, insurance, contracting, final professional judgment, staffing/travel commitments, and final recommendations.",
        "",
        "No award, buyer acceptance, payment, cash, or recognized revenue is claimed by this packet.",
        "",
    ])
    return "\n".join(lines)


def _write_exclusive(path: Path, data: bytes) -> None:
    parent = path.parent
    if not parent.exists() or not parent.is_dir() or parent.is_symlink():
        raise ContractError(f"output parent missing, symlinked, or not directory: {parent}")
    if path.exists() or path.is_symlink():
        raise ContractError(f"refusing existing output path: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


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
            packet = _load_json_file(Path(args.input))
            report = compile_packet(packet)
            _write_exclusive(Path(args.output), canonical_json_bytes(report))
            print(report["receipt_sha256"])
            return 0
        if args.command == "verify":
            report = _load_json_file(Path(args.report))
            verify_report(report)
            print(report["receipt_sha256"])
            return 0
        if args.command == "render":
            report = _load_json_file(Path(args.report))
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
