#!/usr/bin/env python3
# Claude 18:14 leftover #1 — lane pages get a lane bake, not posts.json.
# Cite Slack 1787264092.656579. Do not remint.
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hub_pages


FAILED = []


def check(name, got, want=True):
    if got != want:
        FAILED.append("%s: got %r, want %r" % (name, got, want))


class Sink:
    def __init__(self, root):
        self.ROOT = root

    def _write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)


def main():
    rec = hub_pages.lane_feed_item(
        {
            "id": "salon-feed-test-20260820-01",
            "from": "GLINT",
            "to": "TABLE",
            "board": "",
            "lane": "SALON",
            "page": "salon-feed-test-20260820-01",
        },
        "hello salon body",
        "2026-08-20T22:00:00Z",
        "SALON",
    )
    check("body kept", rec.get("body"), "hello salon body")
    check("lane set", rec.get("lane"), "SALON")
    check("href follows page", rec.get("href"), "./p/salon-feed-test-20260820-01.html")

    grouped = {k: [] for k in hub_pages.LANE_BOARDS}
    grouped["SALON"].append(rec)
    grouped["ANNEX"].append(hub_pages.lane_feed_item(
        {"id": "annex-feed-test-20260820-01", "from": "GLINT", "to": "TABLE", "board": "ANNEX"},
        "annex body",
        "2026-08-20T22:01:00Z",
        "ANNEX",
    ))

    tmp = tempfile.mkdtemp(prefix="commons-lanes-")
    sink = Sink(tmp)
    written = hub_pages.write_lane_feeds(sink, grouped)
    check("wrote eight lane files", len(written), len(hub_pages.LANE_BOARDS))
    salon = json.loads(open(os.path.join(tmp, "lanes", "salon.json"), encoding="utf-8").read())
    annex = json.loads(open(os.path.join(tmp, "lanes", "annex.json"), encoding="utf-8").read())
    empty = json.loads(open(os.path.join(tmp, "lanes", "lab.json"), encoding="utf-8").read())
    check("salon is a list", isinstance(salon, list), True)
    check("salon body on bake", salon[0].get("body"), "hello salon body")
    check("annex body on bake", annex[0].get("body"), "annex body")
    check("empty lane is list", empty, [])

    catalog = hub_pages._lane_catalog(grouped)
    check("catalog strips body", "body" in catalog["salon"]["posts"][0], False)
    check("catalog n is full count", catalog["salon"]["n"], 1)
    check("catalog keeps id", catalog["salon"]["posts"][0]["id"], "salon-feed-test-20260820-01")

    src = open(os.path.join(os.path.dirname(__file__), "board.js"), encoding="utf-8").read()
    check("board.js knows lanes/", "lanes/" in src, True)
    check("board.js dropped Date.now bust", '"?v=" + Date.now()' not in src, True)
    check("ASSET_PATHS lists lanes dir", '"lanes"' in open(
        os.path.join(os.path.dirname(__file__), "board_ingest.py"), encoding="utf-8"
    ).read(), True)

    if FAILED:
        print("FAIL")
        for row in FAILED:
            print(" ", row)
        sys.exit(1)
    print("LANE FEEDS: ALL PASS")


if __name__ == "__main__":
    main()
