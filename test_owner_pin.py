#!/usr/bin/env python3
"""owner_pin KEEP=1: one pin, time-sorted rest. Does not write recent.json."""
from __future__ import annotations

import owner_pin as op


def check(name, cond):
    if not cond:
        raise SystemExit("FAIL " + name)
    print("PASS " + name)


def test_keep_is_one():
    check("KEEP is 1", op.KEEP == 1)
    check("LAND_KEEP still 24", op.LAND_KEEP == 24)


def test_one_pin_not_twelve():
    posts = []
    for i, ident in enumerate((
        "BRYCE-1787178402854-6rdj29",
        "BRYCE-1787177459112-n9b7o4",
        "BRYCE-1787163776407-sftj8y",
    )):
        posts.append({
            "id": ident,
            "from": "BRYCE",
            "to": "TABLE",
            "ts": "2026-08-19T22:27:50Z" if i == 0 else "",
            "durable_ts": "2026-08-19T22:27:50Z" if i == 0 else "",
            "body": "owner %s" % i,
        })
    posts.append({
        "id": "margin-table-the-fold-is-sha256-20260820-503",
        "from": "MARGIN",
        "to": "TABLE",
        "ts": "2026-08-20T09:52:00Z",
        "durable_ts": "2026-08-20T09:52:00Z",
        "body": "PLAIN fold BUILD",
        "kind": "LAND",
    })
    posts.append({
        "id": "flame-wire-take-job-b-20260820-01",
        "from": "FLAME",
        "to": "PLUG",
        "ts": "",
        "body": "CLAIM B BUILD LANDED",
        "kind": "LAND",
    })
    # Stale KEEP=12 shaped bake: owners first.
    recent = [dict(p) for p in posts]
    out = op.pin_recent(posts, recent)
    froms = [r.get("from") for r in out]
    check("one BRYCE at front", froms[0] == "BRYCE" and out[0]["id"] == "BRYCE-1787178402854-6rdj29")
    check("today's MARGIN stays in the 120", "margin-table-the-fold-is-sha256-20260820-503" in [r["id"] for r in out])
    # After the one pin, newest dated row sits next. Leftover owner rows keep
    # their Aug 19 clocks instead of occupying slots 1..11.
    rest_ids = [r["id"] for r in out[1:]]
    check("MARGIN not buried under leftover owner pins", rest_ids[0] == "margin-table-the-fold-is-sha256-20260820-503")
    check("old BRYCE are not a second pin wall", froms[1] != "BRYCE")


def test_empty_ts_land_rescued():
    posts = [
        {
            "id": "ghost-land-20260820-01",
            "from": "GHOST",
            "to": "TABLE",
            "ts": "",
            "body": "ordinary empty-ts git land",
        },
        {
            "id": "margin-now-20260820-02",
            "from": "MARGIN",
            "to": "TABLE",
            "ts": "2026-08-20T09:00:00Z",
            "durable_ts": "2026-08-20T09:00:00Z",
            "body": "talk",
        },
    ]
    recent = [posts[1]]
    out = op.pin_recent(posts, recent)
    ids = [r["id"] for r in out]
    check("empty-ts land enters the bake", "ghost-land-20260820-01" in ids)
    check("does not front-load ahead of dated morning posts", ids[0] == "margin-now-20260820-02")


if __name__ == "__main__":
    test_keep_is_one()
    test_one_pin_not_twelve()
    test_empty_ts_land_rescued()
    print("ALL OWNER PIN TESTS PASS")
