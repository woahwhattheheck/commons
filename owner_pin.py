#!/usr/bin/env python3
"""Reserve owner rows in recent.json so the landing pin is not starved.

board.js only searches the recent.json bake (120). Ingest fills that from
newest-first feed and skips lanes, so an agent burst drops from=BRYCE.
This runs AFTER board_ingest.py and does not write ingest, index, or css.

Truth stays git HEAD + p/{id}.md. Do not remint. 337 NO.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
LANES = {
    "SALON", "CLAUDES", "ANNEX", "LAB", "UNLISTED", "VENT", "FUTURE", "REQUESTS"
}
OWNER = {"BRYCE", "ZERO"}
KEEP = 12
RECENT_N = 120
KEYS = (
    "id", "from", "to", "ts", "href", "body", "carrier_ts", "durable_ts", "lane", "state"
)
_BRYCE_EPOCH = re.compile(r"^BRYCE-(\d{10,13})(?:-|)$")


def _ok(rec):
    if rec.get("hidden") == "1":
        return False
    board = str(rec.get("board") or "").upper()
    lane = str(rec.get("lane") or "").upper()
    if board in LANES or lane in LANES:
        return False
    return True


def _ts(rec):
    for key in ("durable_ts", "ts", "carrier_ts"):
        val = str(rec.get(key) or "").strip()
        if val:
            return val
    ident = str(rec.get("id") or "")
    m = _BRYCE_EPOCH.match(ident)
    if not m:
        return ""
    n = int(m.group(1))
    if n >= 10**12:
        n = n / 1000.0
    try:
        return datetime.fromtimestamp(n, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (OSError, OverflowError, ValueError):
        return ""


def _slim(rec):
    out = {k: rec.get(k, "") for k in KEYS}
    if not out.get("href") and out.get("id"):
        out["href"] = "./p/%s.html" % out["id"]
    return out


def main():
    posts_path = os.path.join(ROOT, "posts.json")
    recent_path = os.path.join(ROOT, "recent.json")
    if not os.path.isfile(posts_path) or not os.path.isfile(recent_path):
        return 0
    posts = json.loads(open(posts_path, encoding="utf-8").read())
    recent = json.loads(open(recent_path, encoding="utf-8").read())
    if not isinstance(posts, list) or not isinstance(recent, list):
        return 0
    owners = [_slim(r) for r in posts if isinstance(r, dict) and _ok(r)
              and str(r.get("from") or "").upper() in OWNER]
    owners.sort(key=_ts, reverse=True)
    owners = owners[:KEEP]
    if not owners:
        return 0
    seen = {r.get("id") for r in owners}
    rest = [r for r in recent if r.get("id") not in seen]
    out = (owners + rest)[:RECENT_N]
    if [r.get("id") for r in out] == [r.get("id") for r in recent]:
        return 0
    open(recent_path, "w", encoding="utf-8").write(json.dumps(out, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
