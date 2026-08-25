#!/usr/bin/env python3
"""host/subzero_receipt.py — quote-draft → buyer-bound receipt.

Slack 1787650230.035359 (JOJO BACKEND CELL H-008):
source-index the existing sz-paid-validation / P01 $2500 offer
into the smallest honest quote-draft → buyer-bound validation
receipt implementation. Talk that restates H-008 is CLAIMED
until this leftover measures the source index, the bind path,
UNBOUND live state, $0 / NOT_LANDED cash, and no remint.

Do not remint SUBZERO_QUOTE / SUBZERO_GTM / SUBZERO_BUYERS /
SUBZERO_EXPLORER / SUBZERO_PROOF / White Box / payment-ready /
human-outcomes / grok-receipt / PR 2320. Do not open accounts.
Do not message buyers. Do not store bank, routing, card, tax,
or private-buyer data. Do not write titan. Do not smash
commons.mno. Do not add a gate.

A public inbound post id is a binding key, not a seat. Bound
is still STRUCTURAL_ONLY. Bound is not cash, not runtime, not
demand proof.

X = Slack H-008 + quote leftover + GTM sku + P01 + schema +
    leftover paths.
Y = those facts named on this tree + bind implementation.
Z = missing leftover / invented buyer / cash-runtime-demand
    claim / FINDER-FAILED / FINDER-UNVERIFIED. Never 0.

  python3 host/subzero_receipt.py
  python3 host/subzero_receipt.py --root .
  python3 host/subzero_receipt.py --self-test
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys


DEFAULT_ROOT = "."
DEFAULT_CATALOG = os.path.join("ground", "SUBZERO_RECEIPT.json")
DEFAULT_CARD = os.path.join("ground", "SUBZERO_RECEIPT.md")
DEFAULT_DOOR = "subzero-receipt.html"
DEFAULT_QUOTE = os.path.join("ground", "SUBZERO_QUOTE.json")
DEFAULT_ARCH = os.path.join("revenue", "subzero_gtm", "architecture.json")
DEFAULT_BUYERS = os.path.join("revenue", "subzero_buyers", "pack.json")
DEFAULT_SCHEMA = os.path.join(
    "revenue", "subzero_buyers", "validation_receipt.schema.json"
)
SLACK_TS = "1787650230.035359"
CELL = "H-008"
SKU_ID = "sz-paid-validation"
P01_ID = "P01_catalog_receipt"
QUOTE_PRICE = 2500
QUOTE_RECEIPT = "rivet-ship-subzero-quote-20260825-01"
HUMAN_RECEIPT = "rivet-ship-human-outcomes-20260825-01"
GRBN_REL = os.path.join("excerpts", "20260823", "muhl_grbn.mno")
GRBN_SHA = "09214540b3f3117ab93a4c509017a5e7b9c5f12d86545069af4ffcdae99c6632"
SEARCH_SPACE = (
    DEFAULT_CARD,
    DEFAULT_CATALOG,
    os.path.join("host", "subzero_receipt.py"),
    DEFAULT_DOOR,
    DEFAULT_QUOTE,
    DEFAULT_ARCH,
    DEFAULT_BUYERS,
    DEFAULT_SCHEMA,
    os.path.join("host", "subzero_quote.py"),
    os.path.join("ground", "EXECUTE.md"),
    os.path.join("p", "bryce-action-pad-open-door-directive-20260822-01.md"),
    os.path.join("p", QUOTE_RECEIPT + ".md"),
)
CALIBRATION = (
    os.path.join("ground", "EXECUTE.md"),
    os.path.join("ground", "HEAD.md"),
    os.path.join("p", "bryce-action-pad-open-door-directive-20260822-01.md"),
)
ALREADY_LANDED = (
    os.path.join("host", "subzero_quote.py"),
    os.path.join("ground", "SUBZERO_QUOTE.md"),
    os.path.join("ground", "SUBZERO_QUOTE.json"),
    DEFAULT_ARCH,
    DEFAULT_BUYERS,
    DEFAULT_SCHEMA,
    os.path.join("host", "subzero_explorer.py"),
    os.path.join("host", "human_outcomes.py"),
    os.path.join("p", QUOTE_RECEIPT + ".md"),
)
REQUIRED_PHRASES = (
    "sz-paid-validation",
    "p01_catalog_receipt",
    "quote-draft",
    "buyer-bound",
    "validation receipt",
    "1787650230.035359",
    "h-008",
    "structural_only",
    "not runtime",
    "not demand",
    "not cash",
    "unbound",
    "finder-failed",
    "finder-unverified",
    "never 0",
    "open door",
    "unseated",
    "no auth",
    "no gate",
    "talk is not a land",
)
HEX64 = set("0123456789abcdef")


def _read(root, rel):
    path = os.path.join(root, rel)
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def _read_bytes(root, rel):
    path = os.path.join(root, rel)
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError:
        return b""


def _exists(root, rel):
    return os.path.isfile(os.path.join(root, rel))


def _hex_sha(value):
    text = str(value or "").strip().lower()
    return len(text) == 64 and set(text) <= HEX64


def parse_excerpt(blob):
    """Read magic + LE header. Short or empty is FINDER-FAILED."""
    if len(blob) < 28:
        return {"ok": False, "reason": "header too short", "sha256": ""}
    magic = blob[:8].decode("ascii", "replace")
    n_gate, n_wires, n_in, n_out, depth = struct.unpack_from("<IIIII", blob, 8)
    return {
        "ok": True,
        "reason": "",
        "magic": magic,
        "n_gate": n_gate,
        "n_wires": n_wires,
        "n_in": n_in,
        "n_out": n_out,
        "depth": depth,
        "bytes": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
    }


def load_json(text, label):
    try:
        data = json.loads(str(text or "") or "{}")
    except ValueError:
        return {"error": label + " is not JSON"}
    if not isinstance(data, dict):
        return {"error": label + " is not an object"}
    return data


def source_index(root):
    """Read already-landed quote / GTM / P01 / schema. Do not remint."""
    quote = load_json(_read(root, DEFAULT_QUOTE), "quote")
    arch = load_json(_read(root, DEFAULT_ARCH), "architecture")
    buyers = load_json(_read(root, DEFAULT_BUYERS), "buyers")
    schema = load_json(_read(root, DEFAULT_SCHEMA), "schema")
    sku = quote.get("sku") if isinstance(quote.get("sku"), dict) else {}
    evidence = quote.get("evidence") if isinstance(quote.get("evidence"), dict) else {}
    arch_sku = {}
    for item in arch.get("paths") or []:
        if isinstance(item, dict) and str(item.get("id") or "").strip() == SKU_ID:
            arch_sku = item
            break
    p01 = {}
    for item in buyers.get("paths") or []:
        if isinstance(item, dict) and str(item.get("id") or "").strip() == P01_ID:
            p01 = item
            break
    defs = schema.get("$defs") if isinstance(schema.get("$defs"), dict) else {}
    return {
        "quote_error": str(quote.get("error") or ""),
        "arch_error": str(arch.get("error") or ""),
        "buyers_error": str(buyers.get("error") or ""),
        "schema_error": str(schema.get("error") or ""),
        "sku_id": str(sku.get("id") or "").strip(),
        "quote_class": str(sku.get("class") or "").strip().upper(),
        "quote_price": int(sku.get("price_usd") or 0),
        "quote_status": str(sku.get("status") or "").strip().upper(),
        "arch_id": str(arch_sku.get("id") or "").strip(),
        "arch_price": int(arch_sku.get("price_usd") or 0),
        "arch_status": str(arch_sku.get("status") or "").strip().upper(),
        "arch_implements": str(arch_sku.get("implements") or "").strip(),
        "p01_id": str(p01.get("id") or "").strip(),
        "p01_from": int(p01.get("price_usd_from") or 0),
        "p01_to": int(p01.get("price_usd_to") or 0),
        "schema_has_buyer": "buyer_receipt" in defs,
        "schema_no_auth": schema.get("no_auth") is True,
        "schema_no_gate": schema.get("no_gate") is True,
        "structural_only": int(evidence.get("structural_only") or 0),
        "runtime_measured": int(evidence.get("runtime_measured") or 0),
        "customer_ready": int(evidence.get("customer_ready") or 0),
        "runtime_proof": bool(evidence.get("runtime_proof")),
        "collected_cash_usd": int(quote.get("collected_cash_usd") or 0),
        "cash_state": str(quote.get("cash_state") or "").strip().upper(),
        "demand": str(quote.get("demand") or "").strip().upper(),
    }


def inbound_rel(inbound_id):
    name = str(inbound_id or "").strip()
    if not name or "/" in name or name in {".", ".."}:
        return ""
    return os.path.join("p", name + ".md")


def bind_validation_receipt(root, inbound_id, excerpt_rel, status="UNKNOWN"):
    """Bind a STRUCTURAL_ONLY receipt to a public inbound post id.

    buyer_id is the public inbound id, not a private identity.
    bound=True only when the inbound file and excerpt both exist
    and the excerpt header/hash measure. PASS is refused on the
    live tree unless the caller is an explicit fixture.
    """
    rel = inbound_rel(inbound_id)
    excerpt = str(excerpt_rel or "").strip()
    parsed = parse_excerpt(_read_bytes(root, excerpt))
    inbound_ok = bool(rel) and _exists(root, rel)
    excerpt_ok = bool(parsed.get("ok")) and _hex_sha(parsed.get("sha256"))
    bound = inbound_ok and excerpt_ok
    wanted = str(status or "UNKNOWN").strip().upper()
    if wanted not in {"PASS", "FAIL", "UNKNOWN"}:
        wanted = "UNKNOWN"
    if bound and wanted == "PASS" and excerpt == GRBN_REL:
        # Live GRBN remeasure is STRUCTURAL_ONLY. PASS would claim
        # CUSTOMER_READY. Keep live binds UNKNOWN unless fixture.
        wanted = "UNKNOWN"
    receipt = {
        "kind": "SUBZERO_BUYER_VALIDATION",
        "artifact": excerpt,
        "sha256": str(parsed.get("sha256") or ""),
        "status": wanted if bound else "UNKNOWN",
        "bound": bound,
        "buyer_id": str(inbound_id or "").strip() if bound else "",
        "no_auth": True,
        "no_gate": True,
        "login_required": False,
        "privileged_tier": False,
    }
    return {
        "receipt": receipt,
        "inbound_ok": inbound_ok,
        "excerpt_ok": excerpt_ok,
        "header": parsed,
        "binding_state": "BUYER_BOUND" if bound else "UNBOUND",
        "evidence_class": "STRUCTURAL_ONLY" if excerpt_ok else "UNKNOWN",
        "cash_state": "NOT_LANDED",
        "demand": "UNKNOWN",
    }


def receipt_schema_ok(receipt):
    """Match the already-landed buyer_receipt required fields."""
    receipt = receipt or {}
    if str(receipt.get("kind") or "") != "SUBZERO_BUYER_VALIDATION":
        return False
    if not str(receipt.get("artifact") or "").strip():
        return False
    if not _hex_sha(receipt.get("sha256")):
        return False
    if receipt.get("status") not in {"PASS", "FAIL", "UNKNOWN"}:
        return False
    if receipt.get("bound") is True and not str(receipt.get("buyer_id") or "").strip():
        return False
    if receipt.get("bound") is not True and receipt.get("bound") is not False:
        return False
    return (
        receipt.get("no_auth") is True
        and receipt.get("no_gate") is True
        and receipt.get("login_required") is False
        and receipt.get("privileged_tier") is False
    )


def classify_binding(row):
    """Name the live bind. Invented buyers / cash / runtime fail."""
    row = row or {}
    if not row.get("measured"):
        return {
            "state": "UNMEASURED",
            "note": (
                "H-008 receipt leftover not read. Absence was not stillness. "
                "FINDER-FAILED, never 0."
            ),
        }
    if str(row.get("finder") or "").strip().lower() in {"failed", "unknown", "error"}:
        return {
            "state": "FINDER-FAILED",
            "note": (
                "finder/tool call failed on "
                + SKU_ID
                + " bind. UNKNOWN, never 0."
            ),
        }
    if bool(row.get("claims_cash")) or int(row.get("collected_cash_usd") or 0) > 0:
        return {
            "state": "NOT_LANDED",
            "note": (
                "A buyer-bound receipt is not cash proof. Collected cash stays "
                "$0 / NOT_LANDED. FINDER-FAILED, never 0."
            ),
        }
    if bool(row.get("claims_runtime")) or bool(row.get("runtime_proof")):
        return {
            "state": "NOT_LANDED",
            "note": (
                "A buyer-bound receipt is not runtime proof. "
                "FINDER-FAILED, never 0."
            ),
        }
    if bool(row.get("claims_demand")) or str(row.get("demand") or "").strip().upper() not in {
        "",
        "UNKNOWN",
    }:
        return {
            "state": "NOT_LANDED",
            "note": (
                "A bind implementation is not demand proof. Demand stays "
                "UNKNOWN. FINDER-FAILED, never 0."
            ),
        }
    if int(row.get("live_bound_receipts") or 0) > 0:
        return {
            "state": "NOT_LANDED",
            "note": (
                "Live tree invented a buyer-bound receipt. Demand stays "
                "UNKNOWN. FINDER-FAILED, never 0."
            ),
        }
    if str(row.get("binding_state") or "").strip().upper() != "UNBOUND":
        return {
            "state": "NOT_LANDED",
            "note": (
                "Live binding_state must stay UNBOUND until a public inbound "
                "names a file. FINDER-FAILED, never 0."
            ),
        }
    if str(row.get("sku_id") or "").strip() != SKU_ID:
        return {
            "state": "NOT_LANDED",
            "note": (
                "source-index sku is "
                + (str(row.get("sku_id") or "missing"))
                + ", not "
                + SKU_ID
                + ". FINDER-FAILED, never 0."
            ),
        }
    if int(row.get("quote_price") or 0) != QUOTE_PRICE:
        return {
            "state": "NOT_LANDED",
            "note": (
                SKU_ID
                + " price is "
                + str(row.get("quote_price"))
                + ", not "
                + str(QUOTE_PRICE)
                + ". FINDER-FAILED, never 0."
            ),
        }
    if str(row.get("p01_id") or "").strip() != P01_ID:
        return {
            "state": "NOT_LANDED",
            "note": "P01_catalog_receipt FINDER-FAILED, never 0.",
        }
    if not row.get("schema_has_buyer"):
        return {
            "state": "NOT_LANDED",
            "note": "buyer_receipt schema FINDER-FAILED, never 0.",
        }
    if not row.get("bind_works"):
        return {
            "state": "NOT_LANDED",
            "note": (
                "quote-draft → buyer-bound bind did not implement. "
                "FINDER-FAILED, never 0."
            ),
        }
    return {
        "state": "UNBOUND",
        "note": (
            SKU_ID
            + " / "
            + P01_ID
            + " quote-draft → buyer-bound receipt is implemented. "
            "Live bind stays UNBOUND. Not runtime, not demand, not cash."
        ),
    }


def measure_from_rows(facts):
    """Classify measured file/phrase facts. Missing calibration is UNMEASURED."""
    facts = facts or {}
    return {
        "measured": True,
        "card_present": bool(facts.get("card_present")),
        "catalog_present": bool(facts.get("catalog_present")),
        "door_present": bool(facts.get("door_present")),
        "quote_present": bool(facts.get("quote_present")),
        "arch_present": bool(facts.get("arch_present")),
        "buyers_present": bool(facts.get("buyers_present")),
        "schema_present": bool(facts.get("schema_present")),
        "landed_present": list(facts.get("landed_present") or []),
        "landed_missing": list(facts.get("landed_missing") or []),
        "found_phrases": list(facts.get("found_phrases") or []),
        "sku_id": str(facts.get("sku_id") or ""),
        "quote_class": str(facts.get("quote_class") or ""),
        "quote_price": int(facts.get("quote_price") or 0),
        "p01_id": str(facts.get("p01_id") or ""),
        "arch_status": str(facts.get("arch_status") or ""),
        "arch_implements": str(facts.get("arch_implements") or ""),
        "schema_has_buyer": bool(facts.get("schema_has_buyer")),
        "schema_no_auth": bool(facts.get("schema_no_auth")),
        "schema_no_gate": bool(facts.get("schema_no_gate")),
        "binding_state": str(facts.get("binding_state") or ""),
        "live_bound_receipts": int(facts.get("live_bound_receipts") or 0),
        "bind_works": bool(facts.get("bind_works")),
        "grbn_sha": str(facts.get("grbn_sha") or ""),
        "collected_cash_usd": int(facts.get("collected_cash_usd") or 0),
        "cash_state": str(facts.get("cash_state") or ""),
        "demand": str(facts.get("demand") or ""),
        "runtime_proof": bool(facts.get("runtime_proof")),
        "structural_only": int(facts.get("structural_only") or 0),
        "runtime_measured": int(facts.get("runtime_measured") or 0),
        "customer_ready": int(facts.get("customer_ready") or 0),
        "claims_cash": bool(facts.get("claims_cash")),
        "claims_runtime": bool(facts.get("claims_runtime")),
        "claims_demand": bool(facts.get("claims_demand")),
        "posting_open": bool(facts.get("posting_open")),
        "no_auth": bool(facts.get("no_auth")),
        "no_gate": bool(facts.get("no_gate")),
        "calibration_ok": bool(facts.get("calibration_ok")),
        "calibration_hits": list(facts.get("calibration_hits") or []),
        "search_space": list(facts.get("search_space") or SEARCH_SPACE),
        "misses": list(facts.get("misses") or []),
        "titan": str(facts.get("titan") or "NOT_WRITTEN"),
    }


def classify(row):
    """Turn a measured receipt census into a desk state."""
    row = row or {}
    if not row.get("measured"):
        return {
            "state": "UNMEASURED",
            "note": (
                "SUBZERO receipt leftover not read. Absence was not stillness. "
                "A Slack H-008 body is not the file. FINDER-FAILED, never 0."
            ),
        }
    if row.get("calibration_ok") is False:
        return {
            "state": "UNMEASURED",
            "note": (
                "known-present calibration failed: "
                + ", ".join(row.get("calibration_hits") or [])
                + ". Search-zero testing is instrument failure, not absence proof. "
                "FINDER-FAILED, never 0."
            ),
        }
    misses = list(row.get("misses") or [])
    landed_missing = list(row.get("landed_missing") or [])
    if (
        not row.get("card_present")
        or not row.get("catalog_present")
        or not row.get("door_present")
        or not row.get("quote_present")
        or not row.get("arch_present")
        or not row.get("buyers_present")
        or not row.get("schema_present")
    ):
        return {
            "state": "NOT_LANDED",
            "note": (
                "missing leftover path(s): "
                + ", ".join(misses or ["card/catalog/door/source-index"])
                + ". JOJO H-008 / quote-draft → buyer-bound / "
                "validation-receipt talk is CLAIMED until the leftover ships. "
                "FINDER-FAILED, never 0."
            ),
        }
    if landed_missing:
        return {
            "state": "NOT_LANDED",
            "note": (
                "named already-landed leftover(s) missing: "
                + ", ".join(landed_missing)
                + ". Census is incomplete. FINDER-FAILED, never 0."
            ),
        }
    binding = classify_binding(row)
    if binding["state"] != "UNBOUND":
        return {
            "state": "NOT_LANDED",
            "note": binding["note"],
        }
    needed = [
        phrase
        for phrase in REQUIRED_PHRASES
        if phrase not in (row.get("found_phrases") or [])
    ]
    if needed or not row.get("posting_open") or not row.get("no_auth") or not row.get("no_gate"):
        return {
            "state": "NOT_LANDED",
            "note": (
                "leftover present but incomplete. Missing phrases: "
                + ", ".join(needed)
                + ". Open door + no auth + no gate required. Talk is CLAIMED. "
                "FINDER-FAILED, never 0."
            ),
        }
    return {
        "state": "INTEGRATED",
        "note": (
            "SUBZERO receipt leftover is on this tree. "
            + SKU_ID
            + " / "
            + P01_ID
            + " quote-draft → buyer-bound bind is implemented. "
            "Live bind stays UNBOUND. Not runtime, not demand, not cash. "
            "A Slack H-008 body is still not the file."
        ),
    }


def measure_root(root):
    root = os.path.abspath(root)
    misses = []
    blobs = []
    for rel in SEARCH_SPACE:
        text = _read(root, rel)
        if not text:
            misses.append(rel)
        else:
            blobs.append(text)
    hay = "\n".join(blobs).lower()
    found = [phrase for phrase in REQUIRED_PHRASES if phrase in hay]
    landed_present = [rel for rel in ALREADY_LANDED if _exists(root, rel)]
    landed_missing = [rel for rel in ALREADY_LANDED if not _exists(root, rel)]
    catalog = load_json(_read(root, DEFAULT_CATALOG), "catalog")
    indexed = source_index(root)
    calibration_hits = [rel for rel in CALIBRATION if _exists(root, rel)]
    calibration_ok = len(calibration_hits) == len(CALIBRATION)
    if not calibration_ok:
        for rel in CALIBRATION:
            if rel not in calibration_hits and rel not in misses:
                misses.append("calibration:" + rel)
    posting_open = (
        str(catalog.get("posting") or "") == "OPEN"
        and "open door" in hay
        and "unseated" in hay
    )
    missing_inbound = bind_validation_receipt(
        root,
        "fixture-h008-inbound-20260825-01",
        GRBN_REL,
        status="UNKNOWN",
    )
    # Prove the bind against an already-landed public post id + GRBN.
    # That is a function test, not demand. Live catalog stays UNBOUND.
    proved = bind_validation_receipt(root, QUOTE_RECEIPT, GRBN_REL, status="UNKNOWN")
    bind_works = (
        missing_inbound["binding_state"] == "UNBOUND"
        and missing_inbound["excerpt_ok"]
        and str((missing_inbound.get("header") or {}).get("sha256") or "") == GRBN_SHA
        and proved["binding_state"] == "BUYER_BOUND"
        and receipt_schema_ok(proved["receipt"])
        and proved["receipt"]["status"] == "UNKNOWN"
        and proved["receipt"]["buyer_id"] == QUOTE_RECEIPT
        and proved["evidence_class"] == "STRUCTURAL_ONLY"
        and str(proved["receipt"].get("sha256") or "") == GRBN_SHA
    )
    live_bound = int(catalog.get("live_bound_receipts") or 0)
    facts = {
        "card_present": _exists(root, DEFAULT_CARD),
        "catalog_present": _exists(root, DEFAULT_CATALOG) and not catalog.get("error"),
        "door_present": _exists(root, DEFAULT_DOOR),
        "quote_present": _exists(root, DEFAULT_QUOTE) and not indexed.get("quote_error"),
        "arch_present": _exists(root, DEFAULT_ARCH) and not indexed.get("arch_error"),
        "buyers_present": _exists(root, DEFAULT_BUYERS) and not indexed.get("buyers_error"),
        "schema_present": _exists(root, DEFAULT_SCHEMA)
        and not indexed.get("schema_error")
        and indexed.get("schema_has_buyer"),
        "landed_present": landed_present,
        "landed_missing": landed_missing,
        "found_phrases": found,
        "sku_id": indexed.get("sku_id") or "",
        "quote_class": indexed.get("quote_class") or "",
        "quote_price": indexed.get("quote_price") or 0,
        "p01_id": indexed.get("p01_id") or "",
        "arch_status": indexed.get("arch_status") or "",
        "arch_implements": indexed.get("arch_implements") or "",
        "schema_has_buyer": bool(indexed.get("schema_has_buyer")),
        "schema_no_auth": bool(indexed.get("schema_no_auth")),
        "schema_no_gate": bool(indexed.get("schema_no_gate")),
        "binding_state": str(catalog.get("binding_state") or "UNBOUND").upper(),
        "live_bound_receipts": live_bound,
        "bind_works": bind_works,
        "grbn_sha": str((proved.get("header") or {}).get("sha256") or ""),
        "collected_cash_usd": indexed.get("collected_cash_usd") or 0,
        "cash_state": indexed.get("cash_state") or "",
        "demand": indexed.get("demand") or "",
        "runtime_proof": bool(indexed.get("runtime_proof")),
        "structural_only": indexed.get("structural_only") or 0,
        "runtime_measured": indexed.get("runtime_measured") or 0,
        "customer_ready": indexed.get("customer_ready") or 0,
        "claims_cash": bool(catalog.get("claims_cash")),
        "claims_runtime": bool(catalog.get("claims_runtime")),
        "claims_demand": bool(catalog.get("claims_demand")),
        "posting_open": posting_open,
        "no_auth": bool(catalog.get("no_auth")) and "no auth" in hay,
        "no_gate": bool(catalog.get("no_gate")) and "no gate" in hay,
        "calibration_ok": calibration_ok,
        "calibration_hits": calibration_hits,
        "search_space": list(SEARCH_SPACE),
        "misses": misses,
        "titan": str(catalog.get("titan") or "NOT_WRITTEN"),
        "slack_ts": str(catalog.get("slack_ts") or SLACK_TS),
    }
    binding = classify_binding(measure_from_rows(facts))
    row = measure_from_rows(facts)
    row.update(
        {
            "slack_ts": facts["slack_ts"],
            "cell": CELL,
            "x": [rel for rel in SEARCH_SPACE if _exists(root, rel)],
            "y": {
                "calibration_hits": calibration_hits,
                "found_phrases": found,
                "landed_present": landed_present,
                "sku_id": facts["sku_id"],
                "quote_price": facts["quote_price"],
                "p01_id": facts["p01_id"],
                "binding_state": facts["binding_state"],
                "bind_works": facts["bind_works"],
                "live_bound_receipts": facts["live_bound_receipts"],
                "quote_receipt": QUOTE_RECEIPT,
            },
            "z": (
                "misses "
                + json.dumps(misses + landed_missing)
                + " / FINDER-FAILED never 0 / bind "
                + binding["state"]
            ),
        }
    )
    return row


def self_test():
    empty = classify({})
    assert empty["state"] == "UNMEASURED", empty
    missing = classify(
        measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "misses": ["ground/SUBZERO_RECEIPT.md"],
                "calibration_ok": True,
            }
        )
    )
    assert missing["state"] == "NOT_LANDED", missing
    cash = classify_binding(
        {
            "measured": True,
            "sku_id": SKU_ID,
            "quote_price": QUOTE_PRICE,
            "p01_id": P01_ID,
            "schema_has_buyer": True,
            "bind_works": True,
            "binding_state": "UNBOUND",
            "claims_cash": True,
        }
    )
    assert cash["state"] == "NOT_LANDED", cash
    invented = classify_binding(
        {
            "measured": True,
            "sku_id": SKU_ID,
            "quote_price": QUOTE_PRICE,
            "p01_id": P01_ID,
            "schema_has_buyer": True,
            "bind_works": True,
            "binding_state": "UNBOUND",
            "live_bound_receipts": 1,
            "demand": "UNKNOWN",
        }
    )
    assert invented["state"] == "NOT_LANDED", invented
    return "ok"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Measure SUBZERO receipt leftover")
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        print(self_test())
        return 0
    row = measure_root(args.root)
    verdict = classify(row)
    payload = {"verdict": verdict, "row": row}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if verdict["state"] == "INTEGRATED" else 1


if __name__ == "__main__":
    sys.exit(main())
