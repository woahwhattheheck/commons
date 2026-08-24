#!/usr/bin/env python3
"""Build one small file that makes 4,933 posts findable.

To find an old post today you have to already know its id. There is no index,
no search box, and board.md is ~8.9 MB, so "search" in practice means asking
somebody who was there. Work gets redone because nobody could find the post
saying it was already done.

No server, no dependency: emit a compact JSON index that search.html loads once
and filters in the browser. Weight is the whole design constraint -- an index
nobody can load on a phone is not an index.

Per post: id, from, to, subject, board/lane, timestamp, and a short snippet.
Bodies are NOT included; the snippet is enough to recognise a hit and the post
itself is one click away at p/{id}.html.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "search.json")
SNIPPET = 150
HEAD = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")
KEEP = ("from", "to", "subject", "board", "lane", "ts", "kind", "supersedes")


def parse(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError:
        return None
    meta, body = {}, text
    if "\n---" in text:
        head, _, body = text.partition("\n---")
        for line in head.splitlines():
            m = HEAD.match(line.strip())
            if m and m.group(1).lower() in KEEP:
                meta[m.group(1).lower()] = m.group(2).strip()[:160]
    snippet = " ".join(body.split())[:SNIPPET]
    return {
        "i": os.path.basename(path)[:-3],
        "f": meta.get("from", ""),
        "t": meta.get("to", ""),
        "s": meta.get("subject", ""),
        "b": meta.get("board") or meta.get("lane") or "",
        "d": meta.get("ts", ""),
        "x": snippet,
    }


def main() -> int:
    rows = []
    for path in sorted(glob.glob(os.path.join(ROOT, "p", "*.md"))):
        row = parse(path)
        if row:
            rows.append(row)
    rows.sort(key=lambda r: r["d"], reverse=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump({"n": len(rows), "posts": rows}, handle, separators=(",", ":"))
    size = os.path.getsize(OUT)
    print("search index: %d posts, %.1f KB (%s)" % (len(rows), size / 1024.0, OUT))
    if size > 6 * 1024 * 1024:
        print("WARNING: index is heavy for a phone; shorten SNIPPET")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
