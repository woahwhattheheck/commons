#!/usr/bin/env python3
"""Classify catalog waitlist rows without writing instance doors.

Sidewalk Signal (TALLY) and LotRibbon Greetings (LEAD) do not host the
shared waitlist form. Harborline Local Sites already cites
packs/waitlist.html on its door. This helper only reads. It does not
overwrite those instance doors, packs/waitlist.html, or TALLY's desk
helper. Not a Commons gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LAW = ROOT / "ground" / "BUSINESS_PACKS.json"
UNIQUE_PACK_ID = "cursor-business-packs-unique-20260902-01"
CATALOG_ID = "cursor-business-pack-instance-catalog-20260902-01"
POINTER_ID = "cursor-business-pack-sidewalk-lotribbon-waitlist-pointer-20260902-01"
SHARED_WAITLIST = "packs/waitlist.html"
EXPECTED_BLOBS = {
    "packs/sidewalk-signal-web-desk-20260902-01/index.html": "638e60b4",
    "packs/lotribbon-greetings-20260902-01/index.html": "ac60db02",
    "packs/desk-website-service-20260902-01/door.html": "d3d6fcc7",
    "packs/waitlist.html": "bdcaa7ea",
    "host/business_pack_desk_instance.py": "a550ae1b",
}
WAITLIST_ON_INSTANCE_DOOR = "WAITLIST_ON_INSTANCE_DOOR"
WAITLIST_CATALOG_POINTER = "WAITLIST_CATALOG_POINTER"
WAITLIST_MISSING = "WAITLIST_MISSING"
WAITLIST_DOOR_MISSING = "WAITLIST_DOOR_MISSING"


def load_law(path: Path | None = None) -> dict[str, Any]:
    target = path or DEFAULT_LAW
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("law is not an object")
    return data


def instances_block(law: dict[str, Any]) -> dict[str, Any]:
    block = law.get("instances")
    return block if isinstance(block, dict) else {}


def door_has_waitlist_href(html: str) -> bool:
    return "waitlist.html" in html.lower()


def blob_prefix(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        return ""
    payload = path.read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()[:8]


def classify_row(row: dict[str, Any], html: str | None) -> str:
    waitlist = str(row.get("waitlist") or "").strip()
    if html is None:
        return WAITLIST_DOOR_MISSING
    on_door = door_has_waitlist_href(html)
    if waitlist == SHARED_WAITLIST and on_door:
        return WAITLIST_ON_INSTANCE_DOOR
    if waitlist == SHARED_WAITLIST and not on_door:
        return WAITLIST_CATALOG_POINTER
    return WAITLIST_MISSING


def classify_catalog(law: dict[str, Any] | None = None) -> dict[str, Any]:
    data = law if isinstance(law, dict) else load_law()
    block = instances_block(data)
    landed = block.get("landed")
    rows_out = []
    if isinstance(landed, list):
        for item in landed:
            if not isinstance(item, dict):
                continue
            rel = str(item.get("door") or "")
            path = ROOT / rel if rel else None
            html = path.read_text(encoding="utf-8") if path and path.is_file() else None
            rows_out.append(
                {
                    "brand": str(item.get("brand") or ""),
                    "door": rel,
                    "waitlist": str(item.get("waitlist") or ""),
                    "owned_by": str(item.get("owned_by") or ""),
                    "verdict": classify_row(item, html),
                    "door_blob": blob_prefix(rel) if rel else "",
                }
            )
    blobs = {rel: blob_prefix(rel) for rel in EXPECTED_BLOBS}
    blobs_match = all(blobs.get(rel, "").startswith(prefix) for rel, prefix in EXPECTED_BLOBS.items())
    verdicts = {row["brand"]: row["verdict"] for row in rows_out}
    pointer_ok = (
        str(data.get("id") or "") == UNIQUE_PACK_ID
        and str(block.get("id") or "") == CATALOG_ID
        and str(block.get("catalog_waitlist_rows_pointer") or "") == POINTER_ID
        and block.get("did_not_steal_instance_files") is True
        and block.get("did_not_overwrite_sidewalk_door") is True
        and block.get("did_not_overwrite_lotribbon_door") is True
        and block.get("did_not_overwrite_waitlist_html") is True
        and str(block.get("checkout") or "") == "NOT_MINTED"
        and data.get("gate") is False
        and data.get("commons_admission") is False
        and verdicts.get("LotRibbon Greetings") == WAITLIST_CATALOG_POINTER
        and verdicts.get("Sidewalk Signal") == WAITLIST_CATALOG_POINTER
        and verdicts.get("Harborline Local Sites") == WAITLIST_ON_INSTANCE_DOOR
        and blobs_match
    )
    return {
        "gate": False,
        "commons_admission": False,
        "id": POINTER_ID,
        "unique_pack_id": str(data.get("id") or ""),
        "catalog_id": str(block.get("id") or ""),
        "shared_waitlist": SHARED_WAITLIST,
        "checkout": str(block.get("checkout") or ""),
        "did_not_overwrite_sidewalk_door": block.get("did_not_overwrite_sidewalk_door") is True,
        "did_not_overwrite_lotribbon_door": block.get("did_not_overwrite_lotribbon_door") is True,
        "did_not_overwrite_waitlist_html": block.get("did_not_overwrite_waitlist_html") is True,
        "did_not_steal_instance_files": block.get("did_not_steal_instance_files") is True,
        "did_not_steal_desk_helper": block.get("did_not_steal_desk_helper") is True,
        "blobs": blobs,
        "blobs_match": blobs_match,
        "rows": rows_out,
        "pointer_ok": pointer_ok,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--law", default="", help="override unique-pack law path")
    args = parser.parse_args(argv)
    law = load_law(Path(args.law) if args.law else None)
    print(json.dumps(classify_catalog(law), indent=2))
    print("", end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
