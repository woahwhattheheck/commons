#!/usr/bin/env python3
"""Compile evidence-bound security HOLD findings into an owner-review remediation SOW."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

SCHEMA = "security-remediation-scope-v1"
REPORT_SCHEMA = "security-remediation-sow-v1"
ACTIONABLE = {"PARTIAL", "HOLD_MISSING_EVIDENCE", "HOLD_STALE_EVIDENCE"}
NON_ACTIONABLE = {"SUPPORTED", "NOT_APPLICABLE"}
ALL_STATUSES = ACTIONABLE | NON_ACTIONABLE
MIN_FIXED_CENTS = 500_000
MAX_FIXED_CENTS = 3_000_000
MAX_FINDINGS = 100
MAX_INPUT_BYTES = 2_000_000
ID_RE = re.compile(r"^[A-Z][A-Z0-9_.-]{0,63}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
PROHIBITED_OUTCOME_RE = re.compile(
    r"(?:\bcertif(?:y|ied|ication)\b|\bguarantee(?:d)?\s+compliance\b|"
    r"\bsoc\s*2\s+compliant\b|\bhipaa\s+compliant\b|"
    r"\biso\s*27001\s+certified\b|\bpci(?:-dss)?\s+compliant\b|"
    r"\bpass(?:es|ed)?\s+(?:an?\s+)?audit\b)",
    re.IGNORECASE,
)
AUTHORITY = {
    "buyer_contact_authorized": False,
    "contract_acceptance_authorized": False,
    "compliance_certification_authorized": False,
    "security_attestation_authorized": False,
    "deployment_authorized": False,
    "invoice_authorized": False,
    "payment_authorized": False,
    "revenue_recognition_authorized": False,
}


class ScopeError(ValueError):
    """Fail-closed validation or verification error."""


def _reject_float(value: str) -> None:
    raise ScopeError(f"floating-point JSON is not allowed: {value}")


def _reject_constant(value: str) -> None:
    raise ScopeError(f"non-finite JSON is not allowed: {value}")


def _no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ScopeError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def loads_strict(raw: bytes) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ScopeError("input must be UTF-8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_no_duplicate_pairs,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except ScopeError:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise ScopeError(f"invalid JSON: {exc}") from exc


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ScopeError(f"value is not canonical JSON: {exc}") from exc


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _object(value: Any, required: set[str], optional: set[str], where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ScopeError(f"{where} must be an object")
    actual = set(value)
    missing = required - actual
    extra = actual - required - optional
    if missing or extra:
        raise ScopeError(f"{where} keys invalid: missing={sorted(missing)} extra={sorted(extra)}")
    return value


def _text(value: Any, where: str, *, max_len: int = 1200) -> str:
    if type(value) is not str or not value.strip() or len(value) > max_len:
        raise ScopeError(f"{where} must be a non-empty string <= {max_len} chars")
    return value


def _id(value: Any, where: str) -> str:
    text = _text(value, where, max_len=64)
    if not ID_RE.fullmatch(text):
        raise ScopeError(f"{where} has invalid identifier syntax")
    return text


def _utc(value: Any, where: str) -> dt.datetime:
    text = _text(value, where, max_len=40)
    if not text.endswith("Z"):
        raise ScopeError(f"{where} must be an explicit UTC Z timestamp")
    try:
        parsed = dt.datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise ScopeError(f"{where} is not a valid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != dt.timedelta(0):
        raise ScopeError(f"{where} must be UTC")
    return parsed


def _sha256(value: Any, where: str) -> str:
    text = _text(value, where, max_len=64)
    if not SHA_RE.fullmatch(text):
        raise ScopeError(f"{where} must be lowercase SHA-256")
    return text


def _string_list(value: Any, where: str, *, allow_empty: bool, max_items: int = 50) -> list[str]:
    if type(value) is not list or len(value) > max_items:
        raise ScopeError(f"{where} must be a list with <= {max_items} items")
    out = [_text(item, f"{where}[{index}]", max_len=500) for index, item in enumerate(value)]
    if not allow_empty and not out:
        raise ScopeError(f"{where} must not be empty")
    if len(set(out)) != len(out):
        raise ScopeError(f"{where} must not contain duplicates")
    return sorted(out)


def _id_list(value: Any, where: str, *, allow_empty: bool = True) -> list[str]:
    if type(value) is not list or len(value) > 100:
        raise ScopeError(f"{where} must be a list with <= 100 items")
    out = [_id(item, f"{where}[{index}]") for index, item in enumerate(value)]
    if not allow_empty and not out:
        raise ScopeError(f"{where} must not be empty")
    if len(set(out)) != len(out):
        raise ScopeError(f"{where} must not contain duplicates")
    return sorted(out)


def _price(value: Any, where: str) -> int:
    if type(value) is not int or value <= 0 or value > MAX_FIXED_CENTS:
        raise ScopeError(f"{where} must be an integer number of cents from 1 to {MAX_FIXED_CENTS}")
    return value


def _reject_prohibited_outcome(text: str, where: str) -> None:
    if PROHIBITED_OUTCOME_RE.search(text):
        raise ScopeError(f"{where} attempts to promise a prohibited certification/compliance/audit outcome")


def validate_manifest(value: Any) -> dict[str, Any]:
    manifest = _object(
        value,
        {"schema", "scope_id", "as_of", "currency", "source_packet", "findings"},
        set(),
        "manifest",
    )
    if manifest["schema"] != SCHEMA:
        raise ScopeError(f"schema must equal {SCHEMA}")
    scope_id = _id(manifest["scope_id"], "manifest.scope_id")
    as_of = _utc(manifest["as_of"], "manifest.as_of")
    if manifest["currency"] != "USD":
        raise ScopeError("manifest.currency must equal USD")

    packet = _object(
        manifest["source_packet"],
        {"packet_id", "sha256", "observed_at"},
        set(),
        "manifest.source_packet",
    )
    packet_id = _id(packet["packet_id"], "manifest.source_packet.packet_id")
    packet_sha = _sha256(packet["sha256"], "manifest.source_packet.sha256")
    packet_observed = _utc(packet["observed_at"], "manifest.source_packet.observed_at")
    if packet_observed > as_of:
        raise ScopeError("source packet cannot be observed after manifest.as_of")

    if type(manifest["findings"]) is not list or len(manifest["findings"]) > MAX_FINDINGS:
        raise ScopeError(f"manifest.findings must be a list with <= {MAX_FINDINGS} items")

    seen: set[str] = set()
    findings: list[dict[str, Any]] = []
    for index, raw in enumerate(manifest["findings"]):
        finding = _object(
            raw,
            {"id", "source_status", "requirement", "source_evidence_ids", "current_state", "gap", "remediation"},
            set(),
            f"findings[{index}]",
        )
        fid = _id(finding["id"], f"findings[{index}].id")
        if fid in seen:
            raise ScopeError(f"duplicate finding id: {fid}")
        seen.add(fid)
        status = finding["source_status"]
        if status not in ALL_STATUSES:
            raise ScopeError(f"findings[{index}].source_status is unsupported")
        normalized = {
            "id": fid,
            "source_status": status,
            "requirement": _text(finding["requirement"], f"findings[{index}].requirement"),
            "source_evidence_ids": _id_list(finding["source_evidence_ids"], f"findings[{index}].source_evidence_ids"),
            "current_state": _text(finding["current_state"], f"findings[{index}].current_state"),
            "gap": _text(finding["gap"], f"findings[{index}].gap"),
            "remediation": None,
        }
        remediation = finding["remediation"]
        if status in NON_ACTIONABLE:
            if remediation is not None:
                raise ScopeError(f"finding {fid} is {status} and cannot be converted into billable remediation")
        else:
            rem = _object(
                remediation,
                {"deliverable", "acceptance_test", "dependencies", "change_control_trigger", "owner_proposed_price_cents"},
                set(),
                f"findings[{index}].remediation",
            )
            deliverable = _text(rem["deliverable"], f"findings[{index}].remediation.deliverable")
            acceptance = _text(rem["acceptance_test"], f"findings[{index}].remediation.acceptance_test")
            change = _text(rem["change_control_trigger"], f"findings[{index}].remediation.change_control_trigger")
            _reject_prohibited_outcome(deliverable, f"finding {fid} deliverable")
            _reject_prohibited_outcome(acceptance, f"finding {fid} acceptance_test")
            _reject_prohibited_outcome(change, f"finding {fid} change_control_trigger")
            normalized["remediation"] = {
                "deliverable": deliverable,
                "acceptance_test": acceptance,
                "dependencies": _string_list(rem["dependencies"], f"findings[{index}].remediation.dependencies", allow_empty=True),
                "change_control_trigger": change,
                "owner_proposed_price_cents": _price(rem["owner_proposed_price_cents"], f"findings[{index}].remediation.owner_proposed_price_cents"),
            }
        findings.append(normalized)

    return {
        "schema": SCHEMA,
        "scope_id": scope_id,
        "as_of": manifest["as_of"],
        "currency": "USD",
        "source_packet": {
            "packet_id": packet_id,
            "sha256": packet_sha,
            "observed_at": packet["observed_at"],
        },
        "findings": sorted(findings, key=lambda row: row["id"]),
    }


def compile_bytes(raw: bytes) -> tuple[dict[str, Any], str]:
    manifest = validate_manifest(loads_strict(raw))
    actionable: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    total = 0
    for row in manifest["findings"]:
        if row["source_status"] in ACTIONABLE:
            rem = row["remediation"]
            assert rem is not None
            total += rem["owner_proposed_price_cents"]
            actionable.append(
                {
                    "finding_id": row["id"],
                    "source_status": row["source_status"],
                    "requirement": row["requirement"],
                    "source_evidence_ids": row["source_evidence_ids"],
                    "current_state": row["current_state"],
                    "gap": row["gap"],
                    **rem,
                }
            )
        else:
            excluded.append({"finding_id": row["id"], "reason": row["source_status"]})

    if not actionable:
        scope_status = "NO_ACTIONABLE_FINDINGS"
    elif MIN_FIXED_CENTS <= total <= MAX_FIXED_CENTS:
        scope_status = "OWNER_REVIEW_READY"
    else:
        scope_status = "HOLD_PRICE_OUTSIDE_FIXED_SCOPE"

    body = {
        "schema": REPORT_SCHEMA,
        "scope_id": manifest["scope_id"],
        "as_of": manifest["as_of"],
        "currency": "USD",
        "source_packet": manifest["source_packet"],
        "evidence_time_semantics": "HISTORICAL_OWNER_REVIEW_ONLY",
        "scope_status": scope_status,
        "work_items": actionable,
        "excluded_findings": excluded,
        "commercial": {
            "proposed_total_cents": total,
            "fixed_scope_min_cents": MIN_FIXED_CENTS,
            "fixed_scope_max_cents": MAX_FIXED_CENTS,
            "commercial_state": "PROPOSED_NOT_ACCEPTED",
            "pricing_authority": "OWNER_PROPOSED_INPUT_ONLY",
        },
        "authority": dict(AUTHORITY),
    }
    receipt = {
        "raw_input_sha256": _sha(raw),
        "semantic_manifest_sha256": _sha(canonical_bytes(manifest)),
        "report_body_sha256": _sha(canonical_bytes(body)),
    }
    report = {**body, "receipt": receipt}
    return report, render_markdown(report)


def verify_bytes(raw: bytes, report_raw: bytes) -> None:
    expected, _ = compile_bytes(raw)
    supplied = loads_strict(report_raw)
    if canonical_bytes(expected) != canonical_bytes(supplied):
        raise ScopeError("report does not exactly match deterministic recompilation")


def _money(cents: int) -> str:
    return f"${cents // 100:,}.{cents % 100:02d}"


def _md(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Security Remediation Scope — Owner Review",
        "",
        f"Scope: `{report['scope_id']}`  ",
        f"Evidence as-of: `{report['as_of']}`  ",
        f"Decision: `{report['scope_status']}`  ",
        f"Commercial state: `{report['commercial']['commercial_state']}`  ",
        f"Owner-proposed total: **{_money(report['commercial']['proposed_total_cents'])}**",
        "",
        "| Finding | Source status | Proposed price | Deliverable |",
        "| --- | --- | ---: | --- |",
    ]
    for item in report["work_items"]:
        lines.append(
            f"| `{item['finding_id']}` | `{item['source_status']}` | {_money(item['owner_proposed_price_cents'])} | {_md(item['deliverable'])} |"
        )
    if not report["work_items"]:
        lines.append("| — | — | $0.00 | No actionable held/partial findings. |")
    lines += ["", "## Work items", ""]
    for item in report["work_items"]:
        lines += [
            f"### {item['finding_id']}",
            "",
            f"**Requirement:** {item['requirement']}",
            "",
            f"**Current state:** {item['current_state']}",
            "",
            f"**Evidence/control gap:** {item['gap']}",
            "",
            f"**Source evidence IDs:** {', '.join('`' + value + '`' for value in item['source_evidence_ids']) or 'none declared'}",
            "",
            f"**Deliverable:** {item['deliverable']}",
            "",
            f"**Acceptance test:** {item['acceptance_test']}",
            "",
            f"**Dependencies:** {', '.join(item['dependencies']) or 'none declared'}",
            "",
            f"**Change control:** {item['change_control_trigger']}",
            "",
        ]
    lines += [
        "## Truth and authority boundary",
        "",
        "This packet is a historical owner-review scoping artifact. It does not certify compliance, attest security posture, guarantee audit passage, contact a buyer, accept a contract, authorize deployment/invoicing/payment, or recognize revenue. Pricing is caller-provided owner-proposed input and remains `PROPOSED_NOT_ACCEPTED`.",
        "",
        f"Receipt: `{report['receipt']['report_body_sha256']}`",
        "",
    ]
    return "\n".join(lines)


def _read_limited(path: Path) -> bytes:
    raw = path.read_bytes()
    if len(raw) > MAX_INPUT_BYTES:
        raise ScopeError(f"{path} exceeds byte ceiling")
    return raw


def _write_exclusive(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ScopeError(f"refusing to overwrite existing output: {path}") from exc


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    compile_p = sub.add_parser("compile")
    compile_p.add_argument("--input", required=True, type=Path)
    compile_p.add_argument("--report-json", required=True, type=Path)
    compile_p.add_argument("--report-md", required=True, type=Path)
    verify_p = sub.add_parser("verify")
    verify_p.add_argument("--input", required=True, type=Path)
    verify_p.add_argument("--report-json", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        raw = _read_limited(args.input)
        if args.command == "compile":
            if args.report_json.exists() or args.report_md.exists():
                raise ScopeError("refusing to overwrite an existing report output")
            report, markdown = compile_bytes(raw)
            _write_exclusive(args.report_json, canonical_bytes(report) + b"\n")
            _write_exclusive(args.report_md, markdown.encode("utf-8"))
        else:
            verify_bytes(raw, _read_limited(args.report_json))
    except (ScopeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
