#!/usr/bin/env python3
"""Leftover: lift live peer pins on Harborline rating helper.

CLAIM cursor-pack-harborline-rating-peer-unpin-20260902-01. Seat
bc-31c8ef9a. Harborline sheet 7fe8667a unread. Leftover receipt
cursor-pack-harborline-rating-20260902-01 blob 29930d8b not reminted.
LotRibbon rating.md not filled. pack_harborline_rating.py peer blob and
peer-absence pins become land-time observations. Pointer receipt
7a8987b5 KEEP MAIN (#7915 not merged). Checkout NOT_MINTED.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "host"))

import pack_harborline_rating as leftover  # noqa: E402

UNPIN_ID = "cursor-pack-harborline-rating-peer-unpin-20260902-01"
LEFTOVER_ID = leftover.RECEIPT_ID
FACTORY_ID = leftover.FACTORY_ID
THIS_SEAT_PATHS = leftover.THIS_SEAT_PATHS
DO_NOT_WRITE = leftover.DO_NOT_OVERWRITE


def classify_unpin() -> dict[str, Any]:
    tree = leftover.classify_tree()
    leftover_receipt = leftover.git_blob_prefix(f"p/{LEFTOVER_ID}.md")
    harborline_sheet = leftover.git_blob_prefix(leftover.HARBORLINE_REL)
    pointer_receipt = leftover.git_blob_prefix(leftover.POINTER_RECEIPT_REL)
    unpin_ok = (
        tree.get("verdict") == "HARBORLINE_RATING_OK"
        and tree.get("live_peer_blobs_not_pinned") is True
        and tree.get("peer_absence_not_pinned") is True
        and tree.get("did_not_fill_lotribbon") is True
        and tree.get("did_not_rewrite_harborline_sheet") is True
        and tree.get("did_not_overwrite_pointer_receipt") is True
        and tree.get("did_not_merge_7915") is True
        and leftover_receipt.startswith(leftover.LEFTOVER_RECEIPT_BLOB)
        and harborline_sheet.startswith(leftover.HARBORLINE_SHEET_BLOB)
        and leftover.LOTRIBBON_REL not in THIS_SEAT_PATHS
        and leftover.HARBORLINE_REL not in THIS_SEAT_PATHS
        and leftover.POINTER_RECEIPT_REL not in THIS_SEAT_PATHS
        and leftover.HARBORLINE_REL in leftover.OBSERVED_AT_LAND
        and leftover.POINTER_RECEIPT_REL in leftover.OBSERVED_AT_LAND
        and leftover.LOTRIBBON_REL in leftover.PEER_ABSENCE_AT_LAND
        and leftover.LOTRIBBON_REL not in leftover.EXPECTED_BLOBS
        and leftover.POINTER_RECEIPT_REL not in leftover.EXPECTED_BLOBS
        and str(tree.get("checkout") or "") == "NOT_MINTED"
        and (ROOT / "p" / f"{UNPIN_ID}.md").is_file()
        and (ROOT / "p" / f"{LEFTOVER_ID}.md").is_file()
        and f"p/{LEFTOVER_ID}.md" not in THIS_SEAT_PATHS
    )
    return {
        "kind": "HARBORLINE_RATING_PEER_UNPIN",
        "gate": False,
        "commons_admission": False,
        "id": UNPIN_ID,
        "leftover_id": LEFTOVER_ID,
        "factory_id": FACTORY_ID,
        "verdict": "HARBORLINE_RATING_PEER_UNPIN_OK" if unpin_ok else "HARBORLINE_RATING_PEER_UNPIN_INCOMPLETE",
        "unpin_ok": unpin_ok,
        "live_peer_blobs_not_pinned": tree.get("live_peer_blobs_not_pinned") is True,
        "peer_absence_not_pinned": tree.get("peer_absence_not_pinned") is True,
        "did_not_fill_lotribbon": leftover.LOTRIBBON_REL not in THIS_SEAT_PATHS,
        "did_not_rewrite_harborline_sheet": leftover.HARBORLINE_REL not in THIS_SEAT_PATHS,
        "did_not_remint_leftover_receipt": leftover_receipt.startswith(
            leftover.LEFTOVER_RECEIPT_BLOB
        ),
        "did_not_overwrite_pointer_receipt": leftover.POINTER_RECEIPT_REL
        not in THIS_SEAT_PATHS,
        "did_not_merge_7915": True,
        "observed_at_land": dict(leftover.OBSERVED_AT_LAND),
        "peer_absence_at_land": list(leftover.PEER_ABSENCE_AT_LAND),
        "blobs": {
            f"p/{LEFTOVER_ID}.md": leftover_receipt,
            leftover.HARBORLINE_REL: harborline_sheet,
            leftover.POINTER_RECEIPT_REL: pointer_receipt,
        },
        "checkout": "NOT_MINTED",
        "this_seat_paths": list(THIS_SEAT_PATHS),
        "do_not_write": list(DO_NOT_WRITE),
        "agents_spend_ads": False,
        "no_auth": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    print(json.dumps(classify_unpin(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
