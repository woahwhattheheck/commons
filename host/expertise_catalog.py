#!/usr/bin/env python3
"""Validate and inspect the Commons expertise catalog.

This module is deliberately fail-closed around money truth. It cannot create a
checkout, contact a buyer, or promote a quote-only offer to a live SKU.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_CATALOG = ROOT / "revenue" / "expertise_catalog" / "catalog.json"
ID_RE = re.compile(r"^expertise-[a-z0-9-]{5,72}$")
CAPABILITY_RE = re.compile(r"^[a-z0-9_]{5,80}$")
REPO_PATH_RE = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$))[A-Za-z0-9._/-]+$")
MONEY_RE = re.compile(r"^[1-9][0-9]*(?:\.[0-9]{2})$")
FORMATS = {"advisory_hour", "written_assessment", "design_review", "embedded_engagement"}
MODES = {"LIVE_EXISTING_SKU", "QUOTE_ONLY"}
REQUIRED_CAPABILITIES = {
    "agent_architecture_review",
    "model_gguf_diagnosis",
    "failure_recovery_analysis",
    "computer_use_design",
    "reproducibility_review",
    "evidence_architecture",
    "carrier_resource_routing",
    "muhlnickel_titan_technical_consultation",
}
TRUTH_FALSE_FIELDS = {
    "buyer_claimed", "acceptance_claimed", "delivery_claimed",
    "settlement_claimed", "payout_claimed", "cash_claimed",
}


class CatalogError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"cannot load catalog: {exc}") from exc
    if not isinstance(value, dict):
        raise CatalogError("catalog root must be an object")
    return value


def _nonempty_strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise CatalogError(f"{field} must be a non-empty array")
    for item in value:
        if not isinstance(item, str) or len(item.strip()) < 3:
            raise CatalogError(f"{field} entries must be non-empty strings")
    if len(value) != len(set(value)):
        raise CatalogError(f"{field} must not contain duplicates")
    return value


def _repo_path(value: Any, field: str) -> str:
    if not isinstance(value, str) or not REPO_PATH_RE.fullmatch(value):
        raise CatalogError(f"{field} must be a safe repository-relative path")
    return value


def _quote_mailto(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise CatalogError(f"{field} must be a mailto route")
    parsed = urlparse(value)
    if parsed.scheme != "mailto" or parsed.path != "tokenjunkielabs@gmail.com":
        raise CatalogError(f"{field} must use the canonical public inquiry mailbox")
    qs = parse_qs(parsed.query, keep_blank_values=True)
    if set(qs) != {"subject"} or len(qs["subject"]) != 1 or not qs["subject"][0].strip():
        raise CatalogError(f"{field} must contain exactly one non-empty subject")
    return value


def validate_catalog(catalog: dict[str, Any], *, root: Path = ROOT, require_sources: bool = True) -> None:
    expected_top = {
        "schema_version", "kind", "family", "canonical_page", "truth_boundary",
        "commercial_modes", "formats", "entries",
    }
    if set(catalog) != expected_top:
        raise CatalogError("catalog top-level fields are invalid")
    if catalog["schema_version"] != "commons-expertise-catalog/v1":
        raise CatalogError("unsupported schema_version")
    if catalog["kind"] != "EXPERTISE_CATALOG" or catalog["family"] != "expertise":
        raise CatalogError("catalog kind/family mismatch")
    if catalog["canonical_page"] != "expertise.html":
        raise CatalogError("canonical_page must be expertise.html")
    if catalog["commercial_modes"] != ["LIVE_EXISTING_SKU", "QUOTE_ONLY"]:
        raise CatalogError("commercial_modes must remain canonical")
    if catalog["formats"] != ["advisory_hour", "written_assessment", "design_review", "embedded_engagement"]:
        raise CatalogError("formats must remain canonical")

    truth = catalog["truth_boundary"]
    if not isinstance(truth, dict) or set(truth) != TRUTH_FALSE_FIELDS | {"rule"}:
        raise CatalogError("truth_boundary fields are invalid")
    for field in TRUTH_FALSE_FIELDS:
        if truth[field] is not False:
            raise CatalogError(f"truth_boundary.{field} must be false")
    if not isinstance(truth["rule"], str) or len(truth["rule"].strip()) < 20:
        raise CatalogError("truth_boundary.rule is too short")

    entries = catalog["entries"]
    if not isinstance(entries, list) or len(entries) < len(REQUIRED_CAPABILITIES):
        raise CatalogError("catalog must expose every required expertise capability")
    ids: set[str] = set()
    capabilities: set[str] = set()
    live_count = 0
    for index, entry in enumerate(entries):
        prefix = f"entries[{index}]"
        expected_entry = {
            "id", "capability", "title", "summary", "buyer_job", "formats", "inputs",
            "deliverables", "acceptance", "commercial", "source_evidence",
        }
        if not isinstance(entry, dict) or set(entry) != expected_entry:
            raise CatalogError(f"{prefix} fields are invalid")
        entry_id = entry["id"]
        if not isinstance(entry_id, str) or not ID_RE.fullmatch(entry_id):
            raise CatalogError(f"{prefix}.id is invalid")
        if entry_id in ids:
            raise CatalogError(f"duplicate entry id: {entry_id}")
        ids.add(entry_id)
        capability = entry["capability"]
        if not isinstance(capability, str) or not CAPABILITY_RE.fullmatch(capability):
            raise CatalogError(f"{prefix}.capability is invalid")
        if capability in capabilities:
            raise CatalogError(f"duplicate capability: {capability}")
        capabilities.add(capability)
        for field in ("title", "summary", "buyer_job"):
            if not isinstance(entry[field], str) or len(entry[field].strip()) < 5:
                raise CatalogError(f"{prefix}.{field} must be a non-empty string")
        formats = _nonempty_strings(entry["formats"], f"{prefix}.formats")
        if any(fmt not in FORMATS for fmt in formats):
            raise CatalogError(f"{prefix}.formats contains an unsupported format")
        for field in ("inputs", "deliverables", "acceptance"):
            _nonempty_strings(entry[field], f"{prefix}.{field}")

        sources = _nonempty_strings(entry["source_evidence"], f"{prefix}.source_evidence")
        for source in sources:
            path = _repo_path(source, f"{prefix}.source_evidence")
            if require_sources and not (root / path).is_file():
                raise CatalogError(f"{prefix}.source_evidence missing: {path}")

        commercial = entry["commercial"]
        if not isinstance(commercial, dict) or set(commercial) != {
            "mode", "amount_usd", "unit", "checkout_reference", "buyer_route"
        }:
            raise CatalogError(f"{prefix}.commercial fields are invalid")
        mode = commercial["mode"]
        if mode not in MODES:
            raise CatalogError(f"{prefix}.commercial.mode is invalid")
        if mode == "LIVE_EXISTING_SKU":
            live_count += 1
            amount = commercial["amount_usd"]
            if not isinstance(amount, str) or not MONEY_RE.fullmatch(amount):
                raise CatalogError(f"{prefix}.commercial.amount_usd must be a positive two-decimal string")
            try:
                if Decimal(amount) <= 0:
                    raise CatalogError(f"{prefix}.commercial.amount_usd must be positive")
            except InvalidOperation as exc:
                raise CatalogError(f"{prefix}.commercial.amount_usd is invalid") from exc
            if not isinstance(commercial["unit"], str) or not commercial["unit"].strip():
                raise CatalogError(f"{prefix}.commercial.unit is required")
            checkout_ref = _repo_path(commercial["checkout_reference"], f"{prefix}.commercial.checkout_reference")
            if checkout_ref not in sources:
                raise CatalogError(f"{prefix}.checkout_reference must also be source evidence")
            if require_sources and not (root / checkout_ref).is_file():
                raise CatalogError(f"{prefix}.checkout_reference missing: {checkout_ref}")
            route = commercial["buyer_route"]
            if not isinstance(route, str) or not route.startswith("commerce.html#"):
                raise CatalogError(f"{prefix}.commercial.buyer_route must route through existing commerce")
            if "stripe.com" in route:
                raise CatalogError(f"{prefix}.commercial.buyer_route must not remint or embed a Stripe URL")
        else:
            if commercial["amount_usd"] is not None or commercial["unit"] is not None or commercial["checkout_reference"] is not None:
                raise CatalogError(f"{prefix} QUOTE_ONLY must not carry price, unit, or checkout reference")
            _quote_mailto(commercial["buyer_route"], f"{prefix}.commercial.buyer_route")

    missing = REQUIRED_CAPABILITIES - capabilities
    if missing:
        raise CatalogError("missing expertise capabilities: " + ", ".join(sorted(missing)))
    if live_count != 1:
        raise CatalogError("catalog must contain exactly one source-backed LIVE_EXISTING_SKU")
    whitebox = next((row for row in entries if row["id"] == "expertise-whitebox-hour"), None)
    if whitebox is None or whitebox["commercial"] != {
        "mode": "LIVE_EXISTING_SKU",
        "amount_usd": "250.00",
        "unit": "hour",
        "checkout_reference": "land/sku-whitebox-hour-20260826.md",
        "buyer_route": "commerce.html#sku-whitebox-hour-20260826",
    }:
        raise CatalogError("White Box hour must exactly reuse the source-backed $250/hour commerce route")


def _self_test() -> None:
    import copy
    catalog = _load(DEFAULT_CATALOG)
    validate_catalog(catalog)
    bad = copy.deepcopy(catalog)
    bad["entries"][1]["commercial"]["amount_usd"] = "100.00"
    try:
        validate_catalog(bad)
    except CatalogError:
        pass
    else:
        raise CatalogError("self-test failed: quote-only invented price was accepted")
    bad = copy.deepcopy(catalog)
    bad["entries"][0]["commercial"]["buyer_route"] = "https://buy.stripe.com/invented"
    try:
        validate_catalog(bad)
    except CatalogError:
        pass
    else:
        raise CatalogError("self-test failed: embedded Stripe URL was accepted")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--self-test", action="store_true")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("validate")
    sub.add_parser("list")
    show = sub.add_parser("show")
    show.add_argument("entry_id")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            _self_test()
            print("SELF_TEST_OK")
            return 0
        catalog = _load(args.catalog)
        validate_catalog(catalog)
        if args.command in {None, "validate"}:
            print(f"VALID entries={len(catalog['entries'])} live_existing_sku=1 quote_only={len(catalog['entries']) - 1}")
        elif args.command == "list":
            for entry in catalog["entries"]:
                commercial = entry["commercial"]
                amount = "$" + commercial["amount_usd"] + "/" + commercial["unit"] if commercial["mode"] == "LIVE_EXISTING_SKU" else "QUOTE_ONLY"
                print(f"{entry['id']}\t{entry['title']}\t{amount}")
        elif args.command == "show":
            entry = next((row for row in catalog["entries"] if row["id"] == args.entry_id), None)
            if entry is None:
                raise CatalogError(f"unknown entry: {args.entry_id}")
            print(json.dumps(entry, indent=2, sort_keys=True))
        return 0
    except CatalogError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
