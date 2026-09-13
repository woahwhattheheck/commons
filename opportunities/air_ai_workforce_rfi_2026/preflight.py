#!/usr/bin/env python3
"""Evidence-bound qualification gate for AIR's 2026 AI-workforce RFI.

This module performs no network call, outreach, submission, participant-data access,
pricing, contracting, payment, or revenue action.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SOURCE_SCHEMA = "air.ai_workforce_rfi.source_snapshot/v1"
OWNER_SCHEMA = "air.ai_workforce_rfi.owner_inputs/v1"
RECEIPT_SCHEMA = "air.ai_workforce_rfi.preflight_receipt/v1"
MAX_SOURCE_AGE = timedelta(days=7)
MAX_BYTES = 2_000_000
MAX_SAFE_INT = 9_007_199_254_740_991

DIRECT_READY = "DIRECT_RFI_READY_FOR_OWNER_REVIEW"
PARTNER_READY = "PARTNER_RFI_READY_FOR_OWNER_REVIEW"
PARTNER_REQUIRED = "PARTNER_REQUIRED"
HOLD = "HOLD"

PLACEHOLDER = re.compile(r"(?:OWNER_INPUT_REQUIRED|\bTBD\b|\bTODO\b|<[^>]+>)", re.I)
SHA256_RE = re.compile(r"[0-9a-f]{64}")
UTC_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
URL_RE = re.compile(r"https://[^\s]+")
SECRET_RE = re.compile(r"(?:sk-[A-Za-z0-9_-]{12,}|api[_-]?key|password|bearer\s+[A-Za-z0-9._-]+)", re.I)

AUTHORITY = {
    "air_contact_authorized": False,
    "partner_contact_authorized": False,
    "submittable_submission_authorized": False,
    "participant_data_access_authorized": False,
    "pricing_or_contract_commitment_authorized": False,
    "award_or_revenue_claim_authorized": False,
}

SOURCE_KEYS = {
    "schema","opportunity_id","buyer","title","release_date","information_due_at",
    "notification_window","checked_at","official_sources","rfp_pdf_bytes_locally_acquired",
    "rfp_pdf_sha256","rfi_has_award","future_funding_or_invitation_guaranteed",
    "submission_channel","eligible_respondent_types","respondent_characteristics",
    "focus_areas","maturity_choices","prompts","review_criteria","authority",
}
OWNER_KEYS = {"schema","organization","contact","innovation","workforce_track_record","partner","evidence_design","claims"}
ORG_KEYS = {"public_name","organization_type","background","website"}
CONTACT_KEYS = {"name","title","email","phone"}
INNOVATION_KEYS = {
    "project_title","summary","focus_areas","workforce_challenge","learning_questions",
    "population_description","population_size_2027_2028","technical_approach","maturity",
    "early_results","safeguards","air_partnership",
}
TRACK_KEYS = {"record_id","workforce_domain","population","period_start","period_end","evidence_ref","evidence_sha256","externally_supportable"}
PARTNER_KEYS = {"status","organization_ref","population_delivery_role","evidence_ref","evidence_sha256","workforce_track_record"}
DESIGN_KEYS = {"worker_voice","primary_outcomes","comparison_design","instrumentation","privacy_plan","fairness_plan","human_oversight","failure_modes","air_independent_evaluation_role"}
CLAIM_KEYS = {"claim_id","kind","text","evidence_ref","evidence_sha256","support_level"}

class PreflightError(ValueError):
    pass

def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise PreflightError(f"duplicate JSON key: {key}")
        out[key] = value
    return out

def _bad_constant(value: str):
    raise PreflightError(f"non-finite JSON value is forbidden: {value}")

def _validate_scalar_graph(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if type(value) is int:
        if abs(value) > MAX_SAFE_INT:
            raise PreflightError(f"unsafe integer at {path}")
        return
    if isinstance(value, float):
        raise PreflightError(f"floats are forbidden at {path}")
    if isinstance(value, list):
        if len(value) > 500:
            raise PreflightError(f"array too large at {path}")
        for i, item in enumerate(value):
            _validate_scalar_graph(item, f"{path}[{i}]")
        return
    if isinstance(value, dict):
        if len(value) > 500:
            raise PreflightError(f"object too large at {path}")
        for key, item in value.items():
            if not isinstance(key, str):
                raise PreflightError(f"non-string key at {path}")
            _validate_scalar_graph(item, f"{path}.{key}")
        return
    raise PreflightError(f"unsupported JSON type at {path}")

def load_json_bytes(raw: bytes, label: str) -> dict:
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise PreflightError(f"{label} bytes invalid or too large")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PreflightError(f"{label} must be UTF-8") from exc
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_bad_constant)
    except PreflightError:
        raise
    except json.JSONDecodeError as exc:
        raise PreflightError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise PreflightError(f"{label} must be a JSON object")
    _validate_scalar_graph(value)
    return value

def canonical_bytes(value: Any) -> bytes:
    _validate_scalar_graph(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def sha256(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical_bytes(value)
    return hashlib.sha256(raw).hexdigest()

def _expect_keys(value: dict, expected: set[str], label: str) -> None:
    got = set(value)
    if got != expected:
        missing = sorted(expected - got)
        extra = sorted(got - expected)
        raise PreflightError(f"{label} key mismatch missing={missing} extra={extra}")

def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 10_000 and not PLACEHOLDER.search(value)

def _digest(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))

def _date(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise PreflightError(f"{label} must be YYYY-MM-DD")
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise PreflightError(f"{label} must be YYYY-MM-DD") from exc

def parse_utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not UTC_RE.fullmatch(value):
        raise PreflightError(f"{label} must be canonical whole-second UTC")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise PreflightError(f"{label} invalid UTC timestamp") from exc

def trusted_time(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise PreflightError("trusted_now must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0)

def _source(source: dict) -> None:
    _expect_keys(source, SOURCE_KEYS, "source")
    if source["schema"] != SOURCE_SCHEMA:
        raise PreflightError("unsupported source schema")
    if source["buyer"] != "American Institutes for Research":
        raise PreflightError("source buyer mismatch")
    if source["rfi_has_award"] is not False or source["future_funding_or_invitation_guaranteed"] is not False:
        raise PreflightError("source must preserve no-award/no-guarantee truth")
    if source["submission_channel"] != "Submittable":
        raise PreflightError("submission channel mismatch")
    parse_utc(source["information_due_at"], "source.information_due_at")
    parse_utc(source["checked_at"], "source.checked_at")
    _date(source["release_date"], "source.release_date")
    if source["rfp_pdf_bytes_locally_acquired"] is not False:
        if not _digest(source["rfp_pdf_sha256"]):
            raise PreflightError("locally acquired PDF requires exact SHA-256")
    elif source["rfp_pdf_sha256"] is not None:
        raise PreflightError("do not publish a PDF digest when bytes were not locally acquired")
    sources = source["official_sources"]
    if not isinstance(sources, list) or len(sources) < 3:
        raise PreflightError("official source inventory incomplete")
    for i, row in enumerate(sources):
        if not isinstance(row, dict):
            raise PreflightError(f"official source {i} malformed")
        _expect_keys(row, {"class","url","label"}, f"official_sources[{i}]")
        if row["class"] != "OFFICIAL" or not isinstance(row["url"], str) or not URL_RE.fullmatch(row["url"]):
            raise PreflightError(f"official source {i} is not an official HTTPS record")
        if not _text(row["label"]):
            raise PreflightError(f"official source {i} label malformed")
    focus = source["focus_areas"]
    if not isinstance(focus, list) or len(focus) != 4 or len(focus) != len(set(focus)) or not all(_text(x) for x in focus):
        raise PreflightError("source focus areas malformed")
    maturity = source["maturity_choices"]
    if maturity != ["Concept","Prototype","Pilot","Deployed solution"]:
        raise PreflightError("source maturity choices drift")
    prompts = source["prompts"]
    if not isinstance(prompts, list) or len(prompts) != 12:
        raise PreflightError("source must contain all 12 prompts")
    nums = []
    limits = {}
    for i, row in enumerate(prompts):
        if not isinstance(row, dict):
            raise PreflightError(f"prompt {i} malformed")
        _expect_keys(row, {"number","name","word_limit"}, f"prompt[{i}]")
        if type(row["number"]) is not int or not (1 <= row["number"] <= 12):
            raise PreflightError("prompt number malformed")
        if not _text(row["name"]):
            raise PreflightError("prompt name malformed")
        wl = row["word_limit"]
        if wl is not None and (type(wl) is not int or wl <= 0):
            raise PreflightError("prompt word limit malformed")
        nums.append(row["number"]); limits[row["number"]] = wl
    if nums != list(range(1,13)):
        raise PreflightError("prompt numbering drift")
    expected_limits = {3:200,4:300,5:200,6:200,7:100,8:300,10:200,11:200,12:150}
    for n, limit in expected_limits.items():
        if limits[n] != limit:
            raise PreflightError(f"prompt {n} word limit drift")
    if not isinstance(source["review_criteria"], list) or len(source["review_criteria"]) != 6:
        raise PreflightError("review criteria malformed")
    if source["authority"] != AUTHORITY:
        raise PreflightError("source authority ceiling drift")

def _track_record(rows: Any, label: str, blockers: list[str]) -> int:
    if not isinstance(rows, list):
        raise PreflightError(f"{label} must be a list")
    seen = set()
    supportable = 0
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise PreflightError(f"{label}[{i}] must be an object")
        _expect_keys(row, TRACK_KEYS, f"{label}[{i}]")
        rid = row["record_id"]
        if not _text(rid) or rid in seen:
            blockers.append(f"{label.upper()}_RECORD_ID_INVALID_OR_DUPLICATE")
        seen.add(rid)
        for key in ("workforce_domain","population","evidence_ref"):
            if not _text(row[key]):
                blockers.append(f"{label.upper()}_{i}_{key.upper()}_REQUIRED")
        if not _digest(row["evidence_sha256"]):
            blockers.append(f"{label.upper()}_{i}_EVIDENCE_SHA256_REQUIRED")
        start = _date(row["period_start"], f"{label}[{i}].period_start")
        end = _date(row["period_end"], f"{label}[{i}].period_end")
        if end < start:
            blockers.append(f"{label.upper()}_{i}_PERIOD_INVERTED")
        if type(row["externally_supportable"]) is not bool:
            raise PreflightError(f"{label}[{i}].externally_supportable must be bool")
        if row["externally_supportable"] is True and _text(row["evidence_ref"]) and _digest(row["evidence_sha256"]):
            supportable += 1
    return supportable

def _claims(rows: Any, blockers: list[str]) -> tuple[int,int,int]:
    if not isinstance(rows, list):
        raise PreflightError("claims must be a list")
    seen = set()
    maturity = early = supported = 0
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise PreflightError(f"claims[{i}] must be an object")
        _expect_keys(row, CLAIM_KEYS, f"claims[{i}]")
        cid = row["claim_id"]
        if not _text(cid) or cid in seen:
            blockers.append("CLAIM_ID_INVALID_OR_DUPLICATE")
        seen.add(cid)
        if row["kind"] not in {"MATURITY","EARLY_RESULT","OUTCOME","TECHNICAL_CAPABILITY"}:
            blockers.append(f"CLAIM_{i}_KIND_UNSUPPORTED")
        if row["support_level"] not in {"SUPPORTED","UNSUPPORTED"}:
            blockers.append(f"CLAIM_{i}_SUPPORT_LEVEL_INVALID")
        if not _text(row["text"]):
            blockers.append(f"CLAIM_{i}_TEXT_REQUIRED")
        if row["support_level"] == "SUPPORTED":
            if not _text(row["evidence_ref"]) or not _digest(row["evidence_sha256"]):
                blockers.append(f"CLAIM_{i}_SUPPORTED_WITHOUT_EVIDENCE")
            else:
                supported += 1
                if row["kind"] == "MATURITY": maturity += 1
                if row["kind"] == "EARLY_RESULT": early += 1
        else:
            blockers.append(f"UNSUPPORTED_CLAIM:{cid}")
    return supported, maturity, early

def _owner(owner: dict) -> None:
    _expect_keys(owner, OWNER_KEYS, "owner")
    if owner["schema"] != OWNER_SCHEMA:
        raise PreflightError("unsupported owner schema")
    for label, keyset in (
        ("organization", ORG_KEYS),("contact",CONTACT_KEYS),("innovation",INNOVATION_KEYS),
        ("partner",PARTNER_KEYS),("evidence_design",DESIGN_KEYS)
    ):
        if not isinstance(owner[label], dict):
            raise PreflightError(f"{label} must be object")
        _expect_keys(owner[label], keyset, label)
    if not isinstance(owner["workforce_track_record"], list) or not isinstance(owner["claims"], list):
        raise PreflightError("track record and claims must be lists")

def evaluate(source: dict, owner: dict, *, trusted_now: datetime) -> dict:
    _source(source); _owner(owner)
    now = trusted_time(trusted_now)
    checked = parse_utc(source["checked_at"], "source.checked_at")
    due = parse_utc(source["information_due_at"], "source.information_due_at")
    if checked > now:
        raise PreflightError("source checked_at cannot be in the future")

    blockers: list[str] = []
    warnings: list[str] = []
    route_gaps: list[str] = []

    if now - checked > MAX_SOURCE_AGE:
        blockers.append("SOURCE_SNAPSHOT_OLDER_THAN_7_DAYS")
    if now >= due:
        blockers.append("RFI_DEADLINE_PASSED")
    if source["rfi_has_award"] is not False:
        blockers.append("RFI_AWARD_TRUTH_DRIFT")

    org = owner["organization"]
    for key in ORG_KEYS:
        if not _text(org[key]):
            blockers.append(f"ORGANIZATION_{key.upper()}_REQUIRED")
    if not isinstance(org["website"], str) or (not PLACEHOLDER.search(org["website"]) and not URL_RE.fullmatch(org["website"])):
        blockers.append("ORGANIZATION_WEBSITE_MUST_BE_HTTPS")

    contact = owner["contact"]
    for key in CONTACT_KEYS:
        if not _text(contact[key]):
            blockers.append(f"PRIVATE_CONTACT_{key.upper()}_REQUIRED")
    # Contact PII is checked only for completeness. It is never copied to the receipt.

    inv = owner["innovation"]
    for key in ("project_title","summary","workforce_challenge","population_description","technical_approach","safeguards","air_partnership"):
        if not _text(inv[key]):
            blockers.append(f"INNOVATION_{key.upper()}_REQUIRED")
    if inv["early_results"] != "NO_EARLY_RESULTS_CLAIMED" and not _text(inv["early_results"]):
        blockers.append("EARLY_RESULTS_TEXT_REQUIRED")
    if inv["maturity"] not in source["maturity_choices"]:
        blockers.append("MATURITY_NOT_IN_AIR_CHOICES")
    areas = inv["focus_areas"]
    if not isinstance(areas, list) or not areas:
        blockers.append("AT_LEAST_ONE_AIR_FOCUS_AREA_REQUIRED")
    else:
        if len(areas) != len(set(areas)):
            blockers.append("DUPLICATE_FOCUS_AREA")
        unknown = sorted(str(x) for x in areas if x not in source["focus_areas"])
        if unknown:
            blockers.append("UNKNOWN_FOCUS_AREA:" + ",".join(unknown))
    questions = inv["learning_questions"]
    if not isinstance(questions, list) or not questions or not all(_text(x) for x in questions):
        blockers.append("LEARNING_QUESTIONS_REQUIRED")
    size = inv["population_size_2027_2028"]
    if type(size) is not int or size <= 0 or size > MAX_SAFE_INT:
        blockers.append("POSITIVE_2027_2028_POPULATION_SIZE_REQUIRED")

    design = owner["evidence_design"]
    for key in ("worker_voice","comparison_design","instrumentation","privacy_plan","fairness_plan","human_oversight","air_independent_evaluation_role"):
        if not _text(design[key]):
            blockers.append(f"EVIDENCE_DESIGN_{key.upper()}_REQUIRED")
    for key in ("primary_outcomes","failure_modes"):
        value = design[key]
        if not isinstance(value, list) or not value or not all(_text(x) for x in value):
            blockers.append(f"EVIDENCE_DESIGN_{key.upper()}_REQUIRED")

    direct_track_count = _track_record(owner["workforce_track_record"], "workforce_track_record", blockers)

    partner = owner["partner"]
    if partner["status"] not in {"NONE","PROSPECTIVE","COMMITTED"}:
        blockers.append("PARTNER_STATUS_INVALID")
    partner_track_count = _track_record(partner["workforce_track_record"], "partner_track_record", blockers)
    partner_complete = False
    if partner["status"] == "COMMITTED":
        for key in ("organization_ref","population_delivery_role","evidence_ref"):
            if not _text(partner[key]):
                blockers.append(f"COMMITTED_PARTNER_{key.upper()}_REQUIRED")
        if not _digest(partner["evidence_sha256"]):
            blockers.append("COMMITTED_PARTNER_EVIDENCE_SHA256_REQUIRED")
        if partner_track_count < 1:
            blockers.append("COMMITTED_PARTNER_WORKFORCE_TRACK_RECORD_REQUIRED")
        partner_complete = all([
            _text(partner["organization_ref"]), _text(partner["population_delivery_role"]),
            _text(partner["evidence_ref"]), _digest(partner["evidence_sha256"]),
            partner_track_count >= 1,
        ])
    elif partner["status"] == "PROSPECTIVE":
        warnings.append("PROSPECTIVE_PARTNER_IS_NOT_A_COMMITMENT")

    supported_claims, maturity_claims, early_claims = _claims(owner["claims"], blockers)
    if inv["maturity"] != "Concept" and maturity_claims < 1:
        blockers.append("NON_CONCEPT_MATURITY_REQUIRES_EVIDENCE")
    if inv["early_results"] != "NO_EARLY_RESULTS_CLAIMED" and early_claims < 1:
        blockers.append("EARLY_RESULTS_REQUIRE_EVIDENCE")

    direct_route = direct_track_count >= 1
    partner_route = partner["status"] == "COMMITTED" and partner_complete

    if not direct_route:
        route_gaps.append("DIRECT_ROUTE_LACKS_EVIDENCED_WORKFORCE_DELIVERY_TRACK_RECORD")
    if not partner_route:
        if partner["status"] == "NONE":
            route_gaps.append("NO_COMMITTED_WORKFORCE_DELIVERY_PARTNER")
        elif partner["status"] == "PROSPECTIVE":
            route_gaps.append("PROSPECTIVE_PARTNER_NOT_COMMITTED")
        else:
            route_gaps.append("COMMITTED_PARTNER_EVIDENCE_INCOMPLETE")

    # Route-specific absence is classified separately from general malformed/incomplete input.
    general_blockers = list(blockers)
    state = HOLD
    route = "NONE"

    if not general_blockers:
        if direct_route:
            state, route = DIRECT_READY, "DIRECT_RFI"
        elif partner_route:
            state, route = PARTNER_READY, "PARTNER_RFI"
        else:
            state, route = PARTNER_REQUIRED, "PARTNER_RFI"
    elif direct_route or partner_route:
        state, route = HOLD, ("DIRECT_RFI" if direct_route else "PARTNER_RFI")
    else:
        state, route = HOLD, "PARTNER_RFI"

    result = {
        "schema": RECEIPT_SCHEMA,
        "state": state,
        "recommended_route": route,
        "evaluated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_snapshot_sha256": sha256(source),
        "owner_input_sha256": sha256(owner),
        "project_title": inv["project_title"] if isinstance(inv["project_title"], str) else "",
        "focus_areas": sorted(areas) if isinstance(areas, list) and all(isinstance(x,str) for x in areas) else [],
        "maturity": inv["maturity"] if isinstance(inv["maturity"], str) else "",
        "population_size_2027_2028": size if type(size) is int else None,
        "direct_track_record_count": direct_track_count,
        "partner_track_record_count": partner_track_count,
        "supported_claim_count": supported_claims,
        "blockers": sorted(set(general_blockers)),
        "route_gaps": sorted(set(route_gaps)),
        "warnings": sorted(set(warnings)),
        "rfi_has_award": False,
        "future_invitation_guaranteed": False,
        "authority": dict(AUTHORITY),
    }
    result["receipt_sha256"] = sha256(result)
    return result

def verify(source: dict, owner: dict, receipt: dict, *, trusted_now: datetime) -> bool:
    if not isinstance(receipt, dict):
        return False
    candidate = evaluate(source, owner, trusted_now=trusted_now)
    return canonical_bytes(candidate) == canonical_bytes(receipt)

def read_plain_file(path: str | Path, label: str) -> bytes:
    p = os.fspath(path)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(p, flags)
    except OSError as exc:
        raise PreflightError(f"{label} must be a readable ordinary non-symlink file") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise PreflightError(f"{label} must be an ordinary file")
        if st.st_size > MAX_BYTES:
            raise PreflightError(f"{label} exceeds size limit")
        chunks = []
        remaining = MAX_BYTES + 1
        while remaining:
            chunk = os.read(fd, min(131072, remaining))
            if not chunk:
                break
            chunks.append(chunk); remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > MAX_BYTES:
            raise PreflightError(f"{label} exceeds size limit")
        return raw
    finally:
        os.close(fd)

def publish_exclusive(path: str | Path, raw: bytes) -> None:
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise PreflightError("output bytes invalid or too large")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(os.fspath(path), flags, 0o600)
    except OSError as exc:
        raise PreflightError("refusing overwrite/symlink/non-ordinary output") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise PreflightError("output must be ordinary file")
        view = memoryview(raw)
        while view:
            n = os.write(fd, view)
            view = view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)

def _load_path(path: str, label: str) -> dict:
    return load_json_bytes(read_plain_file(path, label), label)

def _parse_now(value: str) -> datetime:
    return parse_utc(value, "trusted-now")

def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    cp = sub.add_parser("compile")
    cp.add_argument("--source", required=True)
    cp.add_argument("--owner", required=True)
    cp.add_argument("--trusted-now", required=True)
    cp.add_argument("--out")

    vp = sub.add_parser("verify")
    vp.add_argument("--source", required=True)
    vp.add_argument("--owner", required=True)
    vp.add_argument("--receipt", required=True)
    vp.add_argument("--trusted-now", required=True)

    args = parser.parse_args()
    source = _load_path(args.source, "source")
    owner = _load_path(args.owner, "owner")
    now = _parse_now(args.trusted_now)

    if args.command == "compile":
        receipt = evaluate(source, owner, trusted_now=now)
        raw = json.dumps(receipt, indent=2, sort_keys=True).encode("utf-8") + b"\n"
        if args.out:
            publish_exclusive(args.out, raw)
        else:
            os.write(1, raw)
        return 0 if receipt["state"] in {DIRECT_READY, PARTNER_READY} else 3

    receipt = _load_path(args.receipt, "receipt")
    ok = verify(source, owner, receipt, trusted_now=now)
    os.write(1, (json.dumps({"verified": ok}, sort_keys=True) + "\n").encode("utf-8"))
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
