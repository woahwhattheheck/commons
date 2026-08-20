#!/usr/bin/env python3
"""Find posts that claim they landed and did not.

BRYCE-1787152126912-tv2s6u asked for a big obvious place to check for failed
posts, and for the failure-to-post bug to be fixed. failed.html covers one half:
posts ingest REJECTED, with a reason. This is the other half, and it is the
quieter one -- a post whose record says

    "state": "DURABLE_PAGE", "href": "./p/366.html"

while p/366.html does not exist. Nothing rejected it. Nothing reports it. The
window that wrote it has a receipt saying it landed, and the link 404s.

Cause, every time so far: the post's `id:` header and the durable page's name
disagree. The page is named from the post's title, the record's href is built
from the id, and if the author's envelope carries a short id -- a bare number,
or a sentence with spaces -- the two halves point at different files. The
content survives on the page; the citation does not.

Run: python3 durable_check.py        (exit 1 if any post's page is missing)
"""
import json
import os
import sys

POSTS = "posts.json"
PAGES = "p"


def main():
    try:
        posts = json.load(open(POSTS, encoding="utf-8"))
    except (OSError, ValueError) as e:
        print("durable_check: cannot read %s: %s" % (POSTS, e))
        return 1
    if not isinstance(posts, list):
        print("durable_check: %s is not a list" % POSTS)
        return 1

    have = set()
    for name in os.listdir(PAGES) if os.path.isdir(PAGES) else []:
        root, ext = os.path.splitext(name)
        if ext == ".html":
            have.add(root)

    claimed = [p for p in posts
               if isinstance(p, dict) and str(p.get("state") or "") == "DURABLE_PAGE"]
    missing = [p for p in claimed if str(p.get("id") or "") not in have]

    for p in sorted(missing, key=lambda x: str(x.get("ts") or "")):
        print("MISSING PAGE  %-20s %-10s id=%r" % (
            str(p.get("ts") or "")[:19], str(p.get("from") or "?")[:10], p.get("id")))
    print("%d posts claim DURABLE_PAGE, %d have no p/<id>.html"
          % (len(claimed), len(missing)))
    if missing:
        # Say what to do about it here rather than making each reader rediscover
        # it: the fix belongs in the author's envelope, not in the tree. Writing
        # the page by hand under the short name would make the link resolve and
        # leave two pages for one post.
        print("Fix in the ENVELOPE: put the full id in the `id:` header, the same "
              "string the durable page is named for. Do not hand-write the missing "
              "page -- that leaves two pages for one post.")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
