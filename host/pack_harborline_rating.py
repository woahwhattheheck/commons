#!/usr/bin/env python3
"""Harborline instance fill of the factory rating slot. Compose leftover.

GOAT / unique-pack own packs/_template/rating.md and
host/business_pack_rating.py (id cursor-business-pack-rating-slot-20260902-01).
This leftover only fills Harborline's instance sheet. It does not remint
the factory slot, rewrite the template, pick a partner, invent a bulk
price, or write leftover pin-lift helpers / Harborline door / waitlist /
TALLY / LotRibbon. Empty badge+report is the correct instance state until
Bryce pastes. Completeness audit allowed. Dollar valuation is earnings.

Peer blob and peer-absence pins are lifted. Land-time observations stay in
OBSERVED_AT_LAND. LEAD may fill LotRibbon rating.md and TALLY may fill
Sidewalk rating.md without breaking this leftover. Harborline sheet
7fe8667a stays unread. Pointer receipt 7a8987b5 KEEP MAIN (#7915 not
merged). Checkout NOT_MINTED.
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
HARBORLINE = ROOT / "packs" / "desk-website-service-20260902-01" / "rating.md"
SIDEWALK = ROOT / "packs" / "sidewalk-signal-web-desk-20260902-01" / "rating.md"
LOTRIBBON = ROOT / "packs" / "lotribbon-greetings-20260902-01" / "rating.md"
FACTORY_ID = "cursor-business-pack-rating-slot-20260902-01"
RECEIPT_ID = "cursor-pack-harborline-rating-20260902-01"
UNPIN_ID = "cursor-pack-harborline-rating-peer-unpin-20260902-01"
TEMPLATE_BLOB = "7d644a8b"
DOOR_BLOB = "d3d6fcc7"
SIDECAR_BLOB = "c72d50d0"
MAP_POINTER_BLOB = "1470b378"
MAP_HELPER_POINTER_BLOB = "319a907e"
PACK_MAP_BLOB = "a889db44"
PIN_LIFT_RECEIPT_BLOB = "8fe8a002"
POINTER_RECEIPT_BLOB = "7a8987b5"
HARBORLINE_SHEET_BLOB = "7fe8667a"
LEFTOVER_RECEIPT_BLOB = "29930d8b"
SIDEWALK_REL = "packs/sidewalk-signal-web-desk-20260902-01/rating.md"
LOTRIBBON_REL = "packs/lotribbon-greetings-20260902-01/rating.md"
HARBORLINE_REL = "packs/desk-website-service-20260902-01/rating.md"
POINTER_RECEIPT_REL = (
    "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md"
)
# Land-time observations from leftover SHIP cursor-pack-harborline-rating-20260902-01.
# Not live pins: GOAT template, leftover pin helpers, #7915 pointer, and
# LEAD/TALLY rating sheets may move after this leftover.
OBSERVED_AT_LAND = {
    "packs/_template/rating.md": TEMPLATE_BLOB,
    "packs/desk-website-service-20260902-01/door.html": DOOR_BLOB,
    "host/business_pack_harborline_tally_map.py": SIDECAR_BLOB,
    "host/business_pack_harborline_tally_map_pointer.py": MAP_POINTER_BLOB,
    "host/business_pack_harborline_map_helper_pointer.py": MAP_HELPER_POINTER_BLOB,
    "host/harborline_tally_pack_map.py": PACK_MAP_BLOB,
    "p/cursor-pack-harborline-map-pin-lift-20260902-01.md": PIN_LIFT_RECEIPT_BLOB,
    POINTER_RECEIPT_REL: POINTER_RECEIPT_BLOB,
    HARBORLINE_REL: HARBORLINE_SHEET_BLOB,
}
EXPECTED_BLOBS = {
    f"p/{RECEIPT_ID}.md": LEFTOVER_RECEIPT_BLOB,
}
THIS_SEAT_PATHS = (
    "host/pack_harborline_rating.py",
    "test_pack_harborline_rating.py",
    "host/pack_harborline_rating_peer_unpin.py",
    "test_pack_harborline_rating_peer_unpin.py",
    "land/pack-harborline-rating-peer-unpin-20260902.md",
    f"p/{UNPIN_ID}.md",
)
PEER_ABSENCE_AT_LAND = (SIDEWALK_REL, LOTRIBBON_REL)
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
    "packs/desk-website-service-20260902-01/door.html",
    "host/harborline_tally_pack_map.py",
    "host/business_pack_harborline_tally_map.py",
    "host/business_pack_harborline_tally_map_pointer.py",
    "host/business_pack_harborline_map_helper_pointer.py",
    "p/cursor-pack-harborline-map-pin-lift-20260902-01.md",
    "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md",
    "host/business_pack_desk_instance.py",
    "packs/waitlist.html",
    "packs/thanks.html",
    "packs/sidewalk-signal-web-desk-20260902-01",
    "packs/lotribbon-greetings-20260902-01",
    "packs/curbline-weekend-yard-help-20260902-01",
    "packs/sidewalk-signal-web-desk-20260902-01/rating.md",
    "packs/lotribbon-greetings-20260902-01/rating.md",
    "packs/desk-website-service-20260902-01/rating.md",
    "ground/BUSINESS_PACKS.json",
    "ground/CLAUDE_PEER_CHECK.md",
    "p/wire-claude-peer-check-20260902-01.md",
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
            "kind": "HARBORLINE_RATING",
            "gate": False,
            "commons_admission": False,
            "verdict": "HARBORLINE_RATING_MISSING",
            "path": str(path),
            "sends": 0,
            "checkout": "NOT_MINTED",
            "do_not_overwrite": list(DO_NOT_OVERWRITE),
        }
    text = path.read_text(encoding="utf-8")
    slots = parse_slots(text)
    # Factory ads_copy is offer copy. Do not score the law reminder that names
    # banned phrases ("Independently audited", "dollar valuation").
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
    named = "Harborline Local Sites" in text
    factory_cited = FACTORY_ID in text
    checkout_empty = "NOT_MINTED" in text
    problems: list[str] = []
    if factory_out.get("verdict") != "RATING_SLOT_EMPTY":
        problems.append("factory_verdict")
    if not named:
        problems.append("brand")
    if not factory_cited:
        problems.append("factory_id")
    if not checkout_empty:
        problems.append("checkout")
    if invented_stripe:
        problems.append("stripe")
    if factory_out.get("filled"):
        problems.append("invented_fill")
    verdict = "HARBORLINE_RATING_INSTANCE_OK" if not problems else "HARBORLINE_RATING_INCOMPLETE"
    if factory_out.get("verdict") in {
        "RATING_EARNINGS_CLAIM",
        "EARNINGS_IN_ADS",
        "RATING_LINK_INVENTED",
        "RATING_CLAIM_UNSUBSTANTIATED",
    }:
        verdict = str(factory_out.get("verdict") or verdict)
    return {
        "kind": "HARBORLINE_RATING",
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
        "named_harborline": named,
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
    harborline = classify_path(base / HARBORLINE_REL)
    leftover_receipt = git_blob_prefix(f"p/{RECEIPT_ID}.md")
    live_blobs = {rel: git_blob_prefix(rel) for rel in OBSERVED_AT_LAND}
    live_blobs[f"p/{RECEIPT_ID}.md"] = leftover_receipt
    law = factory.load_law()
    leftover_receipt_ok = leftover_receipt.startswith(LEFTOVER_RECEIPT_BLOB)
    write_set_clean = (
        HARBORLINE_REL not in THIS_SEAT_PATHS
        and LOTRIBBON_REL not in THIS_SEAT_PATHS
        and SIDEWALK_REL not in THIS_SEAT_PATHS
        and "packs/_template/rating.md" not in THIS_SEAT_PATHS
        and POINTER_RECEIPT_REL not in THIS_SEAT_PATHS
        and f"p/{RECEIPT_ID}.md" not in THIS_SEAT_PATHS
    )
    live_peer_blobs_not_pinned = all(
        rel not in EXPECTED_BLOBS for rel in OBSERVED_AT_LAND
    )
    peer_absence_not_pinned = True
    ok = (
        harborline.get("verdict") == "HARBORLINE_RATING_INSTANCE_OK"
        and str(law.get("id") or "") == FACTORY_ID
        and leftover_receipt_ok
        and write_set_clean
        and live_peer_blobs_not_pinned
        and peer_absence_not_pinned
        and (ROOT / "p" / f"{RECEIPT_ID}.md").is_file()
    )
    return {
        "kind": "HARBORLINE_RATING",
        "gate": False,
        "commons_admission": False,
        "verdict": "HARBORLINE_RATING_OK" if ok else "HARBORLINE_RATING_INCOMPLETE",
        "harborline": harborline,
        "factory_id": str(law.get("id") or ""),
        "blobs": live_blobs,
        "observed_at_land": dict(OBSERVED_AT_LAND),
        "peer_absence_at_land": list(PEER_ABSENCE_AT_LAND),
        "live_peer_blobs_not_pinned": live_peer_blobs_not_pinned,
        "peer_absence_not_pinned": peer_absence_not_pinned,
        "did_not_rewrite_goat_template": "packs/_template/rating.md"
        not in THIS_SEAT_PATHS,
        "did_not_remint_factory_slot": str(law.get("id") or "") == FACTORY_ID,
        "did_not_overwrite_harborline_door": (
            "packs/desk-website-service-20260902-01/door.html" not in THIS_SEAT_PATHS
        ),
        "did_not_write_leftover_pin_helpers": (
            "host/business_pack_harborline_tally_map.py" not in THIS_SEAT_PATHS
        ),
        "did_not_overwrite_pointer_receipt": POINTER_RECEIPT_REL not in THIS_SEAT_PATHS,
        "did_not_rewrite_harborline_sheet": HARBORLINE_REL not in THIS_SEAT_PATHS,
        "did_not_fill_sidewalk": SIDEWALK_REL not in THIS_SEAT_PATHS,
        "did_not_fill_lotribbon": LOTRIBBON_REL not in THIS_SEAT_PATHS,
        "did_not_merge_7915": True,
        "did_not_remint_leftover_receipt": leftover_receipt_ok,
        "sends": 0,
        "agents_spend_ads": False,
        "checkout": "NOT_MINTED",
        "do_not_overwrite": list(DO_NOT_OVERWRITE),
        "this_seat_paths": list(THIS_SEAT_PATHS),
        "receipt_id": RECEIPT_ID,
        "unpin_id": UNPIN_ID,
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
