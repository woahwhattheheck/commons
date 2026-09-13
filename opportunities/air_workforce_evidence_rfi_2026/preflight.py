#!/usr/bin/env python3
"""Fail-closed AIR workforce-AI RFI qualification gate. Never submits anything."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

SOURCE_SCHEMA = "air.workforce_ai_rfi.source_snapshot/v1"
OWNER_SCHEMA = "air.workforce_ai_rfi.owner_inputs/v1"
RECEIPT_SCHEMA = "air.workforce_ai_rfi.preflight_receipt/v1"
READY = "READY_FOR_OWNER_SUBMISSION_REVIEW"
OWNER_HOLD = "OWNER_INPUT_REQUIRED"
PARTNER_REQUIRED = "PARTNER_REQUIRED"
SOURCE_CUSTODY_REQUIRED = "SOURCE_CUSTODY_REQUIRED"
SOURCE_REFRESH_REQUIRED = "SOURCE_REFRESH_REQUIRED"
DEADLINE_PASSED = "DEADLINE_PASSED"
MAX_SOURCE_AGE = timedelta(days=7)
MAX_SAFE_INT = 2**53 - 1
Maturity = {"Concept", "Prototype", "Pilot", "Deployed solution"}
PLACEHOLDER = re.compile(r"(?:OWNER_INPUT_REQUIRED|PARTNER_INPUT_REQUIRED|\bTBD\b|\bTODO\b|<[^>]+>|\[[A-Z_]+\])", re.I)
SHA256 = re.compile(r"[0-9a-f]{64}")
URL = re.compile(r"https://[^\s]+")
OFFICIAL_URLS = [
    "https://www.air.org/sites/default/files/2026-08/AIR-RFI-Building-an-Evidence-Network-for-AI-in-Workforce-Systems.pdf",
    "https://www.air.org/resource/blog-post/we-want-hear-you-how-can-ai-help-workers-prepare-adapt-and-thrive",
    "https://www.air.org/artificial-intelligence-air",
]
FOCUS_AREAS = [
    "Skill Training and Development",
    "Career Navigation and Job Placement",
    "Basic Needs",
    "Personalized Support",
]
RESPONSIBLE_AI_DIMENSIONS = ["fairness", "bias", "transparency", "privacy", "governance"]
SOURCE_AUTHORITY_KEYS = {
    "award_assertion_authorized",
    "contact_authorized",
    "future_funding_assertion_authorized",
    "participant_data_access_authorized",
    "submission_authorized",
}
PROMPT_LIMITS = {
    "organizational_background": 200,
    "innovation_overview": 300,
    "workforce_challenge": 200,
    "learning_questions": 200,
    "population_of_focus": 100,
    "technical_approach": 300,
    "early_results": 200,
    "responsible_ai": 200,
    "air_partnership": 150,
}
AUTHORITY = {k: False for k in (
    "air_contact_authorized",
    "partner_contact_authorized",
    "submittable_action_authorized",
    "external_submission_authorized",
    "participant_data_access_authorized",
    "outcome_claim_authorized",
    "pricing_or_contract_commitment_authorized",
    "signature_authorized",
    "spend_authorized",
    "award_or_revenue_claim_authorized",
)}

class PreflightError(ValueError):
    pass

def _bad(v: str):
    raise PreflightError(f"non-finite JSON number {v!r} is forbidden")

def _pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise PreflightError(f"duplicate JSON key: {k}")
        out[k] = v
    return out

def load_json_bytes(raw: bytes, label: str):
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PreflightError(f"{label} must be UTF-8") from exc
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_bad)
    except PreflightError:
        raise
    except json.JSONDecodeError as exc:
        raise PreflightError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise PreflightError(f"{label} must be an object")
    return value

def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else canonical_bytes(value)).hexdigest()

def parse_utc(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise PreflightError(f"{label} must be canonical UTC YYYY-MM-DDTHH:MM:SSZ")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise PreflightError(f"{label} is not a valid UTC timestamp") from exc

def trusted_time(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise PreflightError("trusted_now must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0)

def _text(value):
    return isinstance(value, str) and bool(value.strip()) and not PLACEHOLDER.search(value)

def _int(value):
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= MAX_SAFE_INT

def _words(text):
    return len(re.findall(r"\b\w+(?:[-’']\w+)*\b", text or "", flags=re.UNICODE))

def _source(source):
    if source.get("schema") != SOURCE_SCHEMA:
        raise PreflightError("unsupported source schema")
    if source.get("issuer") != "American Institutes for Research":
        raise PreflightError("source issuer mismatch")
    if source.get("rfi_title") != "Building an Evidence Network for Artificial Intelligence (AI) in Workforce Systems":
        raise PreflightError("RFI identity mismatch")
    parse_utc(source.get("checked_at"), "source.checked_at")
    parse_utc(source.get("due_at_utc"), "source.due_at_utc")
    if source.get("no_award_at_rfi_stage") is not True or source.get("future_funding_guaranteed") is not False:
        raise PreflightError("source must preserve no-award/no-guarantee boundary")
    if source.get("submission_method") != "Submittable":
        raise PreflightError("source submission method drift")
    urls = source.get("official_urls")
    if urls != OFFICIAL_URLS or not all(URL.fullmatch(x) for x in urls):
        raise PreflightError("official_urls must match the controlling AIR source set")
    focus = source.get("focus_areas")
    if focus != FOCUS_AREAS:
        raise PreflightError("focus_areas drift from the controlling AIR RFI")
    if source.get("allowed_maturity_levels") != ["Concept", "Prototype", "Pilot", "Deployed solution"]:
        raise PreflightError("maturity levels drift from the controlling AIR RFI")
    if source.get("responsible_ai_dimensions") != RESPONSIBLE_AI_DIMENSIONS:
        raise PreflightError("responsible-AI dimensions drift from the controlling AIR RFI")
    prompts = source.get("prompt_word_limits")
    if not isinstance(prompts, dict) or prompts != PROMPT_LIMITS:
        raise PreflightError("prompt word limits drift")
    pdf = source.get("rfi_pdf_sha256")
    acquired = source.get("rfi_pdf_bytes_acquired")
    if acquired not in (True, False):
        raise PreflightError("rfi_pdf_bytes_acquired must be boolean")
    if pdf is not None and (not isinstance(pdf, str) or not SHA256.fullmatch(pdf)):
        raise PreflightError("rfi_pdf_sha256 must be null or lowercase SHA-256")
    if acquired is True and pdf is None:
        raise PreflightError("raw PDF custody cannot be claimed without its digest")
    if acquired is False and pdf is not None:
        raise PreflightError("raw PDF digest cannot be asserted when bytes were not acquired")
    extraction = source.get("source_extraction_receipt")
    if not isinstance(extraction, dict):
        raise PreflightError("source_extraction_receipt malformed")
    if extraction.get("raw_byte_hash_available") is not acquired:
        raise PreflightError("source extraction receipt raw-byte state conflicts with custody state")
    pages = extraction.get("web_pdf_pages_observed")
    if not _int(pages) or pages != 10 or not _text(extraction.get("information_requested_pages")):
        raise PreflightError("source extraction receipt page evidence malformed")
    chars = source.get("respondent_characteristics")
    if not isinstance(chars, list) or len(chars) < 3 or not all(_text(x) for x in chars):
        raise PreflightError("respondent characteristics malformed")
    if not isinstance(source.get("review_criteria"), list) or len(source["review_criteria"]) < 5:
        raise PreflightError("review criteria incomplete")
    authority = source.get("authority")
    if not isinstance(authority, dict) or set(authority) != SOURCE_AUTHORITY_KEYS or any(v is not False for v in authority.values()):
        raise PreflightError("source authority must contain the exact false-only authority boundary")

def _owner(owner):
    if owner.get("schema") != OWNER_SCHEMA:
        raise PreflightError("unsupported owner-input schema")
    required_types = {
        "route": str,
        "project_title": str,
        "contact": dict,
        "focus_areas": list,
        "maturity": str,
        "population": dict,
        "drafts": dict,
        "direct_workforce_track_record": list,
        "partner": dict,
        "responsible_ai_controls": dict,
        "evidence_design": dict,
        "early_results_evidence": list,
    }
    for key, typ in required_types.items():
        if not isinstance(owner.get(key), typ):
            raise PreflightError(f"owner.{key} must be {typ.__name__}")
    if not isinstance(owner.get("early_results_claimed"), bool):
        raise PreflightError("early_results_claimed must be boolean")

def _record_complete(row, keys):
    return isinstance(row, dict) and all(_text(row.get(k)) for k in keys)

def _track_record(rows, prefix, blockers):
    good = []
    for i, row in enumerate(rows):
        if not _record_complete(row, ("record_id", "population", "workforce_service", "period", "evidence_ref", "evidence_sha256")):
            blockers.append(f"{prefix}_TRACK_RECORD_{i}_INCOMPLETE")
            continue
        if not SHA256.fullmatch(row["evidence_sha256"]):
            blockers.append(f"{prefix}_TRACK_RECORD_{i}_BAD_DIGEST")
            continue
        good.append(row)
    ids = [r["record_id"] for r in good]
    if len(ids) != len(set(ids)):
        blockers.append(f"{prefix}_TRACK_RECORD_IDS_NOT_UNIQUE")
    return good

def evaluate(source, owner, *, trusted_now):
    _source(source)
    _owner(owner)
    now = trusted_time(trusted_now)
    checked = parse_utc(source["checked_at"], "source.checked_at")
    due = parse_utc(source["due_at_utc"], "source.due_at_utc")
    if checked > now:
        raise PreflightError("source checked_at cannot be in the future")

    blockers = []
    warnings = []
    route = owner["route"]
    partner_gap = False

    if source["rfi_pdf_sha256"] is None:
        blockers.append("RAW_RFI_PDF_SHA256_REQUIRED")
    if now - checked > MAX_SOURCE_AGE:
        blockers.append("SOURCE_SNAPSHOT_OLDER_THAN_7_DAYS")
    if now > due:
        blockers.append("RFI_DEADLINE_PASSED")

    if route not in {"DIRECT_RFI", "PARTNER_RFI", "UNDECIDED"}:
        blockers.append("ROUTE_INVALID")
    elif route == "UNDECIDED":
        blockers.append("ROUTE_SELECTION_REQUIRED")

    if not _text(owner["project_title"]):
        blockers.append("PROJECT_TITLE_REQUIRED")

    contact = owner["contact"]
    for key in ("name", "title", "organization", "email", "phone"):
        if not _text(contact.get(key)):
            blockers.append(f"CONTACT_{key.upper()}_REQUIRED")

    selected = owner["focus_areas"]
    if not selected:
        blockers.append("SELECT_AT_LEAST_ONE_FOCUS_AREA")
    elif len(selected) != len(set(selected)):
        blockers.append("DUPLICATE_FOCUS_AREA")
    unknown = sorted(str(x) for x in selected if x not in source["focus_areas"])
    if unknown:
        blockers.append("UNKNOWN_FOCUS_AREA:" + ",".join(unknown))

    if owner["maturity"] not in Maturity:
        blockers.append("MATURITY_INVALID")

    pop = owner["population"]
    for key in ("description", "evidence_ref"):
        if not _text(pop.get(key)):
            blockers.append(f"POPULATION_{key.upper()}_REQUIRED")
    size = pop.get("estimated_size_2027_2028")
    if not _int(size) or size <= 0:
        blockers.append("POPULATION_2027_2028_SIZE_REQUIRED")

    drafts = owner["drafts"]
    if set(drafts) != set(PROMPT_LIMITS):
        blockers.append("DRAFT_PROMPT_SET_MUST_MATCH_RFI")
    for key, limit in PROMPT_LIMITS.items():
        text = drafts.get(key)
        if not _text(text):
            blockers.append(f"DRAFT_{key.upper()}_REQUIRED")
        elif _words(text) > limit:
            blockers.append(f"WORD_LIMIT_EXCEEDED:{key}:{_words(text)}>{limit}")

    direct = _track_record(owner["direct_workforce_track_record"], "DIRECT", blockers)
    partner = owner["partner"]
    partner_rows = partner.get("workforce_track_record") if isinstance(partner.get("workforce_track_record"), list) else []
    partner_good = _track_record(partner_rows, "PARTNER", blockers)
    if route == "DIRECT_RFI" and not direct:
        blockers.append("ESTABLISHED_DIRECT_WORKFORCE_TRACK_RECORD_NOT_EVIDENCED")
        partner_gap = True
    if route == "PARTNER_RFI":
        for key in ("organization", "role", "commitment_evidence_ref"):
            if not _text(partner.get(key)):
                blockers.append(f"PARTNER_{key.upper()}_REQUIRED")
                partner_gap = True
        if not partner_good:
            blockers.append("ESTABLISHED_PARTNER_WORKFORCE_TRACK_RECORD_NOT_EVIDENCED")
            partner_gap = True

    controls = owner["responsible_ai_controls"]
    for key in ("fairness", "bias", "transparency", "privacy", "governance"):
        if not _text(controls.get(key)):
            blockers.append(f"RESPONSIBLE_AI_{key.upper()}_REQUIRED")

    design = owner["evidence_design"]
    for key in ("outcomes", "comparison_design", "instrumentation", "worker_voice", "data_minimization", "human_oversight", "failure_modes", "interim_learning", "independent_evaluation_fit"):
        if not _text(design.get(key)):
            blockers.append(f"EVIDENCE_DESIGN_{key.upper()}_REQUIRED")

    ev = owner["early_results_evidence"]
    if owner["early_results_claimed"]:
        if not ev:
            blockers.append("EARLY_RESULTS_EVIDENCE_REQUIRED")
        for i, row in enumerate(ev):
            if not _record_complete(row, ("claim", "evidence_ref", "evidence_sha256")) or not SHA256.fullmatch(str(row.get("evidence_sha256", ""))):
                blockers.append(f"EARLY_RESULTS_EVIDENCE_{i}_INVALID")
    elif ev:
        blockers.append("EARLY_RESULTS_EVIDENCE_PRESENT_WHILE_CLAIM_FALSE")

    if owner.get("source_refresh_reviewed") is not True:
        blockers.append("SOURCE_REFRESH_REVIEW_REQUIRED")
    if owner.get("submission_boundary_reviewed") is not True:
        blockers.append("SUBMISSION_BOUNDARY_REVIEW_REQUIRED")

    if owner["maturity"] in {"Pilot", "Deployed solution"} and not owner["early_results_claimed"]:
        warnings.append("PILOT_OR_DEPLOYED_WITHOUT_EARLY_RESULTS_CLAIM")

    if now > due:
        state = DEADLINE_PASSED
    elif now - checked > MAX_SOURCE_AGE:
        state = SOURCE_REFRESH_REQUIRED
    elif source["rfi_pdf_sha256"] is None:
        state = SOURCE_CUSTODY_REQUIRED
    elif partner_gap:
        state = PARTNER_REQUIRED
    else:
        state = READY if not blockers else OWNER_HOLD

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "state": state,
        "evaluated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_snapshot_sha256": digest(source),
        "owner_input_sha256": digest(owner),
        "route": route,
        "focus_areas": list(selected),
        "direct_track_record_count": len(direct),
        "partner_track_record_count": len(partner_good),
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "authority": dict(AUTHORITY),
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt

def verify_receipt(receipt, source, owner, *, trusted_now):
    if not isinstance(receipt, dict) or receipt.get("schema") != RECEIPT_SCHEMA:
        return False
    candidate = evaluate(copy.deepcopy(source), copy.deepcopy(owner), trusted_now=trusted_now)
    return canonical_bytes(candidate) == canonical_bytes(receipt)

def parse_trusted_now(text):
    return parse_utc(text, "trusted-now")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--trusted-now", required=True)
    args = parser.parse_args()
    source = load_json_bytes(Path(args.source).read_bytes(), "source")
    owner = load_json_bytes(Path(args.owner).read_bytes(), "owner")
    print(json.dumps(evaluate(source, owner, trusted_now=parse_trusted_now(args.trusted_now)), indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
