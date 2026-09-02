#!/usr/bin/env python3
"""Classify business-pack sales for clone-stamps. Not a Commons gate.

Bryce / GOAT 1788323099.458239: each customer purchase is a fresh package.
Do not sell the same assets+ops twice. Marketing uniqueness is only honest
when the fingerprint is unique. Agents do not spend ads. No fake Stripe URLs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LAW = ROOT / "ground" / "BUSINESS_PACKS.json"


def load_law(path: Path | None = None) -> dict[str, Any]:
    target = path or DEFAULT_LAW
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("law is not an object")
    return data


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_fingerprint(pack: dict[str, Any]) -> str:
    """Hash of assets+ops that must differ between customer purchases."""
    assets = str(pack.get("assets_sha256") or "").strip().lower()
    ops = str(pack.get("ops_sha256") or "").strip().lower()
    if assets and ops:
        return _sha256_text(assets + "\n" + ops)
    blob_parts: list[str] = []
    for key in ("assets", "ops"):
        value = pack.get(key)
        if value is None or value == "":
            continue
        if isinstance(value, (dict, list)):
            blob_parts.append(json.dumps(value, sort_keys=True, separators=(",", ":")))
        else:
            blob_parts.append(str(value))
    if len(blob_parts) < 2:
        return ""
    return _sha256_text("\n".join(blob_parts))


def classify_sales(sales: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Ledger of customer purchases. Same fingerprint on two sales is CLONE_STAMP."""
    rows = sales if isinstance(sales, list) else []
    by_sale: dict[str, str] = {}
    by_fp: dict[str, list[str]] = {}
    missing: list[str] = []
    conflicts: list[str] = []
    classified: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        sale_id = str(raw.get("sale_id") or "").strip()
        if not sale_id:
            missing.append("(blank sale_id)")
            continue
        fingerprint = content_fingerprint(raw)
        if not fingerprint:
            missing.append(sale_id)
            classified.append(
                {
                    "sale_id": sale_id,
                    "verdict": "MISSING_FINGERPRINT",
                    "fingerprint": "",
                    "marketing_uniqueness_ok": False,
                }
            )
            continue
        prior = by_sale.get(sale_id)
        if prior and prior != fingerprint:
            conflicts.append(sale_id)
        by_sale[sale_id] = fingerprint
        by_fp.setdefault(fingerprint, [])
        if sale_id not in by_fp[fingerprint]:
            by_fp[fingerprint].append(sale_id)
    clone_pairs: list[list[str]] = []
    for fingerprint, sale_ids in by_fp.items():
        if len(sale_ids) > 1:
            clone_pairs.append(sale_ids)
    for sale_id, fingerprint in by_sale.items():
        shared = by_fp.get(fingerprint) or [sale_id]
        if sale_id in conflicts:
            verdict = "CONFLICT"
        elif len(shared) > 1:
            verdict = "CLONE_STAMP"
        else:
            verdict = "UNIQUE"
        classified.append(
            {
                "sale_id": sale_id,
                "verdict": verdict,
                "fingerprint": fingerprint,
                "shared_with": [s for s in shared if s != sale_id],
                "marketing_uniqueness_ok": verdict == "UNIQUE",
            }
        )
    clone_sales = {s for pair in clone_pairs for s in pair}
    unique_count = sum(1 for row in classified if row["verdict"] == "UNIQUE")
    return {
        "gate": False,
        "commons_admission": False,
        "clone_stamp": bool(clone_pairs),
        "each_purchase": "fresh_package",
        "marketing": "bryce_only",
        "no_fake_stripe_urls": True,
        "sales": classified,
        "clone_pairs": clone_pairs,
        "conflicts": conflicts,
        "missing_fingerprint": missing,
        "unique_count": unique_count,
        "clone_stamp_count": len(clone_sales),
    }


def marketing_uniqueness_ok(pack: dict[str, Any], sales: list[dict[str, Any]]) -> bool:
    """True only when this pack's fingerprint appears on exactly one sale."""
    result = classify_sales(sales)
    sale_id = str(pack.get("sale_id") or "").strip()
    for row in result["sales"]:
        if row["sale_id"] == sale_id:
            return bool(row["marketing_uniqueness_ok"])
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sales-json", default="", help="JSON list of sale objects")
    parser.add_argument("--sales-file", default="", help="path to JSON list of sales")
    parser.add_argument("--law", default="", help="override law path")
    args = parser.parse_args(argv)
    law = load_law(Path(args.law) if args.law else None)
    sales: list[dict[str, Any]] = []
    if args.sales_file:
        loaded = json.loads(Path(args.sales_file).read_text(encoding="utf-8"))
        if isinstance(loaded, list):
            sales = loaded
    elif args.sales_json:
        loaded = json.loads(args.sales_json)
        if isinstance(loaded, list):
            sales = loaded
    result = classify_sales(sales)
    result["law_id"] = law.get("id")
    result["source_channel_id"] = law.get("source_channel_id")
    print(json.dumps(result, indent=2))
    print("", end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
