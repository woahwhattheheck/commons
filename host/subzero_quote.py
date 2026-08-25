#!/usr/bin/env python3
"""host/subzero_quote.py — sz-paid-validation is a quote draft.

Slack 1787649732.551439 (JOJO INTEGRATED presence receipt):
file presence is PRESENT, structural=31, runtime=0, customer=0,
runtime_proof=false. Commercial consequence: sz-paid-validation
remains a $2,500 quote draft over STRUCTURAL_ONLY evidence — not
runtime, demand, or cash proof.

That Slack body is CLAIMED for the quote leftover. Presence already
landed as rivet-ship-subzero-tech-presence-20260825-01. Do not remint
it. This leftover names the commercial fact those bytes left open.

Do not remint SUBZERO_TECH / SUBZERO_GTM / SUBZERO_BUYERS /
SUBZERO_EXPLORER / SUBZERO_PROOF / White Box / payment-ready /
human-outcomes. Do not open accounts. Do not message buyers.
Do not store bank, routing, card, tax, or private-buyer data.
Do not write titan. Do not smash commons.mno. Do not add a gate.

X = Slack commercial-consequence + architecture sku + presence
counts + cash $0 / NOT_LANDED + leftover paths.
Y = those facts named on this tree.
Z = missing leftover / cash-runtime-demand claim / FINDER-FAILED /
FINDER-UNVERIFIED. Never 0.

  python3 host/subzero_quote.py
  python3 host/subzero_quote.py --root .
  python3 host/subzero_quote.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import sys


DEFAULT_ROOT = "."
DEFAULT_CATALOG = os.path.join("ground", "SUBZERO_QUOTE.json")
DEFAULT_CARD = os.path.join("ground", "SUBZERO_QUOTE.md")
DEFAULT_DOOR = "subzero-quote.html"
DEFAULT_ARCH = os.path.join("revenue", "subzero_gtm", "architecture.json")
SLACK_TS = "1787649732.551439"
SKU_ID = "sz-paid-validation"
QUOTE_PRICE = 2500
PRESENCE_RECEIPT = "rivet-ship-subzero-tech-presence-20260825-01"
SEARCH_SPACE = (
    DEFAULT_CARD,
    DEFAULT_CATALOG,
    os.path.join("host", "subzero_quote.py"),
    DEFAULT_DOOR,
    DEFAULT_ARCH,
    os.path.join("ground", "SUBZERO_TECH.md"),
    os.path.join("host", "subzero_tech.py"),
    os.path.join("ground", "SUBZERO_GTM.md"),
    os.path.join("host", "subzero_gtm.py"),
    os.path.join("ground", "EXECUTE.md"),
    os.path.join("p", "bryce-action-pad-open-door-directive-20260822-01.md"),
    os.path.join("p", PRESENCE_RECEIPT + ".md"),
)
CALIBRATION = (
    os.path.join("ground", "EXECUTE.md"),
    os.path.join("ground", "HEAD.md"),
    os.path.join("p", "bryce-action-pad-open-door-directive-20260822-01.md"),
)
ALREADY_LANDED = (
    os.path.join("host", "subzero_tech.py"),
    os.path.join("ground", "SUBZERO_TECH.md"),
    os.path.join("host", "subzero_gtm.py"),
    os.path.join("ground", "SUBZERO_GTM.md"),
    DEFAULT_ARCH,
    os.path.join("host", "subzero_buyers.py"),
    os.path.join("host", "subzero_explorer.py"),
    os.path.join("host", "subzero_proof.py"),
    os.path.join("p", PRESENCE_RECEIPT + ".md"),
)
REQUIRED_PHRASES = (
    "sz-paid-validation",
    "quote draft",
    "1787649732.551439",
    "structural_only",
    "not runtime",
    "not demand",
    "not cash",
    "commercial consequence",
    "finder-failed",
    "finder-unverified",
    "never 0",
    "open door",
    "unseated",
    "no auth",
    "no gate",
    "talk is not a land",
)


def _read(root, rel):
    path = os.path.join(root, rel)
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def _exists(root, rel):
    return os.path.isfile(os.path.join(root, rel))


def load_catalog(text):
    """Parse the quote leftover catalog. Invalid is measured empty."""
    try:
        data = json.loads(str(text or "") or "{}")
    except ValueError:
        return {"error": "catalog is not JSON"}
    if not isinstance(data, dict):
        return {"error": "catalog is not an object"}
    sku = data.get("sku") if isinstance(data.get("sku"), dict) else {}
    evidence = data.get("evidence") if isinstance(data.get("evidence"), dict) else {}
    return {
        "error": "",
        "slack_ts": str(data.get("slack_ts") or "").strip() or SLACK_TS,
        "titan": str(data.get("titan") or "NOT_WRITTEN").strip().upper() or "NOT_WRITTEN",
        "posting": str(data.get("posting") or "").strip(),
        "no_auth": bool(data.get("no_auth", True)),
        "no_gate": bool(data.get("no_gate", True)),
        "sku_id": str(sku.get("id") or "").strip(),
        "price_usd": int(sku.get("price_usd") or 0),
        "sku_status": str(sku.get("status") or "").strip().upper(),
        "sku_class": str(sku.get("class") or "").strip().upper(),
        "collected_cash_usd": int(data.get("collected_cash_usd") or 0),
        "cash_state": str(data.get("cash_state") or "").strip().upper(),
        "demand": str(data.get("demand") or "").strip().upper(),
        "runtime_proof": bool(evidence.get("runtime_proof")),
        "structural_only": int(evidence.get("structural_only") or 0),
        "runtime_measured": int(evidence.get("runtime_measured") or 0),
        "customer_ready": int(evidence.get("customer_ready") or 0),
        "claims_cash": bool(data.get("claims_cash")),
        "claims_runtime": bool(data.get("claims_runtime")),
        "claims_demand": bool(data.get("claims_demand")),
    }


def load_arch_sku(text):
    """Read sz-paid-validation from the already-landed GTM architecture."""
    try:
        data = json.loads(str(text or "") or "{}")
    except ValueError:
        return {"error": "architecture is not JSON"}
    if not isinstance(data, dict):
        return {"error": "architecture is not an object"}
    for item in data.get("paths") or []:
        if isinstance(item, dict) and str(item.get("id") or "").strip() == SKU_ID:
            return {
                "error": "",
                "id": SKU_ID,
                "price_usd": int(item.get("price_usd") or 0),
                "status": str(item.get("status") or "").strip().upper(),
                "kind": str(item.get("kind") or "").strip(),
            }
    return {"error": SKU_ID + " path FINDER-FAILED"}


def classify_quote(row):
    """Name one SKU. Presence / GTM bytes are not cash, runtime, or demand."""
    row = row or {}
    if not row.get("measured"):
        return {
            "state": "UNMEASURED",
            "note": (
                "sz-paid-validation quote not read. Absence was not stillness. "
                "FINDER-FAILED, never 0."
            ),
        }
    if str(row.get("finder") or "").strip().lower() in {"failed", "unknown", "error"}:
        return {
            "state": "FINDER-FAILED",
            "note": (
                "finder/tool call failed on "
                + str(row.get("sku_id") or SKU_ID)
                + ". UNKNOWN, never 0."
            ),
        }
    sku_id = str(row.get("sku_id") or "").strip()
    if sku_id != SKU_ID:
        return {
            "state": "NOT_LANDED",
            "note": (
                "sku is "
                + (sku_id or "missing")
                + ", not "
                + SKU_ID
                + ". Commercial consequence stays unnamed. FINDER-FAILED, never 0."
            ),
        }
    if bool(row.get("claims_cash")) or int(row.get("collected_cash_usd") or 0) > 0:
        return {
            "state": "NOT_LANDED",
            "note": (
                SKU_ID
                + " is not cash proof. Collected cash stays $0 / NOT_LANDED. "
                "A quote draft is not a deposit. FINDER-FAILED, never 0."
            ),
        }
    if bool(row.get("claims_runtime")) or bool(row.get("runtime_proof")):
        return {
            "state": "NOT_LANDED",
            "note": (
                SKU_ID
                + " is not runtime proof. Titan presence is PRESENT and "
                "runtime_proof is false. FINDER-FAILED, never 0."
            ),
        }
    if bool(row.get("claims_demand")) or str(row.get("demand") or "").strip().upper() not in {
        "",
        "UNKNOWN",
    }:
        return {
            "state": "NOT_LANDED",
            "note": (
                SKU_ID
                + " is not demand proof. Demand stays UNKNOWN. "
                "FINDER-FAILED, never 0."
            ),
        }
    price = int(row.get("price_usd") or 0)
    if price != QUOTE_PRICE:
        return {
            "state": "NOT_LANDED",
            "note": (
                SKU_ID
                + " price is "
                + str(price)
                + ", not "
                + str(QUOTE_PRICE)
                + ". Quote draft stays unbound. FINDER-FAILED, never 0."
            ),
        }
    if str(row.get("sku_class") or "").strip().upper() != "QUOTE_DRAFT":
        return {
            "state": "NOT_LANDED",
            "note": (
                SKU_ID
                + " must stay QUOTE_DRAFT over STRUCTURAL_ONLY evidence. "
                "CANDIDATE in GTM is not cash. FINDER-FAILED, never 0."
            ),
        }
    if int(row.get("structural_only") or 0) != 31:
        return {
            "state": "NOT_LANDED",
            "note": (
                "presence leftover named structural=31. This quote leftover "
                "must keep that count. FINDER-FAILED, never 0."
            ),
        }
    if int(row.get("runtime_measured") or 0) != 0 or int(row.get("customer_ready") or 0) != 0:
        return {
            "state": "NOT_LANDED",
            "note": (
                "runtime/customer counts must stay 0 until a distinct "
                "cross-process or buyer receipt lands. Never 0 as a silent "
                "finder. FINDER-FAILED, never 0."
            ),
        }
    return {
        "state": "QUOTE_DRAFT",
        "note": (
            SKU_ID
            + " is a $"
            + str(QUOTE_PRICE)
            + " quote draft over STRUCTURAL_ONLY evidence. "
            "Not runtime, not demand, not cash proof."
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
        "arch_present": bool(facts.get("arch_present")),
        "landed_present": list(facts.get("landed_present") or []),
        "landed_missing": list(facts.get("landed_missing") or []),
        "found_phrases": list(facts.get("found_phrases") or []),
        "sku_id": str(facts.get("sku_id") or ""),
        "price_usd": int(facts.get("price_usd") or 0),
        "sku_status": str(facts.get("sku_status") or ""),
        "sku_class": str(facts.get("sku_class") or ""),
        "arch_price_usd": int(facts.get("arch_price_usd") or 0),
        "arch_status": str(facts.get("arch_status") or ""),
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
        "quote_state": str(facts.get("quote_state") or ""),
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
    """Turn a measured quote census into a desk state."""
    row = row or {}
    if not row.get("measured"):
        return {
            "state": "UNMEASURED",
            "note": (
                "SUBZERO quote leftover not read. Absence was not stillness. "
                "A Slack commercial consequence is not the file. "
                "not stillness. FINDER-FAILED, never 0."
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
        or not row.get("arch_present")
    ):
        return {
            "state": "NOT_LANDED",
            "note": (
                "missing leftover path(s): "
                + ", ".join(misses or ["card/catalog/door/arch"])
                + ". JOJO commercial-consequence / sz-paid-validation / "
                "quote-draft talk is CLAIMED until the leftover ships. "
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
    quote = classify_quote(row)
    if quote["state"] != "QUOTE_DRAFT":
        return {
            "state": "NOT_LANDED",
            "note": quote["note"],
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
            "SUBZERO quote leftover is on this tree. "
            + SKU_ID
            + " stays a $"
            + str(QUOTE_PRICE)
            + " QUOTE_DRAFT over STRUCTURAL_ONLY. Not runtime, not demand, "
            "not cash. A Slack commercial consequence is still not the file."
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
    catalog = load_catalog(_read(root, DEFAULT_CATALOG))
    arch = load_arch_sku(_read(root, DEFAULT_ARCH))
    calibration_hits = [rel for rel in CALIBRATION if _exists(root, rel)]
    calibration_ok = len(calibration_hits) == len(CALIBRATION)
    if not calibration_ok:
        for rel in CALIBRATION:
            if rel not in calibration_hits and rel not in misses:
                misses.append("calibration:" + rel)
    posting_open = (
        catalog.get("posting") == "OPEN"
        and "open door" in hay
        and "unseated" in hay
    )
    facts = {
        "card_present": _exists(root, DEFAULT_CARD),
        "catalog_present": _exists(root, DEFAULT_CATALOG) and not catalog.get("error"),
        "door_present": _exists(root, DEFAULT_DOOR),
        "arch_present": _exists(root, DEFAULT_ARCH) and not arch.get("error"),
        "landed_present": landed_present,
        "landed_missing": landed_missing,
        "found_phrases": found,
        "sku_id": catalog.get("sku_id") or "",
        "price_usd": catalog.get("price_usd") or 0,
        "sku_status": catalog.get("sku_status") or "",
        "sku_class": catalog.get("sku_class") or "",
        "arch_price_usd": arch.get("price_usd") or 0,
        "arch_status": arch.get("status") or "",
        "collected_cash_usd": catalog.get("collected_cash_usd") or 0,
        "cash_state": catalog.get("cash_state") or "",
        "demand": catalog.get("demand") or "",
        "runtime_proof": bool(catalog.get("runtime_proof")),
        "structural_only": catalog.get("structural_only") or 0,
        "runtime_measured": catalog.get("runtime_measured") or 0,
        "customer_ready": catalog.get("customer_ready") or 0,
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
        "titan": catalog.get("titan") or "NOT_WRITTEN",
        "slack_ts": catalog.get("slack_ts") or SLACK_TS,
    }
    quote = classify_quote(
        {
            "measured": True,
            "sku_id": facts["sku_id"],
            "price_usd": facts["price_usd"],
            "sku_class": facts["sku_class"],
            "collected_cash_usd": facts["collected_cash_usd"],
            "demand": facts["demand"],
            "runtime_proof": facts["runtime_proof"],
            "structural_only": facts["structural_only"],
            "runtime_measured": facts["runtime_measured"],
            "customer_ready": facts["customer_ready"],
            "claims_cash": facts["claims_cash"],
            "claims_runtime": facts["claims_runtime"],
            "claims_demand": facts["claims_demand"],
        }
    )
    facts["quote_state"] = quote["state"]
    row = measure_from_rows(facts)
    row.update(
        {
            "slack_ts": facts["slack_ts"],
            "x": [rel for rel in SEARCH_SPACE if _exists(root, rel)],
            "y": {
                "calibration_hits": calibration_hits,
                "found_phrases": found,
                "landed_present": landed_present,
                "sku_id": facts["sku_id"],
                "price_usd": facts["price_usd"],
                "sku_class": facts["sku_class"],
                "arch_status": facts["arch_status"],
                "arch_price_usd": facts["arch_price_usd"],
                "quote_state": quote["state"],
                "presence_receipt": PRESENCE_RECEIPT,
            },
            "z": (
                "misses "
                + json.dumps(misses + landed_missing)
                + " / FINDER-FAILED never 0 / quote "
                + quote["state"]
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
                "misses": ["ground/SUBZERO_QUOTE.md"],
                "calibration_ok": True,
            }
        )
    )
    assert missing["state"] == "NOT_LANDED", missing
    cash = classify_quote(
        {
            "measured": True,
            "sku_id": SKU_ID,
            "price_usd": QUOTE_PRICE,
            "sku_class": "QUOTE_DRAFT",
            "claims_cash": True,
            "structural_only": 31,
        }
    )
    assert cash["state"] == "NOT_LANDED", cash
    assert "not cash" in cash["note"].lower() or "not cash proof" in cash["note"].lower(), cash
    runtime = classify_quote(
        {
            "measured": True,
            "sku_id": SKU_ID,
            "price_usd": QUOTE_PRICE,
            "sku_class": "QUOTE_DRAFT",
            "runtime_proof": True,
            "structural_only": 31,
        }
    )
    assert runtime["state"] == "NOT_LANDED", runtime
    draft = classify_quote(
        {
            "measured": True,
            "sku_id": SKU_ID,
            "price_usd": QUOTE_PRICE,
            "sku_class": "QUOTE_DRAFT",
            "demand": "UNKNOWN",
            "structural_only": 31,
            "runtime_measured": 0,
            "customer_ready": 0,
            "runtime_proof": False,
            "collected_cash_usd": 0,
        }
    )
    assert draft["state"] == "QUOTE_DRAFT", draft
    return "ok"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Measure SUBZERO quote leftover")
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
