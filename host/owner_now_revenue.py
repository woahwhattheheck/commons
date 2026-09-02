#!/usr/bin/env python3
"""OWNER_NOW leftover: generate revenue from proven rails. Not a Commons gate.

Independently MATCH leftover cursor-owner-now-readback-20260902-01.
Ask for the sale on CHARGEABLE canonical Stripe SKUs.
Do not invent Stripe URLs. New Payment Links stay EXTERNAL_PROVIDER_ACTION
until a private connector mints one. NOT_MINTED is a measurement, not a freeze.
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
OWNER_CARD = "ground/OWNER_NOW.md"
LEFTOVER = "p/cursor-owner-now-readback-20260902-01.md"
DOOR = "owner-now-revenue.html"
OWNER_PREFIX = "6b8ee988"
LEFTOVER_PREFIX = "1b3cd631"
LEFTOVER_LAND = "348ffcc2a"
STRIPE_HOSTS = ("buy.stripe.com", "donate.stripe.com")


def _load_checkout():
    spec = importlib.util.spec_from_file_location(
        "checkout_capability", HOST / "checkout_capability.py"
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


def leftover_match(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    owner = git_blob(OWNER_CARD, base)
    leftover = git_blob(LEFTOVER, base)
    card = (base / OWNER_CARD).read_text(encoding="utf-8")
    receipt = (base / LEFTOVER).read_text(encoding="utf-8")
    ok = (
        leftover.startswith(LEFTOVER_PREFIX)
        and "Point is generate revenue" in card
        and "NOT_MINTED as a freeze" in card
        and "invented 337 closer was never Bryce law" in card
        and "Did not invent Stripe URLs" in receipt
        and OWNER_PREFIX in receipt
        and "cursor-owner-now-readback-20260902-01" in receipt
    )
    return {
        "ok": ok,
        "owner_now_blob": owner,
        "leftover_blob": leftover,
        "owner_now_prefix": OWNER_PREFIX,
        "leftover_prefix": LEFTOVER_PREFIX,
        "leftover_land": LEFTOVER_LAND,
        "did_not_remint_owner_card": owner.startswith(OWNER_PREFIX),
        "did_not_remint_leftover": leftover.startswith(LEFTOVER_PREFIX),
    }


def looks_like_stripe_checkout(url: str) -> bool:
    if not url.startswith("https://"):
        return False
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.hostname in STRIPE_HOSTS and bool(parsed.path.strip("/"))


def canonical_urls(projected: dict[str, Any]) -> set[str]:
    urls = set()
    for row in projected.get("public_rails") or []:
        stored = str(row.get("stored_url") or "").strip()
        if stored:
            urls.add(stored)
        live = str(row.get("url") or "").strip()
        if live:
            urls.add(live)
    return urls


def refuse_invented(url: str, projected: dict[str, Any]) -> dict[str, Any]:
    allowed = canonical_urls(projected)
    invented = looks_like_stripe_checkout(url) and url not in allowed
    return {
        "url": url,
        "invented": invented,
        "verdict": "INVENTED_REFUSED" if invented else "CANONICAL",
        "allowed": sorted(allowed),
    }


def ask_for_sale(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    match = leftover_match(base)
    capability = _load_checkout()
    measured = capability.measure_root(str(base))
    projected = measured.get("projected") or {}
    rails = []
    for row in projected.get("public_rails") or []:
        if not row.get("chargeable"):
            continue
        url = str(row.get("url") or row.get("stored_url") or "")
        if not url or url not in canonical_urls(projected):
            continue
        rails.append(
            {
                "sku": row.get("sku"),
                "url": url,
                "public": row.get("public"),
                "ask": "ASK_FOR_SALE",
            }
        )
    not_minted_freeze = False
    verdict = "ASK_FOR_SALE" if match["ok"] and rails else "NOT_LANDED"
    return {
        "kind": "OWNER_NOW_REVENUE",
        "id": "cursor-owner-now-revenue-20260902-01",
        "gate": False,
        "commons_admission": False,
        "verdict": verdict,
        "point": "generate revenue",
        "leftover_match": match,
        "chargeable": bool(projected.get("account_ready") and rails),
        "ask_for_sale": rails,
        "sku_count": len(rails),
        "cash_usd": projected.get("collected_cash_usd"),
        "authorization": projected.get("authorization"),
        "bank_available": projected.get("bank_available"),
        "invented_stripe_urls": False,
        "new_stripe_mint": "EXTERNAL_PROVIDER_ACTION",
        "not_minted_is_freeze": not_minted_freeze,
        "did_not_ack_hourly": True,
        "sends": 0,
        "door": DOOR,
        "pay_door": "pay.html",
        "checkout_errors": measured.get("errors") or [],
        "checkout_state": measured.get("state"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ask for the sale on proven OWNER_NOW rails"
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
    if args.url:
        capability = _load_checkout()
        projected = capability.measure_root(str(root)).get("projected") or {}
        check = refuse_invented(args.url, projected)
        packet["url_check"] = check
        if check["invented"]:
            packet["verdict"] = "INVENTED_REFUSED"
            packet["invented_stripe_urls"] = True
    if args.json or True:
        json.dump(packet, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0 if packet.get("verdict") == "ASK_FOR_SALE" else 1


if __name__ == "__main__":
    sys.exit(main())
