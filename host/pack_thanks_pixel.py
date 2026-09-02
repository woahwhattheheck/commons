#!/usr/bin/env python3
"""Validate the shared pack thanks door. Empty X Pixel slot loads no third-party scripts.

SCOUT demand scout-demand-pack-door-thanks-pixel-20260902-01.
Does not mint a pixel ID, ads account, Payment Link, or spend.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
THANKS = ROOT / "packs" / "thanks.html"
CHECKOUT = ROOT / "packs" / "_template" / "checkout.md"
ALLOWED_VALUES = (20, 50, 100, 200, 1000, 10000)
PIXEL_META_RE = re.compile(
    r'<meta\s+name="x-pixel-id"\s+content="([^"]*)"',
    re.IGNORECASE,
)
SCRIPT_SRC_RE = re.compile(r"<script\b[^>]*\bsrc=['\"]([^'\"]+)['\"]", re.IGNORECASE)
EARNINGS_RE = re.compile(
    r"(?i)make \$\d|guaranteed income|passive income|quit your job|"
    r"results within a (?:period|week|weekend)|\$\d+ this weekend"
)
THIRD_PARTY_RE = re.compile(r"(?i)^https?://")


def parse_thanks(path: Path | None = None) -> dict[str, Any]:
    target = path or THANKS
    html = target.read_text(encoding="utf-8")
    match = PIXEL_META_RE.search(html)
    pixel = match.group(1).strip() if match else None
    srcs = SCRIPT_SRC_RE.findall(html)
    third = [src for src in srcs if THIRD_PARTY_RE.search(src)]
    return {
        "path": str(target),
        "pixel_id": pixel or "",
        "static_script_srcs": srcs,
        "third_party_scripts": third,
        "empty_slot": pixel == "",
        "empty_slot_loads_no_third_party": pixel == "" and third == [],
        "earnings_claim": bool(EARNINGS_RE.search(html)),
        "gate": False,
        "mint_pixel": False,
        "mint_checkout": False,
        "keep_shipping": True,
    }


def checkout_points_at_thanks(path: Path | None = None) -> bool:
    text = (path or CHECKOUT).read_text(encoding="utf-8")
    return "thanks.html" in text and "after-payment" in text.lower()


def filled_slot_would_purchase(html: str, value: int) -> dict[str, Any]:
    if value not in ALLOWED_VALUES:
        raise ValueError("tier value not allowed")
    patched = PIXEL_META_RE.sub(
        '<meta name="x-pixel-id" content="1234567890"',
        html,
        count=1,
    )
    return {
        "pixel_id": "1234567890",
        "static_third_party_scripts": [
            src
            for src in SCRIPT_SRC_RE.findall(patched)
            if THIRD_PARTY_RE.search(src)
        ],
        "injector_present": "static.ads-twitter.com/uwt.js" in patched
        and 'twq("event", "Purchase"' in patched,
        "value_allowed": value in ALLOWED_VALUES,
        "login_ask": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = parse_thanks()
    payload["checkout_redirect"] = checkout_points_at_thanks()
    if args.json:
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    else:
        sys.stdout.write(
            f"empty_slot_loads_no_third_party={payload['empty_slot_loads_no_third_party']} "
            f"checkout_redirect={payload['checkout_redirect']}\n"
        )
    ok = payload["empty_slot_loads_no_third_party"] and not payload["earnings_claim"]
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
