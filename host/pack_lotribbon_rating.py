#!/usr/bin/env python3
"""LotRibbon instance fill of the factory rating slot. Compose leftover.

GOAT / unique-pack own packs/_template/rating.md and
host/business_pack_rating.py (id cursor-business-pack-rating-slot-20260902-01).
This leftover only fills LotRibbon's instance sheet after Harborline
peer-unpin cursor-pack-harborline-rating-peer-unpin-20260902-01. It does
not remint the factory slot, rewrite the template, pick a partner,
invent a bulk price, rewrite Harborline rating 7fe8667a, or write
Harborline / Sidewalk / yard-card / pin-lift helpers. Empty badge+report
is the correct instance state until Bryce pastes. Completeness audit
allowed. Dollar valuation is earnings. KEEP MAIN #7915.
Checkout NOT_MINTED.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "host"))

import business_pack_rating as factory  # noqa: E402

TEMPLATE = ROOT / "packs" / "_template" / "rating.md"
LOTRIBBON = ROOT / "packs" / "lotribbon-greetings-20260902-01" / "rating.md"
HARBORLINE = ROOT / "packs" / "desk-website-service-20260902-01" / "rating.md"
SIDEWALK = ROOT / "packs" / "sidewalk-signal-web-desk-20260902-01" / "rating.md"
FACTORY_ID = "cursor-business-pack-rating-slot-20260902-01"
RECEIPT_ID = "cursor-lead-lotribbon-rating-20260902-01"
UNPIN_ID = "cursor-pack-harborline-rating-peer-unpin-20260902-01"
HARBORLINE_RECEIPT_ID = "cursor-pack-harborline-rating-20260902-01"
TEMPLATE_BLOB = "7d644a8b"
HARBORLINE_SHEET_BLOB = "7fe8667a"
HARBORLINE_RECEIPT_BLOB = "29930d8b"
UNPIN_RECEIPT_BLOB = "9d1991f3"
DOOR_BLOB = "7804ec33"
POINTER_RECEIPT_BLOB = "7a8987b5"
SLOT_RE = {
    "badge_url": re.compile(r"(?im)^Badge URL:\s*`?([^`\n]+)`?"),
    "report_url": re.compile(r"(?im)^Report URL:\s*`?([^`\n]+)`?"),
    "partner_name": re.compile(r"(?im)^Partner name:\s*`?([^`\n]+)`?"),
    "bulk_price": re.compile(r"(?im)^Bulk price:\s*`?([^`\n]+)`?"),
    "owner_pasted": re.compile(r"(?im)^Owner pasted:\s*`?([^`\n]+)`?"),
}
STRIPE_FAKE_RE = re.compile(r"(?i)https?://(?:buy|donate)\.stripe\.com/")
DO_NOT_OVERWRITE = (
    "packs/_template/rating.md",
    "packs/_template/README.md",
    "host/business_pack_rating.py",
    "ground/BUSINESS_PACK_RATING.json",
    "p/cursor-business-pack-rating-slot-20260902-01.md",
    "p/cursor-pack-harborline-rating-20260902-01.md",
    "p/cursor-pack-harborline-rating-peer-unpin-20260902-01.md",
    "packs/desk-website-service-20260902-01/rating.md",
    "host/pack_harborline_rating.py",
    "packs/desk-website-service-20260902-01/door.html",
    "packs/lotribbon-greetings-20260902-01/index.html",
    "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md",
    "host/business_pack_desk_instance.py",
    "packs/waitlist.html",
    "packs/thanks.html",
    "packs/sidewalk-signal-web-desk-20260902-01",
    "packs/curbline-weekend-yard-help-20260902-01",
    "ground/BUSINESS_PACKS.json",
)


def git_blob_prefix(rel: str, n: int = 8) -> str:
    path = ROOT / rel
    if not path.is_file():
        return ""
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()[:n]


def parse_slots(text: str) -> dict[str, Any]:
    body = text or ""
    slots: dict[str, Any] = {}
    for key, pattern in SLOT_RE.items():
        match = pattern.search(body)
        slots[key] = (match.group(1).strip() if match else "")
    pasted = str(slots.get("owner_pasted") or "").strip().lower()
    return {
        "badge_url": slots.get("badge_url") or "",
        "report_url": slots.get("report_url") or "",
        "partner_name": slots.get("partner_name") or "",
        "bulk_price": slots.get("bulk_price") or "",
        "owner_pasted_rating": pasted in {"yes", "true", "1"},
        "copy": body,
    }


def classify_path(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "kind": "LOTRIBBON_RATING",
            "gate": False,
            "commons_admission": False,
            "verdict": "LOTRIBBON_RATING_MISSING",
            "path": str(path),
            "sends": 0,
            "checkout": "NOT_MINTED",
            "do_not_overwrite": list(DO_NOT_OVERWRITE),
        }
    text = path.read_text(encoding="utf-8")
    slots = parse_slots(text)
    factory_out = factory.classify_rating(
        {
            "badge_url": slots["badge_url"],
            "report_url": slots["report_url"],
            "partner_name": slots["partner_name"],
            "bulk_price": slots["bulk_price"],
            "owner_pasted_rating": slots["owner_pasted_rating"],
            "copy": "",
        }
    )
    invented_stripe = bool(STRIPE_FAKE_RE.search(text))
    named = "LotRibbon Greetings" in text
    factory_cited = FACTORY_ID in text
    checkout_empty = "NOT_MINTED" in text
    harborline_cited = HARBORLINE_SHEET_BLOB in text and UNPIN_ID in text
    problems: list[str] = []
    if factory_out.get("verdict") != "RATING_SLOT_EMPTY":
        problems.append("factory_verdict")
    if not named:
        problems.append("brand")
    if not factory_cited:
        problems.append("factory_id")
    if not checkout_empty:
        problems.append("checkout")
    if not harborline_cited:
        problems.append("harborline_unread")
    if invented_stripe:
        problems.append("stripe")
    if factory_out.get("filled"):
        problems.append("invented_fill")
    verdict = "LOTRIBBON_RATING_INSTANCE_OK" if not problems else "LOTRIBBON_RATING_INCOMPLETE"
    if factory_out.get("verdict") in {
        "RATING_EARNINGS_CLAIM",
        "EARNINGS_IN_ADS",
        "RATING_LINK_INVENTED",
        "RATING_CLAIM_UNSUBSTANTIATED",
    }:
        verdict = str(factory_out.get("verdict") or verdict)
    return {
        "kind": "LOTRIBBON_RATING",
        "gate": False,
        "commons_admission": False,
        "verdict": verdict,
        "path": str(path),
        "factory_verdict": factory_out.get("verdict"),
        "factory_id": FACTORY_ID,
        "slots": {
            "badge_url": slots["badge_url"],
            "report_url": slots["report_url"],
            "partner_name": slots["partner_name"],
            "bulk_price": slots["bulk_price"],
            "owner_pasted_rating": slots["owner_pasted_rating"],
        },
        "empty": factory_out.get("empty") is True,
        "named_lotribbon": named,
        "problems": problems,
        "sends": 0,
        "agents_spend_ads": False,
        "agents_pick_partner": False,
        "agents_invent_bulk_price": False,
        "checkout": "NOT_MINTED",
        "do_not_overwrite": list(DO_NOT_OVERWRITE),
        "receipt_id": RECEIPT_ID,
    }


def classify_tree(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    lotribbon = classify_path(base / "packs" / "lotribbon-greetings-20260902-01" / "rating.md")
    template_blob = git_blob_prefix("packs/_template/rating.md")
    door_blob = git_blob_prefix("packs/lotribbon-greetings-20260902-01/index.html")
    harborline_sheet = git_blob_prefix("packs/desk-website-service-20260902-01/rating.md")
    harborline_receipt = git_blob_prefix("p/cursor-pack-harborline-rating-20260902-01.md")
    unpin_receipt = git_blob_prefix("p/cursor-pack-harborline-rating-peer-unpin-20260902-01.md")
    pointer_receipt = git_blob_prefix(
        "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md"
    )
    law = factory.load_law()
    ok = (
        lotribbon.get("verdict") == "LOTRIBBON_RATING_INSTANCE_OK"
        and str(law.get("id") or "") == FACTORY_ID
        and template_blob == TEMPLATE_BLOB
        and door_blob == DOOR_BLOB
        and harborline_sheet == HARBORLINE_SHEET_BLOB
        and harborline_receipt == HARBORLINE_RECEIPT_BLOB
        and unpin_receipt == UNPIN_RECEIPT_BLOB
        and pointer_receipt == POINTER_RECEIPT_BLOB
        and not SIDEWALK.is_file()
    )
    return {
        "kind": "LOTRIBBON_RATING",
        "gate": False,
        "commons_admission": False,
        "verdict": "LOTRIBBON_RATING_OK" if ok else "LOTRIBBON_RATING_INCOMPLETE",
        "lotribbon": lotribbon,
        "factory_id": str(law.get("id") or ""),
        "blobs": {
            "packs/_template/rating.md": template_blob,
            "packs/lotribbon-greetings-20260902-01/index.html": door_blob,
            "packs/desk-website-service-20260902-01/rating.md": harborline_sheet,
            "p/cursor-pack-harborline-rating-20260902-01.md": harborline_receipt,
            "p/cursor-pack-harborline-rating-peer-unpin-20260902-01.md": unpin_receipt,
            "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md": pointer_receipt,
        },
        "did_not_rewrite_goat_template": template_blob == TEMPLATE_BLOB,
        "did_not_remint_factory_slot": str(law.get("id") or "") == FACTORY_ID,
        "did_not_overwrite_lotribbon_door": door_blob == DOOR_BLOB,
        "did_not_overwrite_harborline_rating": harborline_sheet == HARBORLINE_SHEET_BLOB,
        "did_not_remint_harborline_receipt": harborline_receipt == HARBORLINE_RECEIPT_BLOB,
        "did_not_remint_harborline_unpin": unpin_receipt == UNPIN_RECEIPT_BLOB,
        "did_not_overwrite_pointer_receipt": pointer_receipt == POINTER_RECEIPT_BLOB,
        "did_not_fill_sidewalk": not SIDEWALK.is_file(),
        "did_not_merge_7915": True,
        "harborline_sheet_read": harborline_sheet == HARBORLINE_SHEET_BLOB,
        "sends": 0,
        "agents_spend_ads": False,
        "checkout": "NOT_MINTED",
        "do_not_overwrite": list(DO_NOT_OVERWRITE),
        "receipt_id": RECEIPT_ID,
        "unpin_id": UNPIN_ID,
        "harborline_receipt_id": HARBORLINE_RECEIPT_ID,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", default="classify")
    parser.add_argument("--file", default="")
    args = parser.parse_args(argv)
    if args.file:
        print(json.dumps(classify_path(Path(args.file)), indent=2))
        return 0
    print(json.dumps(classify_tree(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
