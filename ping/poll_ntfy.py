#!/usr/bin/env python3
"""Poll ntfy JSON. ChatGPT / Claude do not get webhooks. They GET.

Usage:
  python ping/poll_ntfy.py https://ntfy.sh/TOPIC
  python ping/poll_ntfy.py https://ntfy.sh/TOPIC --since 1h

Prints message ids. Does not invent dest. Does not fire 337.
Does not write the board.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request


def poll(url: str, since: str | None) -> list:
    target = url.rstrip("/") + "/json?poll=1"
    if since:
        target += "&since=" + since
    req = urllib.request.Request(target, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    rows = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--since", default=None)
    args = ap.parse_args()
    rows = poll(args.url, args.since)
    if not rows:
        print("none")
        return 0
    for rec in rows:
        mid = rec.get("id") or ""
        msg = rec.get("message") or rec.get("title") or ""
        print("%s\t%s" % (mid, msg.replace("\n", " ")[:200]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
