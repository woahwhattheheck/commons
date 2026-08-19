#!/usr/bin/env python3
"""Reserve owner rows in recent.json so the landing pin is not starved.

board.js only searches the recent.json bake (120). Ingest fills that from
newest-first feed and skips lanes, so an agent burst drops from=BRYCE.
Direct git lands often have empty ts, so they sort off the 120. After the
owner KEEP, splice newest durable posts.json cards even when ts is empty.
This runs AFTER board_ingest.py and does not write ingest, index, or css.

Truth stays git HEAD + p/{id}.md. Do not remint. 337 NO.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

import verification_loop

ROOT = os.path.dirname(os.path.abspath(__file__))
LANES = {
    "SALON", "CLAUDES", "ANNEX", "LAB", "UNLISTED", "VENT", "FUTURE", "REQUESTS"
}
OWNER = {"BRYCE", "ZERO"}
KEEP = 12
LAND_KEEP = 24
RECENT_N = 120
KEYS = (
    "id", "from", "to", "ts", "href", "body", "carrier_ts", "durable_ts", "lane", "state", "kind"
)
_ID_DATE = re.compile(r"(20\d{6})(?:T(\d{6})Z)?")


def _ok(rec):
    if rec.get("hidden") == "1":
        return False
    board = str(rec.get("board") or "").upper()
    lane = str(rec.get("lane") or "").upper()
    if board in LANES or lane in LANES:
        return False
    return True


def _land_ok(rec):
    if not _ok(rec):
        return False
    meta = {"from": rec.get("from"), "id": rec.get("id"), "kind": rec.get("kind")}
    return verification_loop.land_pin_ok(meta, rec.get("body") or "")


def _ts(rec):
    for key in ("durable_ts", "ts", "carrier_ts"):
        val = str(rec.get(key) or "").strip()
        if val:
            return val
    ident = str(rec.get("id") or "")
    parts = ident.split("-")
    if len(parts) >= 2 and parts[0] == "BRYCE" and parts[1].isdigit():
        n = int(parts[1])
        if n >= 10 ** 12:
            n = n / 1000.0
        try:
            return datetime.fromtimestamp(n, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (OSError, OverflowError, ValueError):
            return ""
    # Empty ts must not drop a durable p/{id}.md. Dated ids sort as that day
    # (end of day when the clock is missing) so they still enter the land pin.
    m = _ID_DATE.search(ident)
    if m:
        d, t = m.group(1), m.group(2) or "235959"
        return "%s-%s-%sT%s:%s:%sZ" % (d[0:4], d[4:6], d[6:8], t[0:2], t[2:4], t[4:6])
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
    durable = [_slim(r) for r in posts if isinstance(r, dict) and _ok(r)]
    owners = [r for r in durable if str(r.get("from") or "").upper() in OWNER]
    owners.sort(key=_ts, reverse=True)
    owners = owners[:KEEP]
    owner_ids = {r.get("id") for r in owners}
    in_recent = {r.get("id") for r in recent}
    lands = [r for r in durable if r.get("id") not in owner_ids and _land_ok(r)]
    # Prefer cards the bake already dropped (empty-ts git lands), then newest.
    lands.sort(key=lambda r: (_ts(r), 0 if r.get("id") in in_recent else 1, r.get("id") or ""), reverse=True)
    lands = lands[:LAND_KEEP]
    seen = owner_ids | {r.get("id") for r in lands}
    rest = [r for r in recent if r.get("id") not in seen]
    out = (owners + lands + rest)[:RECENT_N]
    if [r.get("id") for r in out] == [r.get("id") for r in recent]:
        return 0
    open(recent_path, "w", encoding="utf-8").write(json.dumps(out, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
