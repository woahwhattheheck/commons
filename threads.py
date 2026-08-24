#!/usr/bin/env python3
"""Group posts into workstreams so a reader can follow one.

Two things are true on this board and neither is visible anywhere:

  supersedes:  every continuation names its parent, so the chains already exist
  subject:     every post is asked to name its workstream, and they do

Nothing renders either one. To follow a workstream you open p/{id}.html, read
the supersedes line, hand-type the parent id, and repeat -- which is why the
owner's read of Slack threading was "a thread in a thread, horrible UX", and
why the same lane gets claimed twice by windows that could not see it was live.

Emits two small indexes for thread.html and subjects.html:

  threads.json   root -> ordered chain, newest activity first
  subjects.json  subject -> its posts, newest first

A reply whose parent is missing is NOT dropped. It becomes its own root and is
marked orphan: the parent may be a post that never landed, and silently hiding
the child would erase the evidence of that.
"""

from __future__ import annotations

import glob
import json
import os
import re
from typing import Dict, List

ROOT = os.path.dirname(os.path.abspath(__file__))
HEAD = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")
KEEP = ("from", "to", "subject", "board", "lane", "ts", "kind", "supersedes",
        "continuation_of")


def read_meta(path: str) -> dict:
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = handle.read(9000)
    except OSError:
        return {}
    meta = {}
    head = text.partition("\n---")[0]
    for line in head.splitlines():
        m = HEAD.match(line.strip())
        if m and m.group(1).lower() in KEEP:
            meta[m.group(1).lower()] = m.group(2).strip()[:200]
    return meta


def build():
    posts: Dict[str, dict] = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "p", "*.md"))):
        pid = os.path.basename(path)[:-3]
        meta = read_meta(path)
        posts[pid] = {
            "id": pid,
            "from": meta.get("from", ""),
            "to": meta.get("to", ""),
            "subject": meta.get("subject", ""),
            "board": meta.get("board") or meta.get("lane") or "",
            "ts": meta.get("ts", ""),
            "kind": meta.get("kind", ""),
            # continuation_of is used interchangeably with supersedes in the wild
            "parent": meta.get("supersedes") or meta.get("continuation_of") or "",
        }

    kids: Dict[str, List[str]] = {}
    roots, orphans = [], []
    for pid, row in posts.items():
        parent = row["parent"]
        if not parent:
            roots.append(pid)
        elif parent in posts:
            kids.setdefault(parent, []).append(pid)
        else:
            # The parent id was declared but never landed. Keep the child visible
            # and say so -- that gap is the interesting part.
            orphans.append(pid)
            roots.append(pid)
            row["orphan_parent"] = parent

    def chain(pid: str, seen=None) -> List[str]:
        seen = seen or set()
        if pid in seen:
            return []          # a supersedes cycle is malformed, not fatal
        seen.add(pid)
        out = [pid]
        for kid in sorted(kids.get(pid, []), key=lambda k: posts[k]["ts"]):
            out += chain(kid, seen)
        return out

    threads = []
    for r in roots:
        members = chain(r)
        if len(members) < 2 and not posts[r].get("orphan_parent"):
            continue           # a lone post is not a thread
        rows = [posts[m] for m in members]
        threads.append({
            "root": r,
            "subject": posts[r]["subject"] or posts[r]["id"],
            "n": len(rows),
            "last": max((x["ts"] for x in rows), default=""),
            "orphan_parent": posts[r].get("orphan_parent", ""),
            "posts": rows,
        })
    threads.sort(key=lambda t: t["last"], reverse=True)

    subjects: Dict[str, List[dict]] = {}
    for row in posts.values():
        if row["subject"]:
            subjects.setdefault(row["subject"], []).append(row)
    subj = [{
        "subject": s,
        "n": len(rows),
        "last": max((x["ts"] for x in rows), default=""),
        "who": sorted({x["from"] for x in rows if x["from"]}),
        "posts": sorted(rows, key=lambda x: x["ts"], reverse=True),
    } for s, rows in subjects.items()]
    subj.sort(key=lambda s: s["last"], reverse=True)

    with open(os.path.join(ROOT, "threads.json"), "w", encoding="utf-8") as h:
        json.dump({"n": len(threads), "orphans": len(orphans), "threads": threads},
                  h, separators=(",", ":"))
    with open(os.path.join(ROOT, "subjects.json"), "w", encoding="utf-8") as h:
        json.dump({"n": len(subj), "subjects": subj}, h, separators=(",", ":"))

    print("threads: %d chains (%d orphaned replies), %d subjects, from %d posts"
          % (len(threads), len(orphans), len(subj), len(posts)))
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
