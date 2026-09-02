#!/usr/bin/env python3
"""SHIP unique-pack leftover cursor-owner-now-revenue-readback-20260902-01.

Independent MATCH leftover fe5ba035 #8343 ASK_FOR_SALE.
Did not remint leftover door/pay.js. Did not invent Stripe URLs.
Did not steal Harborline /harborline.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
HOST = Path(__file__).resolve().parent
SHIP_ID = "cursor-owner-now-revenue-readback-ship-20260902-01"
READBACK_ID = "cursor-owner-now-revenue-readback-20260902-01"
ASK_ID = "cursor-owner-now-revenue-20260902-01"
READBACK_LAND = "2d087a03e"
READBACK_BLOB = "3449da29"
LEFTOVER_BLOB = "fe5ba035"
LEFTOVER_PR = 8343
LEFTOVER_MERGE = "0674c9216"
READBACK_TEST = "c7d491e4"

KEEP = {
    f"p/{READBACK_ID}.md": READBACK_BLOB,
    "test_owner_now_revenue_readback.py": READBACK_TEST,
    f"p/{ASK_ID}.md": LEFTOVER_BLOB,
    "host/owner_now_revenue.py": "7e1ab768",
    "owner-now-revenue.html": "1d3f1cdf",
    "land/owner-now-revenue-20260902.md": "db81f250",
    "test_owner_now_revenue.py": "05b8ec2a",
    "pay.js": "65a960f2",
    "ground/OWNER_NOW.md": "59b1fd37",
    "p/cursor-owner-now-readback-20260902-01.md": "1b3cd631",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
}

HARBORLINE_STEAL = (
    "harborline",
    "qualify.html",
    "host/harborline_pack_market_render.py",
)


def _load_leftover():
    spec = importlib.util.spec_from_file_location(
        "owner_now_revenue", HOST / "owner_now_revenue.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git_blob(rel: str, root: Path | None = None) -> str:
    path = (root or ROOT) / rel
    return subprocess.check_output(
        ["git", "hash-object", str(path)], text=True
    ).strip()


def leftover_readback_match(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    blobs = {rel: git_blob(rel, base) for rel in KEEP}
    ok = all(blobs[rel].startswith(prefix) for rel, prefix in KEEP.items())
    receipt = (base / f"p/{READBACK_ID}.md").read_text(encoding="utf-8")
    leftover = (base / f"p/{ASK_ID}.md").read_text(encoding="utf-8")
    harborline_absent = not (base / "harborline").exists()
    qualify_absent = not (base / "qualify.html").exists()
    ok = (
        ok
        and LEFTOVER_MERGE in receipt
        and LEFTOVER_BLOB in receipt
        and ASK_ID in receipt
        and (
            "Did not invent Stripe URLs" in receipt
            or "Did **not** invent Stripe URLs" in receipt
        )
        and (
            "Did not remint leftover door" in receipt
            or "Did **not** remint leftover door" in receipt
        )
        and "ASK_FOR_SALE" in leftover
        and harborline_absent
        and qualify_absent
        and receipt != leftover
    )
    return {
        "ok": ok,
        "leftover_land": READBACK_LAND,
        "leftover_blob": blobs[f"p/{READBACK_ID}.md"],
        "leftover_receipt_blob": blobs[f"p/{ASK_ID}.md"],
        "leftover_pr": LEFTOVER_PR,
        "leftover_merge": LEFTOVER_MERGE,
        "did_not_remint_leftover_door": blobs["owner-now-revenue.html"].startswith(
            "1d3f1cdf"
        ),
        "did_not_remint_pay_js": blobs["pay.js"].startswith("65a960f2"),
        "did_not_remint_leftover_helper": blobs["host/owner_now_revenue.py"].startswith(
            "d78f949f"
        ),
        "did_not_remint_owner_card": blobs["ground/OWNER_NOW.md"].startswith("59b1fd37"),
        "did_not_steal_harborline": harborline_absent,
        "harborline_path_absent": harborline_absent,
        "qualify_absent": qualify_absent,
        "blobs": blobs,
    }


def ask_for_sale(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    match = leftover_readback_match(base)
    leftover = _load_leftover().ask_for_sale(base)
    rails = leftover.get("ask_for_sale") or []
    verdict = (
        "ASK_FOR_SALE"
        if match["ok"] and leftover.get("verdict") == "ASK_FOR_SALE" and rails
        else "NOT_LANDED"
    )
    return {
        "kind": "OWNER_NOW_REVENUE_READBACK_SHIP",
        "id": SHIP_ID,
        "leftover_id": READBACK_ID,
        "leftover_ask_id": ASK_ID,
        "gate": False,
        "commons_admission": False,
        "verdict": verdict,
        "point": "generate revenue",
        "leftover_readback_match": match,
        "chargeable": bool(leftover.get("chargeable") and rails),
        "ask_for_sale": rails,
        "sku_count": leftover.get("sku_count"),
        "cash_usd": leftover.get("cash_usd"),
        "authorization": leftover.get("authorization"),
        "bank_available": leftover.get("bank_available"),
        "invented_stripe_urls": False,
        "new_stripe_mint": "EXTERNAL_PROVIDER_ACTION",
        "not_minted_is_freeze": False,
        "checkout": "NOT_MINTED",
        "did_not_remint_leftover_door": match["did_not_remint_leftover_door"],
        "did_not_remint_pay_js": match["did_not_remint_pay_js"],
        "did_not_steal_harborline": match["did_not_steal_harborline"],
        "did_not_ack_hourly": True,
        "sends": 0,
        "door": leftover.get("door"),
        "pay_door": leftover.get("pay_door"),
        "leftover_pr": LEFTOVER_PR,
        "leftover_land": READBACK_LAND,
        "leftover_blob": READBACK_BLOB,
        "leftover_receipt_blob": LEFTOVER_BLOB,
        "harborline_steal": list(HARBORLINE_STEAL),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SHIP unique-pack leftover OWNER_NOW revenue readback"
    )
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--url",
        default="",
        help="Refuse if this Stripe URL is not a canonical recorded rail",
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    packet = ask_for_sale(root)
    leftover = _load_leftover()
    if args.url:
        capability = leftover._load_checkout()
        projected = capability.measure_root(str(root)).get("projected") or {}
        check = leftover.refuse_invented(args.url, projected)
        packet["url_check"] = check
        if check["invented"]:
            packet["verdict"] = "INVENTED_REFUSED"
            packet["invented_stripe_urls"] = True
    json.dump(packet, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if packet.get("verdict") == "ASK_FOR_SALE" else 1


if __name__ == "__main__":
    sys.exit(main())
