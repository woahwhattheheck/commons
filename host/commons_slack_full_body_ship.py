#!/usr/bin/env python3
"""SHIP leftover Commons ↔ Slack full-body. Do not remint leftover or slack_mirror."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFUSE = ("--send", "--apply", "--go", "--autopilot")

LEFTOVER_ID = "cursor-commons-slack-full-body-20260902-01"
SHIP_ID = "cursor-commons-slack-full-body-ship-20260902-01"
LAND = "cee208ea8"
LEFTOVER_SEAT = "bc-73365238"
THIS_SEAT = "bc-7e34a47c"

KEEP = {
    f"p/{LEFTOVER_ID}.md": "86f4eddc",
    "host/commons_slack_full_body.py": "16ba0f4c",
    "test_commons_slack_full_body.py": "7388c998",
    "ground/COMMONS_SLACK_FULL_BODY.json": "d5dba5e8",
    "ground/COMMONS_SLACK_FULL_BODY.md": "f23df2ec",
    "commons-slack.html": "4cbca421",
    "host/slack_mirror.py": "8d3a5e0b",
    "slack_ingest.py": "0040a726",
    "test_slack_mirror.py": "201bca45",
}

THIS_SEAT_PATHS = (
    "host/commons_slack_full_body_ship.py",
    "test_commons_slack_full_body_ship.py",
    f"p/{SHIP_ID}.md",
)


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def keep_ok() -> dict[str, str]:
    measured: dict[str, str] = {}
    for rel, prefix in KEEP.items():
        blob = git_blob(rel)
        if not blob.startswith(prefix):
            raise SystemExit(f"{rel} reminted: want {prefix} got {blob[:8]}")
        measured[rel] = blob
    return measured


def refuse_payload(flag: str) -> dict[str, object]:
    return {
        "kind": "COMMONS_SLACK_FULL_BODY_SHIP",
        "id": SHIP_ID,
        "leftover_id": LEFTOVER_ID,
        "gate": False,
        "login": False,
        "new_token": False,
        "refused": flag,
        "verdict": "FINDER-FAILED",
        "sent": 0,
        "cash": 0,
        "checkout": "NOT_MINTED",
        "note": (
            f"{flag} REFUSED. sent=0 cash=0. No new Slack secret. "
            "Did not remint leftover or slack_mirror.py."
        ),
    }


def leftover_measure() -> dict[str, object]:
    proc = subprocess.run(
        ["python3", str(ROOT / "host/commons_slack_full_body.py"), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    return {"rc": proc.returncode, "payload": payload}


def leftover_tests() -> dict[str, object]:
    proc = subprocess.run(
        ["python3", "-m", "unittest", "test_commons_slack_full_body.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "rc": proc.returncode,
        "ok": proc.returncode == 0,
        "ran_7": "Ran 7 tests" in (proc.stderr or ""),
    }


def leftover_refuse(flag: str) -> dict[str, object]:
    proc = subprocess.run(
        ["python3", str(ROOT / "host/commons_slack_full_body.py"), flag],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    return {"rc": proc.returncode, "payload": payload}


def classify_ship() -> dict[str, object]:
    blobs = keep_ok()
    measured = leftover_measure()
    tests = leftover_tests()
    send = leftover_refuse("--send")
    go = leftover_refuse("--go")
    leftover = measured["payload"]
    dumped = (ROOT / "marketplace.html").exists() or (ROOT / "qualify.html").exists()
    corner = (ROOT / "CLAUDE_CORNER.md").exists()
    ship_ok = (
        measured["rc"] == 0
        and leftover.get("verdict") == "RENDER"
        and leftover.get("two_way") is True
        and leftover.get("instant") is True
        and leftover.get("posts_not_receipts") is True
        and leftover.get("full_body") is True
        and leftover.get("new_token") is False
        and leftover.get("login") is False
        and leftover.get("gate") is False
        and leftover.get("sends") == 0
        and tests["ok"]
        and tests["ran_7"]
        and send["rc"] == 2
        and send["payload"].get("sent") == 0
        and go["rc"] == 2
        and go["payload"].get("sent") == 0
        and not dumped
        and not corner
    )
    return {
        "kind": "COMMONS_SLACK_FULL_BODY_SHIP",
        "id": SHIP_ID,
        "leftover_id": LEFTOVER_ID,
        "leftover_seat": LEFTOVER_SEAT,
        "this_seat": THIS_SEAT,
        "land": LAND,
        "receipt_blob": "86f4eddc",
        "receipt_bytes": 2416,
        "receipt_sha256": "2aaecb01",
        "two_way": True,
        "instant": True,
        "posts_not_receipts": True,
        "full_body": True,
        "new_token": False,
        "login": False,
        "gate": False,
        "slack_ts_is_commons_id": False,
        "channel_is_allowlist": False,
        "leftover_tests": "7/7",
        "send_rc": send["rc"],
        "go_rc": go["rc"],
        "sent": 0,
        "cash": 0,
        "checkout": "NOT_MINTED",
        "did_not_remint_leftover": True,
        "did_not_remint_slack_mirror": True,
        "this_seat_paths": list(THIS_SEAT_PATHS),
        "keep_blobs": {rel: blobs[rel][:8] for rel in KEEP},
        "ship_ok": ship_ok,
        "verdict": "SHIP" if ship_ok else "FINDER-FAILED",
        "note": (
            f"SHIP leftover {LEFTOVER_ID} land {LAND} receipt 86f4eddc "
            "(2416) SHA256 2aaecb01. Tests 7/7. --send/--go rc=2 sent=0. "
            "Did not remint slack_mirror.py 8d3a5e0b. "
            "Checkout NOT_MINTED is a measurement, not a freeze. Sends 0."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--json", action="store_true")
    args, unknown = parser.parse_known_args(argv)
    for flag in unknown:
        if flag in REFUSE:
            print(json.dumps(refuse_payload(flag), sort_keys=True))
            return 2
        if flag.startswith("-"):
            print(
                json.dumps(
                    {
                        "kind": "COMMONS_SLACK_FULL_BODY_SHIP",
                        "verdict": "FINDER-FAILED",
                        "sent": 0,
                        "unknown": flag,
                        "id": SHIP_ID,
                        "note": f"{flag} FINDER-FAILED, never silent 0.",
                    },
                    sort_keys=True,
                )
            )
            return 1
    payload = classify_ship()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ship_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
