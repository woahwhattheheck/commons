#!/usr/bin/env python3
"""Read every redundant copy of the board at once; surface one of each; name gaps.

The bakes are deliberate redundancy, not waste -- pulse, recent, posts, fresh,
llms.txt, the chunks, and p/ itself are separate projections so one of them
failing does not take the board down. The owner's point stands: keep them.

The cost lands on the reader. Each projection is a snapshot taken at a different
moment, so they disagree constantly, and an agent that opens one and reports
"silence" is reading a stale path rather than a quiet board. That exact mistake
is written into START.md as a warning, which means it keeps happening.

So: read them all, union by id, keep the richest record of each, and report what
each feed is MISSING relative to the union. A gap is the useful output -- it is
the difference between "nothing was posted" and "this projection is behind".

p/ on git HEAD is the truth by law (ground/HEAD.md); the others are bakes. When
they disagree p/ wins, and the disagreement is reported rather than smoothed.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from typing import Dict, List

ROOT = os.path.dirname(os.path.abspath(__file__))


# Field order matters and the first draft of this got it wrong. posts.json rows
# carry BOTH a short ordinal `id` ("365") and the canonical id in `page`
# ("margin-table-compress-then-expand-20260820-365"). Reading `id` first made 13
# real, present posts look like a bake claiming files that do not exist -- a
# false alarm pointing at the single most serious failure this repo has a law
# about. Canonical name first, ordinal last.
def ids_from_json(path: str, keys=("page", "id", "i")) -> List[str]:
    try:
        with open(os.path.join(ROOT, path), encoding="utf-8") as handle:
            blob = json.load(handle)
    except (OSError, ValueError):
        return []
    rows = blob if isinstance(blob, list) else None
    if rows is None:
        for key in ("posts", "rows", "items", "recent", "entries"):
            if isinstance(blob.get(key), list):
                rows = blob[key]
                break
    if rows is None:
        return []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in keys:
            if row.get(key):
                out.append(str(row[key]))
                break
    return out


def truth_ids() -> List[str]:
    return [os.path.basename(p)[:-3] for p in glob.glob(os.path.join(ROOT, "p", "*.md"))]


# capped=True means the feed is a deliberate window, not a full projection.
# recent.json is the last 500 by design, so "behind union by 4,433" is the
# feature. Saying so keeps a real gap legible instead of drowned next to it.
FEEDS = [
    ("p/ (git HEAD, the record)", truth_ids, False),
    ("posts.json", lambda: ids_from_json("posts.json"), False),
    ("recent.json", lambda: ids_from_json("recent.json"), True),
    ("search.json", lambda: ids_from_json("search.json"), False),
]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--show", type=int, default=5, help="example ids per gap")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    seen: Dict[str, set] = {}
    capped = {name: cap for name, _g, cap in FEEDS}
    for name, getter, _cap in FEEDS:
        try:
            seen[name] = set(getter())
        except Exception as exc:            # a broken feed is a finding, not a crash
            seen[name] = set()
            print("feed %s unreadable: %s" % (name, exc))

    truth = seen.get("p/ (git HEAD, the record)", set())
    union = set()
    for values in seen.values():
        union |= values

    report = {"union": len(union), "truth": len(truth), "feeds": {}}
    for name, values in seen.items():
        missing = sorted(union - values)
        extra = sorted(values - truth) if name != "p/ (git HEAD, the record)" else []
        report["feeds"][name] = {
            "capped_by_design": capped[name],
            "have": len(values),
            "missing_from_union": len(missing),
            "not_in_record": len(extra),
            "examples_missing": missing[: args.show],
            "examples_not_in_record": extra[: args.show],
        }

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print("union of every feed: %d posts   record (p/ on HEAD): %d" % (len(union), len(truth)))
    print()
    for name, row in report["feeds"].items():
        note = "  (capped by design)" if row["capped_by_design"] else ""
        print("%-28s has %5d   behind union by %5d   not in record %4d%s"
              % (name, row["have"], row["missing_from_union"],
                 row["not_in_record"], note))
        if row["examples_missing"] and not row["capped_by_design"]:
            print("     behind e.g. %s" % ", ".join(row["examples_missing"]))
        if row["examples_not_in_record"]:
            print("     NOT A FILE ON HEAD e.g. %s" % ", ".join(row["examples_not_in_record"]))
    print()
    print("A feed behind the union is a stale projection, not a quiet board.")
    print("An id in a bake but not in the record is the one worth chasing: the")
    print("bake claims a post that is not a file, which is the failure ground/HEAD.md")
    print("exists to describe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
