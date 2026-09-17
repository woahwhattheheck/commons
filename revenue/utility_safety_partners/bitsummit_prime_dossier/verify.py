#!/usr/bin/env python3
"""Fail-closed verifier for the public-only BITSUMMIT prime qualification donor."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_STATUSES = {"SUPPORTED", "PARTNER_CONFIRMATION_REQUIRED", "OWNER_INPUT", "GAP"}
ALLOWED_SOURCE_CLASSES = {
    "ISSUER_DIRECTORY",
    "PARTNER_SELF",
    "PARTNER_POLICY",
    "PARTNER_ROUTE",
    "CONFLICTING_PUBLIC",
    "OWNER_REQUIRED",
    "NO_PUBLIC_SOURCE",
}
SELF_CLASSES = {"PARTNER_SELF"}
SUPPORTED_CLASSES = {"ISSUER_DIRECTORY", "PARTNER_POLICY", "PARTNER_ROUTE"}
EXPECTED_AUTHORITY = {
    "buyer_contact": False,
    "partner_contact": False,
    "pricing": False,
    "proposal_submission": False,
    "signature": False,
    "contract_acceptance": False,
    "award": False,
    "payment": False,
    "revenue_recognition": False,
}
EXPECTED_OPERATION = "USP-BITSUMMIT-PRIME-EVIDENCE-DOSSIER-20260916"
EXPECTED_OWNER = "Z-CitrineLedger-1442 (ZCL-1442) / GPT-5.6 Sol"
EXPECTED_CANONICAL_OWNER = "Z-LagrangeFathom-913840-B8R3 (ZLF-B8R3)"
EXPECTED_CANONICAL_ISSUE = "woahwhattheheck/commons#13850"
EXPECTED_HARD_GATES = (
    "entity_profile",
    "financial_information",
    "similar_client_references",
    "architecture_security_integration",
    "implementation_training_support",
    "data_modernization_ai_readiness_governance",
    "pricing",
    "partner_prime_route",
    "signatures_legal_delivery",
)
EXPECTED_STATUS_DEFINITIONS = {
    "SUPPORTED": "The narrow public fact is directly evidenced by an issuing/authoritative public source, or is only the existence of the partner's own published route/policy. It does not imply bid eligibility.",
    "PARTNER_CONFIRMATION_REQUIRED": "Public partner-authored material supports the claim directionally, but independent issuer/customer verification or direct partner confirmation is still required before proposal reliance.",
    "OWNER_INPUT": "The fact requires owner/legal/commercial/confidential-buyer input and must not be inferred from public marketing.",
    "GAP": "No adequate public evidence was found, or public sources conflict materially.",
}

# SUPPORTED partner-policy/route rows are intentionally narrow: they prove only that
# the published route/policy exists and what it states. Pin the authority-bearing
# wording so a later edit cannot widen one of these self-hosted rows into a claim of
# legal eligibility, security compliance, or bid readiness while still verifying.
SUPPORTED_ITEM_CONTRACTS = {
    "ibm_partner_directory_identity": {
        "gates": ["entity_profile", "partner_prime_route"],
        "claim": "IBM Partner Plus publicly lists BITSUMMIT Corp in Oakville, Ontario as a VAR/Reseller/Solution Provider and shows IBM resale authorizations.",
        "source_class": "ISSUER_DIRECTORY",
        "publisher": "IBM",
        "url": "https://www.ibm.com/partnerplus/directory/company/9669",
        "marketing_claim": False,
        "limitations": "Proves the IBM directory listing and partner relationship only; does not establish exact Ontario legal name, audited financials, Utility Safety eligibility, or Microsoft status.",
    },
    "privacy_policy_exists": {
        "gates": ["architecture_security_integration", "signatures_legal_delivery"],
        "claim": "BITSUMMIT publishes a versioned partner-program privacy policy (v1.0, updated 2026-03-18) covering collection, use, retention, security, rights and privacy complaints.",
        "source_class": "PARTNER_POLICY",
        "publisher": "BITSUMMIT",
        "url": "https://partner.bitsummit.com/privacy",
        "marketing_claim": False,
        "limitations": "Supports only that a public policy exists and what it states; not a security audit, SOC report, DPA, breach-history statement, or contractual privacy acceptance.",
    },
    "public_contact_route": {
        "gates": ["partner_prime_route"],
        "claim": "BITSUMMIT's current public contact page lists intake@bitsummit.com, +1 833 489 2262, an Oakville office and a Frisco, Texas office.",
        "source_class": "PARTNER_ROUTE",
        "publisher": "BITSUMMIT",
        "url": "https://www.bitsummit.com/contact",
        "marketing_claim": False,
        "limitations": "Route existence only. Existing Muse-cleared outreach is already sent and DNR-unless-reply; this dossier grants zero contact authority.",
    },
}


class VerificationError(ValueError):
    pass


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise VerificationError(msg)


def _parse_date(value: str, field: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise VerificationError(f"{field}: invalid ISO date") from exc


def verify_payload(payload: dict) -> dict:
    _require(isinstance(payload, dict), "root must be object")
    _require(payload.get("schema_version") == 1, "schema_version must be 1")
    _require(payload.get("operation") == EXPECTED_OPERATION, "operation mismatch")
    _require(payload.get("owner") == EXPECTED_OWNER, "owner mismatch")
    _require(payload.get("canonical_pursuit_owner") == EXPECTED_CANONICAL_OWNER, "canonical pursuit owner mismatch")
    _require(payload.get("canonical_issue") == EXPECTED_CANONICAL_ISSUE, "canonical issue mismatch")
    _require(payload.get("public_only") is True, "public_only must be true")
    _require(payload.get("authority") == EXPECTED_AUTHORITY, "authority ceiling mismatch")
    _require(payload.get("status_definitions") == EXPECTED_STATUS_DEFINITIONS, "status definitions mismatch")

    hard_gates = payload.get("hard_gate_categories")
    _require(isinstance(hard_gates, list), "hard_gate_categories must be list")
    _require(tuple(hard_gates) == EXPECTED_HARD_GATES, "hard gate taxonomy mismatch")
    hard_gate_set = set(EXPECTED_HARD_GATES)

    as_of = _parse_date(payload.get("as_of"), "as_of")
    items = payload.get("items")
    _require(isinstance(items, list) and items, "items must be non-empty list")
    seen = set()
    covered_gates = set()
    counts = {s: 0 for s in sorted(ALLOWED_STATUSES)}

    for idx, item in enumerate(items):
        pfx = f"items[{idx}]"
        _require(isinstance(item, dict), f"{pfx}: must be object")
        item_id = item.get("id")
        _require(isinstance(item_id, str) and item_id, f"{pfx}: id required")
        _require(item_id not in seen, f"{pfx}: duplicate id {item_id}")
        seen.add(item_id)
        status = item.get("status")
        source_class = item.get("source_class")
        _require(status in ALLOWED_STATUSES, f"{item_id}: bad status")
        _require(source_class in ALLOWED_SOURCE_CLASSES, f"{item_id}: bad source_class")
        counts[status] += 1

        gates = item.get("gates")
        _require(isinstance(gates, list) and gates and all(isinstance(g, str) and g for g in gates), f"{item_id}: gates required")
        _require(len(gates) == len(set(gates)), f"{item_id}: duplicate gate")
        _require(set(gates) <= hard_gate_set, f"{item_id}: unknown hard gate")
        covered_gates.update(gates)
        _require(isinstance(item.get("claim"), str) and item["claim"].strip(), f"{item_id}: claim required")
        _require(isinstance(item.get("limitations"), str) and item["limitations"].strip(), f"{item_id}: limitations required")
        _require(type(item.get("marketing_claim")) is bool, f"{item_id}: marketing_claim must be bool")

        observed = _parse_date(item.get("observed_at"), f"{item_id}.observed_at")
        _require(observed <= as_of, f"{item_id}: observed_at after as_of")
        max_age = item.get("max_age_days")
        _require(type(max_age) is int and max_age >= 0, f"{item_id}: max_age_days must be nonnegative int")
        if source_class not in {"OWNER_REQUIRED", "NO_PUBLIC_SOURCE"}:
            _require((as_of - observed).days <= max_age, f"{item_id}: stale evidence")

        url = item.get("url")
        if source_class in {"OWNER_REQUIRED", "NO_PUBLIC_SOURCE"}:
            _require(url is None, f"{item_id}: owner/gap source must not invent URL")
        else:
            _require(isinstance(url, str) and url.startswith("https://"), f"{item_id}: https source URL required")
            parsed = urlparse(url)
            _require(bool(parsed.netloc), f"{item_id}: source URL host required")

        if status == "SUPPORTED":
            _require(source_class in SUPPORTED_CLASSES, f"{item_id}: SUPPORTED requires issuer/policy/route source")
            _require(item.get("marketing_claim") is False, f"{item_id}: marketing-only claim cannot be SUPPORTED")
            contract = SUPPORTED_ITEM_CONTRACTS.get(item_id)
            _require(contract is not None, f"{item_id}: unrecognized SUPPORTED item")
            for field, expected in contract.items():
                _require(item.get(field) == expected, f"{item_id}: SUPPORTED {field} contract mismatch")
        if source_class in SELF_CLASSES:
            _require(status != "SUPPORTED", f"{item_id}: partner self-claim cannot be SUPPORTED")
        if status == "OWNER_INPUT":
            _require(source_class == "OWNER_REQUIRED", f"{item_id}: OWNER_INPUT requires OWNER_REQUIRED")
        if source_class == "NO_PUBLIC_SOURCE":
            _require(status == "GAP", f"{item_id}: NO_PUBLIC_SOURCE must be GAP")
        if source_class == "CONFLICTING_PUBLIC":
            _require(status == "GAP", f"{item_id}: conflicting public evidence must be GAP")

        lower = (item["claim"] + " " + item["limitations"]).lower()
        if "iso/iec 42001" in lower or "iso 42001" in lower:
            _require("certified" not in item["claim"].lower(), f"{item_id}: ISO 42001 certification overclaim")
        if "soc 2" in lower or "iso 27001" in lower:
            if source_class == "PARTNER_SELF":
                _require(status == "PARTNER_CONFIRMATION_REQUIRED", f"{item_id}: self-published assurance claim needs confirmation")

    _require(covered_gates == hard_gate_set, "every hard gate must be represented by evidence")
    _require(set(SUPPORTED_ITEM_CONTRACTS) <= seen, "locked SUPPORTED evidence item missing")
    _require(counts["SUPPORTED"] > 0, "at least one narrow supported public fact required")
    _require(counts["PARTNER_CONFIRMATION_REQUIRED"] > 0, "partner confirmation bucket required")
    _require(counts["OWNER_INPUT"] > 0, "owner input bucket required")
    _require(counts["GAP"] > 0, "gap bucket required")
    return {"ok": True, "item_count": len(items), "status_counts": counts, "covered_gates": sorted(covered_gates)}


def verify_path(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(f"cannot load ledger: {exc}") from exc
    return verify_payload(payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=str(Path(__file__).with_name("evidence.json")))
    args = parser.parse_args()
    try:
        result = verify_path(Path(args.path))
    except VerificationError as exc:
        print(f"INVALID: {exc}")
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
