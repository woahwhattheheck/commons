#!/usr/bin/env python3
"""Fail-closed internal readiness authority for WRF 5417. No network/submission actions."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import stat
import sys
from decimal import Decimal, InvalidOperation, ROUND_CEILING

READY = "READY_FOR_AUTHORIZED_SUBMITTER_REVIEW"
HOLD = "HOLD"
ALLOWED = {"PROVEN", "PARTNER_CURABLE", "MISSING", "NOT_APPLICABLE", "HOLD"}
CONTRACT_VERSION = "WRF-5417-READINESS/v2"
OPPORTUNITY_ID = "WRF-5417"
DEADLINE_UTC = dt.datetime(2026, 9, 14, 21, 0, 0, tzinfo=dt.timezone.utc)
MAX_JSON_BYTES = 1_048_576
REQUIRED_HARD_GATES = frozenset({
    "organization_my_portal_account",
    "applying_entity_identity",
    "w9_or_applicable_entity_tax_document",
    "financial_statements_packet",
    "financial_grant_management_capabilities_form",
    "certification_and_assurance_form",
    "pi_and_copi_identified",
    "current_and_pending_forms",
    "team_qualification_evidence",
    "consenting_multi_site_utility_participation",
    "water_wastewater_domain_lead",
    "computer_vision_lead",
    "cost_share_commitments",
    "technical_proposal_components",
    "legal_ip_pfa_review",
    "final_pdf_and_portal_qa",
})
PINNED_AUTHORITY_ROOTS = frozenset()

CONTRACT = {
    "version": CONTRACT_VERSION,
    "opportunity_id": OPPORTUNITY_ID,
    "deadline_utc": "2026-09-14T21:00:00Z",
    "deadline_source_text": "September 14, 2026, 3:00 PM Mountain Time",
    "deadline_zone": "America/Denver",
    "deadline_portal_offset_label": "GMT-07:00",
    "wrf_request_ceiling_usd": 300000,
    "minimum_applicant_contribution_fraction": "0.33",
    "reimbursed_indirect_ceiling_fraction": "0.15",
    "required_hard_gates": sorted(REQUIRED_HARD_GATES),
    "required_budget_authorities": ["budget_terms", "budget_workbook", "budget_narrative"],
    "utility_min_distinct_sites": 2,
    "utility_required_sectors": ["drinking_water", "wastewater"],
    "requirements_git_blob_sha1": "ef4ca5d4a91bea0f03054ad879409fba0083c36d",
}

_TOP_KEYS = {
    "schema_version", "opportunity_id", "owner", "intended_submission_state", "deadline",
    "budget", "hard_gates", "utility_participants", "team_members",
    "third_party_contributions", "submission_authority", "notes",
}
_DEADLINE_KEYS = {"local", "iana_zone", "source_text", "portal_offset_label", "deadline_offset_recheck"}
_BUDGET_KEYS = {
    "wrf_request_usd", "documented_eligible_contribution_usd", "reimbursed_indirect_cost_usd",
    "budget_terms", "budget_workbook", "budget_narrative",
}
_GATE_KEYS = {"status", "evidence"}
_AUTHORITY_KEYS = {"schema_version", "opportunity_id", "generation", "captured_at", "records"}
_RECORD_KEYS = {
    "record_id", "opportunity_id", "gate", "subject", "evidence_type", "source_id",
    "source_generation", "source_sha256", "claim_sha256", "verified_at", "expires_at",
}
_UTILITY_KEYS = {"utility_ref", "site_ref", "sector", "consent_status", "consent_evidence"}
_THIRD_PARTY_KEYS = {
    "contributor_ref", "contribution_type", "value_usd", "commitment_status", "commitment_evidence",
}
_SUBMISSION_AUTH_KEYS = {"carrier_may_submit", "authorized_submitter", "final_submission_status"}
_HEX = frozenset("0123456789abcdef")


def _plain(v):
    return isinstance(v, dict)


def _exact_keys(value, expected, label, reasons):
    if not _plain(value):
        reasons.append(f"{label}: object required")
        return False
    actual = set(value)
    if actual != set(expected):
        missing = sorted(set(expected) - actual)
        extra = sorted(actual - set(expected))
        if missing:
            reasons.append(f"{label}: missing keys {','.join(missing)}")
        if extra:
            reasons.append(f"{label}: unknown keys {','.join(extra)}")
        return False
    return True


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_json(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


CONTRACT_DIGEST = sha256_json(CONTRACT)


def _strict_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def parse_strict_json_bytes(data):
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("bytes required")
    if len(data) > MAX_JSON_BYTES:
        raise ValueError("JSON input exceeds hard byte cap")
    text = bytes(data).decode("utf-8")
    return json.loads(
        text,
        object_pairs_hook=_strict_pairs,
        parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"invalid JSON constant: {x}")),
    )


def read_bounded_regular_file(path, max_bytes=MAX_JSON_BYTES):
    path = os.fspath(path)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("input must be a regular file")
        if before.st_size > max_bytes:
            raise ValueError("input exceeds hard byte cap")
        chunks, total = [], 0
        while True:
            remaining = max_bytes + 1 - total
            if remaining <= 0:
                raise ValueError("input exceeds hard byte cap")
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise ValueError("input exceeds hard byte cap")
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise ValueError("input descriptor generation changed")
        if after.st_size != total:
            raise ValueError("input changed during read")
        return b"".join(chunks)
    finally:
        os.close(fd)


def _decimal(value, label, reasons, *, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        reasons.append(f"{label}: finite number required")
        return None
    if isinstance(value, float) and not math.isfinite(value):
        reasons.append(f"{label}: finite number required")
        return None
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, ValueError):
        reasons.append(f"{label}: finite number required")
        return None
    if minimum is not None and dec < Decimal(str(minimum)):
        reasons.append(f"{label}: below minimum")
    if maximum is not None and dec > Decimal(str(maximum)):
        reasons.append(f"{label}: above maximum")
    return dec


def _timestamp(value, label, reasons):
    if not isinstance(value, str):
        reasons.append(f"{label}: timestamp required")
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        reasons.append(f"{label}: invalid timestamp")
        return None
    if parsed.tzinfo is None:
        reasons.append(f"{label}: timezone required")
        return None
    return parsed.astimezone(dt.timezone.utc)


def _valid_sha256(value):
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX


def _record_body(record):
    return {k: record[k] for k in sorted(_RECORD_KEYS - {"record_id"})}


def record_id_for(record):
    return sha256_json(_record_body(record))


def authority_bundle_digest(bundle):
    return sha256_json(bundle)


def _gate_claim(gate, subject="applicant"):
    return sha256_json({
        "opportunity_id": OPPORTUNITY_ID,
        "gate": gate,
        "subject": subject,
        "status": "PROVEN",
    })


def _budget_claim(budget):
    return sha256_json({
        "opportunity_id": OPPORTUNITY_ID,
        "wrf_request_usd": budget.get("wrf_request_usd"),
        "documented_eligible_contribution_usd": budget.get("documented_eligible_contribution_usd"),
        "reimbursed_indirect_cost_usd": budget.get("reimbursed_indirect_cost_usd"),
    })


def _utility_claim(p):
    return sha256_json({
        "opportunity_id": OPPORTUNITY_ID,
        "gate": "utility_consent",
        "utility_ref": p.get("utility_ref"),
        "site_ref": p.get("site_ref"),
        "sector": p.get("sector"),
        "consent_status": "PROVEN",
    })


def _third_party_claim(p):
    return sha256_json({
        "opportunity_id": OPPORTUNITY_ID,
        "gate": "third_party_contribution",
        "contributor_ref": p.get("contributor_ref"),
        "contribution_type": p.get("contribution_type"),
        "value_usd": p.get("value_usd"),
        "commitment_status": "PROVEN",
    })


def _authority_index(bundle, now, reasons):
    if not _plain(bundle):
        reasons.append("trusted authority bundle missing")
        return {}, None
    if not _exact_keys(bundle, _AUTHORITY_KEYS, "authority_bundle", reasons):
        return {}, None
    if bundle.get("schema_version") != 1:
        reasons.append("authority_bundle: schema_version must be 1")
    if bundle.get("opportunity_id") != OPPORTUNITY_ID:
        reasons.append("authority_bundle: wrong opportunity_id")
    if not isinstance(bundle.get("generation"), str) or not bundle["generation"].strip():
        reasons.append("authority_bundle: generation required")
    captured = _timestamp(bundle.get("captured_at"), "authority_bundle.captured_at", reasons)
    if captured and captured > now:
        reasons.append("authority_bundle: captured_at is from future")
    records = bundle.get("records")
    if not isinstance(records, list):
        reasons.append("authority_bundle: records array required")
        return {}, None
    digest = authority_bundle_digest(bundle)
    if digest not in PINNED_AUTHORITY_ROOTS:
        reasons.append("authority_bundle: root not pinned by reviewed verifier source")
    index, source_identities = {}, {}
    for i, record in enumerate(records):
        label = f"authority_bundle.records[{i}]"
        if not _exact_keys(record, _RECORD_KEYS, label, reasons):
            continue
        rid = record.get("record_id")
        if not _valid_sha256(rid) or rid != record_id_for(record):
            reasons.append(f"{label}: invalid record_id")
            continue
        if rid in index:
            reasons.append(f"{label}: duplicate record_id")
            continue
        if record.get("opportunity_id") != OPPORTUNITY_ID:
            reasons.append(f"{label}: wrong opportunity_id")
        if not all(isinstance(record.get(k), str) and record[k].strip() for k in (
            "gate", "subject", "evidence_type", "source_id", "source_generation"
        )):
            reasons.append(f"{label}: typed identity fields required")
        if not _valid_sha256(record.get("source_sha256")):
            reasons.append(f"{label}: invalid source_sha256")
        if not _valid_sha256(record.get("claim_sha256")):
            reasons.append(f"{label}: invalid claim_sha256")
        verified = _timestamp(record.get("verified_at"), f"{label}.verified_at", reasons)
        expires = _timestamp(record.get("expires_at"), f"{label}.expires_at", reasons)
        if verified and verified > now:
            reasons.append(f"{label}: verified_at is from future")
        if expires and expires <= now:
            reasons.append(f"{label}: authority expired")
        source_identity = (record.get("source_id"), record.get("source_generation"), record.get("source_sha256"))
        if source_identity in source_identities:
            reasons.append(f"{label}: source evidence reused by {source_identities[source_identity]}")
        else:
            source_identities[source_identity] = rid
        index[rid] = record
    return index, digest


def _entry(entry, label, reasons):
    if not _exact_keys(entry, _GATE_KEYS, label, reasons):
        return None, []
    status = entry.get("status")
    if status not in ALLOWED:
        reasons.append(f"{label}: invalid status")
    refs = entry.get("evidence")
    if not isinstance(refs, list) or any(not _valid_sha256(x) for x in refs):
        reasons.append(f"{label}: evidence must be record-id array")
        refs = []
    if len(refs) != len(set(refs)):
        reasons.append(f"{label}: duplicate evidence reference")
    return status, refs


def _require_authority(entry, label, gate, subject, expected_claim, authority, used, reasons):
    status, refs = _entry(entry, label, reasons)
    if status != "PROVEN":
        reasons.append(f"{label}: {status}")
        return
    if not refs:
        reasons.append(f"{label}: PROVEN without trusted evidence")
        return
    valid = False
    for rid in refs:
        if rid in used:
            reasons.append(f"{label}: authority record reused across claims")
            continue
        used.add(rid)
        record = authority.get(rid)
        if record is None:
            reasons.append(f"{label}: authority record missing")
            continue
        if record.get("gate") != gate:
            reasons.append(f"{label}: authority gate mismatch")
            continue
        if record.get("subject") != subject:
            reasons.append(f"{label}: authority subject mismatch")
            continue
        if record.get("claim_sha256") != expected_claim:
            reasons.append(f"{label}: authority claim digest mismatch")
            continue
        valid = True
    if not valid:
        reasons.append(f"{label}: no matching trusted authority record")


def _validate_contract_fields(manifest, reasons):
    if manifest.get("opportunity_id") != OPPORTUNITY_ID:
        reasons.append("wrong opportunity_id")
    if manifest.get("schema_version") != 2:
        reasons.append("schema_version must be 2")
    deadline = manifest.get("deadline")
    if not _exact_keys(deadline, _DEADLINE_KEYS, "deadline", reasons):
        return
    exact_deadline = {
        "local": "2026-09-14T15:00:00",
        "iana_zone": "America/Denver",
        "source_text": "3:00 PM Mountain Time on Monday, September 14, 2026",
        "portal_offset_label": "GMT-07:00",
    }
    for key, expected in exact_deadline.items():
        if deadline.get(key) != expected:
            reasons.append(f"deadline.{key}: candidate cannot override controlling contract")


def evaluate(manifest, authority_bundle=None, now=None):
    reasons = []
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(dt.timezone.utc)

    _exact_keys(manifest, _TOP_KEYS, "manifest", reasons)
    _validate_contract_fields(manifest, reasons)

    intended = manifest.get("intended_submission_state")
    if intended not in {HOLD, READY}:
        reasons.append("invalid intended_submission_state")
    elif intended == HOLD:
        reasons.append("owner intent remains HOLD")

    if now >= DEADLINE_UTC:
        reasons.append("deadline expired")

    authority, authority_digest = _authority_index(authority_bundle, now, reasons)
    used = set()

    deadline = manifest.get("deadline") if _plain(manifest.get("deadline")) else {}
    _require_authority(
        deadline.get("deadline_offset_recheck"),
        "deadline.deadline_offset_recheck",
        "deadline_offset_recheck",
        OPPORTUNITY_ID,
        _gate_claim("deadline_offset_recheck", OPPORTUNITY_ID),
        authority, used, reasons,
    )

    gates = manifest.get("hard_gates")
    if not _plain(gates):
        reasons.append("hard_gates: object required")
        gates = {}
    actual_gate_names = set(gates)
    missing = sorted(REQUIRED_HARD_GATES - actual_gate_names)
    extra = sorted(actual_gate_names - REQUIRED_HARD_GATES)
    if missing:
        reasons.append("hard_gates: missing required gates " + ",".join(missing))
    if extra:
        reasons.append("hard_gates: unknown gates " + ",".join(extra))
    for name in sorted(REQUIRED_HARD_GATES):
        _require_authority(
            gates.get(name), f"hard_gates.{name}", name, "applicant",
            _gate_claim(name), authority, used, reasons,
        )

    budget = manifest.get("budget")
    if not _exact_keys(budget, _BUDGET_KEYS, "budget", reasons):
        budget = budget if _plain(budget) else {}
    req = _decimal(budget.get("wrf_request_usd"), "budget.wrf_request_usd", reasons, minimum="0.01", maximum="300000")
    contrib = _decimal(
        budget.get("documented_eligible_contribution_usd"),
        "budget.documented_eligible_contribution_usd", reasons, minimum="0",
    )
    indirect = _decimal(
        budget.get("reimbursed_indirect_cost_usd"),
        "budget.reimbursed_indirect_cost_usd", reasons, minimum="0",
    )
    if req is not None and contrib is not None:
        required = (req * Decimal("0.33")).quantize(Decimal("0.01"), rounding=ROUND_CEILING)
        if contrib < required:
            reasons.append(f"contribution below required {required:.2f}")
    if req is not None and indirect is not None:
        ceiling = (req * Decimal("0.15")).quantize(Decimal("0.01"))
        if indirect > ceiling:
            reasons.append(f"reimbursed indirect cost exceeds 15% ceiling {ceiling:.2f}")
    _require_authority(
        budget.get("budget_terms"), "budget.budget_terms", "budget_terms", "applicant",
        _budget_claim(budget), authority, used, reasons,
    )
    for gate in ("budget_workbook", "budget_narrative"):
        _require_authority(
            budget.get(gate), f"budget.{gate}", gate, "applicant",
            _gate_claim(gate), authority, used, reasons,
        )

    participants = manifest.get("utility_participants")
    if not isinstance(participants, list):
        reasons.append("utility_participants: array required")
        participants = []
    sectors, sites = set(), set()
    seen_participants = set()
    if len(participants) < 2:
        reasons.append("at least two distinct consenting utility sites required")
    for idx, p in enumerate(participants):
        label = f"utility_participants[{idx}]"
        if not _exact_keys(p, _UTILITY_KEYS, label, reasons):
            continue
        utility_ref, site_ref = p.get("utility_ref"), p.get("site_ref")
        if not isinstance(utility_ref, str) or not utility_ref.strip() or not isinstance(site_ref, str) or not site_ref.strip():
            reasons.append(f"{label}: utility_ref/site_ref required")
            continue
        key = (utility_ref, site_ref)
        if key in seen_participants:
            reasons.append(f"{label}: duplicate utility/site")
        seen_participants.add(key)
        sites.add(site_ref)
        sector = p.get("sector")
        if sector not in {"drinking_water", "wastewater"}:
            reasons.append(f"{label}: sector must be drinking_water or wastewater")
        else:
            sectors.add(sector)
        _require_authority(
            {"status": p.get("consent_status"), "evidence": p.get("consent_evidence")},
            label + ".consent", "utility_consent", f"{utility_ref}:{site_ref}",
            _utility_claim(p), authority, used, reasons,
        )
    if len(sites) < 2:
        reasons.append("multi-site utility requirement not proven")
    if sectors != {"drinking_water", "wastewater"}:
        reasons.append("proven utilities must span drinking_water and wastewater")

    contributions = manifest.get("third_party_contributions")
    if not isinstance(contributions, list):
        reasons.append("third_party_contributions: array required")
        contributions = []
    for idx, p in enumerate(contributions):
        label = f"third_party_contributions[{idx}]"
        if not _exact_keys(p, _THIRD_PARTY_KEYS, label, reasons):
            continue
        ref = p.get("contributor_ref")
        if not isinstance(ref, str) or not ref.strip():
            reasons.append(f"{label}: contributor_ref required")
            continue
        if p.get("contribution_type") not in {"cash", "in_kind"}:
            reasons.append(f"{label}: invalid contribution_type")
        _decimal(p.get("value_usd"), f"{label}.value_usd", reasons, minimum="0.01")
        _require_authority(
            {"status": p.get("commitment_status"), "evidence": p.get("commitment_evidence")},
            label + ".commitment", "third_party_contribution", ref,
            _third_party_claim(p), authority, used, reasons,
        )

    if not isinstance(manifest.get("team_members"), list):
        reasons.append("team_members: array required")
    notes = manifest.get("notes")
    if not isinstance(notes, list) or any(not isinstance(x, str) for x in notes):
        reasons.append("notes: string array required")

    sub = manifest.get("submission_authority")
    if _exact_keys(sub, _SUBMISSION_AUTH_KEYS, "submission_authority", reasons):
        if sub.get("carrier_may_submit") is not False:
            reasons.append("carrier_may_submit must remain false")
        if sub.get("authorized_submitter") is not None:
            reasons.append("authorized_submitter must remain null in public carrier")
        if sub.get("final_submission_status") != "NOT_AUTHORIZED":
            reasons.append("final_submission_status must remain NOT_AUTHORIZED")

    state = READY if not reasons else HOLD
    if intended == READY and reasons:
        reasons.insert(0, "READY spoofed while blockers remain")
    receipt = {
        "schema_version": 1,
        "contract_version": CONTRACT_VERSION,
        "contract_sha256": CONTRACT_DIGEST,
        "manifest_sha256": sha256_json(manifest),
        "authority_bundle_sha256": authority_digest,
        "authority_generation": authority_bundle.get("generation") if _plain(authority_bundle) else None,
        "evaluated_at": now.isoformat().replace("+00:00", "Z"),
        "state": state,
        "reasons": list(reasons),
        "carrier_may_submit": False,
    }
    receipt["receipt_sha256"] = sha256_json(receipt)
    return {"state": state, "reasons": reasons, "receipt": receipt}


def check(manifest, authority_bundle=None, now=None):
    result = evaluate(manifest, authority_bundle, now)
    return result["state"], result["reasons"]


def main():
    if len(sys.argv) not in {2, 3}:
        print("usage: validate_readiness.py MANIFEST.json [AUTHORITY_BUNDLE.json]", file=sys.stderr)
        return 2
    try:
        manifest = parse_strict_json_bytes(read_bounded_regular_file(sys.argv[1]))
        authority = None
        if len(sys.argv) == 3:
            authority = parse_strict_json_bytes(read_bounded_regular_file(sys.argv[2]))
        result = evaluate(manifest, authority)
    except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"state": HOLD, "reasons": [f"ingress: {exc}"]}, indent=2))
        return 3
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["state"] == READY else 3


if __name__ == "__main__":
    raise SystemExit(main())
