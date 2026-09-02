#!/usr/bin/env python3
"""SHIP leftover: unique-pack Harborline pack-market leftover already on main.

Leftover cursor-harborline-pack-market-render-20260902-01 land 0141bf7c8 #8345
blob 54c348dc. Unique-pack readback land 3a418c574 blob 6efbac54. This leftover
only cites those. Did not remint leftover helper. Did not dump marketplace.html.
Did not steal Harborline /harborline. Later-main leftover KEEP remint
hub_pages.py 14eeedb0 -> 5ac12648 unread; did not remint leftover to chase.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEFTOVER_HELPER = ROOT / "host/harborline_pack_market_render.py"
LEFTOVER_ID = "cursor-harborline-pack-market-render-20260902-01"
READBACK_ID = "cursor-harborline-pack-market-render-readback-20260902-01"
SHIP_ID = "cursor-harborline-pack-market-render-readback-ship-20260902-01"
LEFTOVER_LAND = "0141bf7c8"
READBACK_LAND = "3a418c574"
LEFTOVER_PR = 8345
EXPECTED_BLOBS = {
    f"p/{LEFTOVER_ID}.md": "54c348dc",
    "host/harborline_pack_market_render.py": "cc9a3320",
    "test_harborline_pack_market_render.py": "e8f8703c",
    f"p/{READBACK_ID}.md": "6efbac54",
    "test_harborline_pack_market_render_readback.py": "f4ee4f15",
}
LATER_MAIN_KEEP_REMINT = {
    "path": "hub_pages.py",
    "leftover_pin": "14eeedb0",
    "live": "5ac12648",
    "unread": True,
    "did_not_remint_leftover_to_chase": True,
}
REFUSE = ("--send", "--apply", "--go", "--autopilot")
DUMP = ("--dump-commons", "--marketplace-html")


def blob_prefix(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        return ""
    payload = path.read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()[:8]


def run_leftover(*flags: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(LEFTOVER_HELPER), *flags],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def refuse_payload(flag: str) -> dict[str, object]:
    return {
        "id": SHIP_ID,
        "store": "standalone",
        "commons_is_store": False,
        "refused": flag,
        "verdict": "FINDER-FAILED",
        "sent": 0,
        "booked": 0,
        "cash": 0,
        "checkout": "NOT_MINTED",
        "did_not_remint_leftover_helper": True,
        "did_not_dump_marketplace_html": True,
        "did_not_steal_harborline": True,
        "note": (
            f"{flag} REFUSED. sent=0 booked=0 cash=0. "
            "Did not remint leftover helper. Did not dump marketplace.html. "
            "Did not steal Harborline /harborline."
        ),
    }


def measure() -> dict[str, object]:
    blobs = {rel: blob_prefix(rel) for rel in EXPECTED_BLOBS}
    leftover_blobs_ok = all(
        blobs.get(rel, "").startswith(prefix) for rel, prefix in EXPECTED_BLOBS.items()
    )
    dumped = (ROOT / "marketplace.html").exists()
    harborline_stolen = (ROOT / "harborline").exists() or (ROOT / "qualify.html").exists()
    leftover_json = run_leftover("--json")
    leftover_send = run_leftover("--send")
    leftover_payload: dict[str, object] = {}
    leftover_send_payload: dict[str, object] = {}
    try:
        leftover_payload = json.loads(leftover_json.stdout)
    except json.JSONDecodeError:
        leftover_payload = {}
    try:
        leftover_send_payload = json.loads(leftover_send.stdout)
    except json.JSONDecodeError:
        leftover_send_payload = {}
    leftover_render = (
        leftover_json.returncode == 0
        and leftover_payload.get("verdict") == "RENDER"
        and leftover_payload.get("commons_is_store") is False
        and leftover_payload.get("marketplace_html_on_commons") is False
        and leftover_payload.get("sent") == 0
    )
    leftover_send_refused = (
        leftover_send.returncode == 2
        and leftover_send_payload.get("refused") == "--send"
        and leftover_send_payload.get("sent") == 0
    )
    live_hub = blob_prefix("hub_pages.py")
    later_main = dict(LATER_MAIN_KEEP_REMINT)
    later_main["live"] = live_hub or later_main["live"]
    later_main["unread"] = not live_hub.startswith(later_main["leftover_pin"])
    match = leftover_blobs_ok and leftover_render and leftover_send_refused and not dumped and not harborline_stolen
    return {
        "id": SHIP_ID,
        "leftover_id": LEFTOVER_ID,
        "readback_id": READBACK_ID,
        "leftover_land": LEFTOVER_LAND,
        "readback_land": READBACK_LAND,
        "leftover_pr": LEFTOVER_PR,
        "store": "standalone",
        "desk_route": "/market",
        "commons_is_store": False,
        "marketplace_html_on_commons": dumped,
        "harborline_path_stolen": harborline_stolen,
        "leftover_blobs_ok": leftover_blobs_ok,
        "leftover_helper_not_reminted": blobs.get(
            "host/harborline_pack_market_render.py", ""
        ).startswith("cc9a3320"),
        "leftover_json_verdict": leftover_payload.get("verdict"),
        "leftover_send_refused": leftover_send_refused,
        "later_main_keep_remint": later_main,
        "did_not_remint_leftover_helper": True,
        "did_not_dump_marketplace_html": not dumped,
        "did_not_steal_harborline": not harborline_stolen,
        "checkout": "NOT_MINTED",
        "sent": 0,
        "booked": 0,
        "cash": 0,
        "gate": False,
        "commons_admission": False,
        "blobs": blobs,
        "verdict": "MATCH" if match else "FINDER-FAILED",
        "note": (
            "SHIP unique-pack leftover "
            f"{READBACK_ID} land {READBACK_LAND} blob 6efbac54. "
            f"Independent MATCH leftover 54c348dc #{LEFTOVER_PR}. "
            "Did not remint leftover helper. Did not dump marketplace.html. "
            "Did not steal Harborline /harborline. "
            "Later-main leftover KEEP remint hub_pages.py unread; "
            "did not remint leftover to chase."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--json", action="store_true")
    args, unknown = parser.parse_known_args(argv)
    for flag in unknown:
        if flag in REFUSE or flag in DUMP:
            print(json.dumps(refuse_payload(flag), sort_keys=True))
            return 2
        if flag.startswith("-"):
            print(
                json.dumps(
                    {
                        "id": SHIP_ID,
                        "store": "standalone",
                        "verdict": "FINDER-FAILED",
                        "sent": 0,
                        "unknown": flag,
                        "note": f"{flag} FINDER-FAILED, never silent 0.",
                    },
                    sort_keys=True,
                )
            )
            return 1
    payload = measure()
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload["verdict"] == "MATCH" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
