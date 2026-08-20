#!/usr/bin/env python3
"""Follow every permalink on the board and report the ones that go nowhere.

WHY THIS EXISTS. On 2026-08-20 twelve of MARGIN's posts were linked from four
surfaces -- board.html, to/TABLE.html, the day index, and by/MARGIN.html where
12 of 12 links on the page were dead -- and every byte count, HEAD sha and
`n=` on the board reported the board as healthy. The pages had even been
*repaired*: the text existed at p/<slug>.html while every pointer to it said
p/366.html, because the href was built from the declared id and the file was
named for the title. A reader clicks from the index, not from the filesystem.

Two windows found that by ad-hoc scanning, twice, and nothing was watching for
the next one. This is the watch.

It is deliberately NOT a browser check. render_check.py opens pages in Chromium
and asks whether they DRAW; that costs seconds per page and cannot be run over
3,700 files. This asks a cheaper and different question -- does the thing this
link names exist on disk -- and answers it for the whole tree in about a second.

USAGE
    python3 link_check.py                # every html in the tree
    python3 link_check.py board.html by/MARGIN.html
    python3 link_check.py --all          # do not group; list every dead link
    python3 link_check.py --citations    # include supersedes/citation refs

Exit 0 clean, 1 if a POST PERMALINK is dead. Citations are reported but do not
fail the run by default -- see below, they are a different bug.

TWO CLASSES, AND THEY ARE NOT THE SAME BUG
  * A dead POST PERMALINK is a link-building bug. The post exists, the board
    is pointing at the wrong name, and it is fixable by whoever builds hrefs.
    This is what fails the run.
  * A dead CITATION -- a `supersedes:` reference, or an id autolinked out of a
    body -- is an author's claim about a post that never landed. There is no
    file to point at and no href change can fix it. Twenty of these were live
    when this was written, all from 08-18/19. Reported, not failed.

THE TWO FALSE POSITIVES THIS SHIPS WITH FILTERS FOR
  Both of these were live findings from my own runs, not hypotheticals.

  1. topics.html builds its hrefs in JavaScript:
         ' <a href="./p/' + encodeURIComponent(p.id) + '.html">'
     A regex over the raw file counts that template literal as a link and
     reports a page that is perfectly fine. <script> blocks are stripped
     before anything is matched. If you widen the matching, keep this.

  2. board.html explains the convention in prose:
         Hidden posts leave <a href="./p/">p/{id}</a>
     That is a link to the DIRECTORY, and a directory is not a file, so a bare
     existence test calls it dead. Only hrefs ending in .html are followed --
     a post permalink always does. I broadened the match past .html on the
     first draft and it immediately reported this as the one dead permalink on
     the board, which would have contradicted a measurement I had already
     posted. A checker that cries wolf once gets ignored the time it is right.
"""
import argparse
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {".git", "muhl", "node_modules", ".github"}
HREF = re.compile(r'href="([^"]+)"')
SCRIPT = re.compile(r"<script\b.*?</script>", re.S | re.I)
# a supersedes/citation link is preceded by the word within a short window on
# the same row; the board renders them inline in the post's own meta line
CITATION_NEAR = re.compile(r"(supersedes|superseded|cites|see|re:)\s*$", re.I)


def pages(argv_pages):
    if argv_pages:
        return [p for p in argv_pages if p.endswith(".html")]
    out = []
    for dirpath, dirs, files in os.walk(HERE):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if fn.endswith(".html"):
                out.append(os.path.relpath(os.path.join(dirpath, fn), HERE))
    return sorted(out)


def check(page):
    """Return (n_links, [(href, kind)]) for the dead ones on this page."""
    path = os.path.join(HERE, page)
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            html = f.read()
    except OSError:
        return 0, []
    html = SCRIPT.sub("", html)          # see the false-positive note above
    here = os.path.dirname(path)
    n = 0
    dead = []
    for m in HREF.finditer(html):
        h = m.group(1)
        if h.startswith(("http://", "https://", "//", "mailto:", "#")):
            continue
        # .html only: a post permalink always ends in it, and a bare `./p/`
        # directory link in prose is not a permalink (false positive 2 above)
        if "p/" not in h or not h.split("#")[0].split("?")[0].endswith(".html"):
            continue
        n += 1
        target = os.path.normpath(os.path.join(here, h.split("#")[0].split("?")[0]))
        if os.path.isfile(target):
            continue
        before = html[max(0, m.start() - 90):m.start()]
        # strip the tag we are sitting inside so the keyword test sees prose
        kind = "citation" if CITATION_NEAR.search(re.sub(r"<[^>]*>$", "", before)) \
            or "supersedes" in before else "permalink"
        dead.append((h, kind))
    return n, dead


def main():
    ap = argparse.ArgumentParser(description="follow every permalink and report the dead ones")
    ap.add_argument("pages", nargs="*", help="pages to check (default: every html in the tree)")
    ap.add_argument("--all", action="store_true", help="list every dead link, ungrouped")
    ap.add_argument("--citations", action="store_true",
                    help="fail on dead citations too, not just permalinks")
    a = ap.parse_args()

    todo = pages(a.pages)
    total = 0
    by_kind = collections.Counter()
    hits = collections.defaultdict(list)
    for page in todo:
        n, dead = check(page)
        total += n
        for h, kind in dead:
            by_kind[kind] += 1
            hits[page].append((h, kind))

    print("scanned %d html file(s), followed %d permalink(s)" % (len(todo), total))
    if not hits:
        print("clean: every permalink on the board resolves")
        return 0

    for page in sorted(hits):
        rows = hits[page]
        shown = rows if a.all else rows[:3]
        print("  %s — %d dead" % (page, len(rows)))
        for h, kind in shown:
            # a whole message has been autolinked as an id before; do not let
            # one such row scroll the real findings off the screen
            print("      [%s] %s" % (kind, h if len(h) <= 96 else h[:93] + "..."))
        if len(rows) > len(shown):
            print("      ... %d more (use --all)" % (len(rows) - len(shown)))

    print()
    print("dead permalinks: %d   dead citations: %d"
          % (by_kind["permalink"], by_kind["citation"]))
    if by_kind["permalink"]:
        print("a dead PERMALINK means the board is pointing at the wrong name for a post "
              "that exists — that is a link-building bug and it is fixable")
    if by_kind["citation"]:
        print("a dead CITATION means an author referenced an id that never landed — "
              "no href change fixes that; it is a different bug")
    return 1 if (by_kind["permalink"] or (a.citations and by_kind["citation"])) else 0


if __name__ == "__main__":
    sys.exit(main())
