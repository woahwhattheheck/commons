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
EXPECTED_CANONICAL_ISSUE = "woahwhattheheck/commons#13850"

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
    _require(payload.get("canonical_issue") == EXPECTED_CANONICAL_ISSUE, "canonical issue mismatch")
    _require(payload.get("public_only") is True, "public_only must be true")
    _require(payload.get("authority") == EXPECTED_AUTHORITY, "authority ceiling mismatch")

    as_of = _parse_date(payload.get("as_of"), "as_of")
    items = payload.get("items")
    _require(isinstance(items, list) and items, "items must be non-empty list")
    seen = set()
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

    _require(counts["SUPPORTED"] > 0, "at least one narrow supported public fact required")
    _require(counts["PARTNER_CONFIRMATION_REQUIRED"] > 0, "partner confirmation bucket required")
    _require(counts["OWNER_INPUT"] > 0, "owner input bucket required")
    _require(counts["GAP"] > 0, "gap bucket required")
    return {"ok": True, "item_count": len(items), "status_counts": counts}


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
