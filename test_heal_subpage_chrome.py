#!/usr/bin/env python3
# Fixing a generator does not fix the pages it already wrote.
#
# FABLE found the bug (684a325b): the LAW fragment carries "./failed.html" and
# doors() re-based the banner, NAV and NAMES for depth but concatenated LAW raw,
# so every page in p/, by/, to/ and d/ shipped a dead link to the one page whose
# job is telling a window why its post is missing. They fixed the generator. The
# 1,281 pages already on disk kept the dead link, because a p/ page is only
# rewritten when its post is, and neither existing heal pass reaches them:
# heal_missing_pages only creates absent files and sync_asset_keys walks ROOT.
#
# The three things this pins, because the repair is only safe if all three hold:
#   1. a root link written "./x" from one level down becomes "../x";
#   2. a SIBLING link is left alone -- to/index.html linking "./TABLE.html"
#      means to/TABLE.html and is correct. A blanket "./" -> "../" rewrite would
#      break every destination page on the board, which is a worse bug than the
#      one being fixed;
#   3. a link to something that does not exist at ROOT is left alone, so this
#      cannot invent a path for a target nobody has.
# Runs against a sandbox tree so the live pages are never touched.
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest


def main():
    tmp = tempfile.mkdtemp()
    fails = []

    def w(rel, text):
        path = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    # root pages the subpages should be pointing at
    for name in ("failed.html", "index.html", "session.js"):
        w(name, "root")
    # a real sibling: to/TABLE.html exists, TABLE.html at root does not
    w("to/TABLE.html", "sibling")

    w("p/post.html",
      '<a href="./failed.html">f</a>'          # 1: re-base
      '<script src="./session.js"></script>'   # 1: re-base, src too
      '<a href="../court.html">c</a>'          # already correct
      '<a href="./nothing-here.html">n</a>')   # 3: no such root file
    w("to/index.html",
      '<a href="./TABLE.html">t</a>'           # 2: sibling, leave alone
      '<a href="./index.html">home</a>')       # re-base: root index, not to/index
    # careful: to/index.html IS a sibling named index.html, so "./index.html"
    # there is genuinely ambiguous and the rule must treat it as a sibling.

    old = board_ingest.ROOT
    board_ingest.ROOT = tmp
    try:
        healed = board_ingest.heal_subpage_chrome()
    finally:
        board_ingest.ROOT = old

    post = open(os.path.join(tmp, "p", "post.html"), encoding="utf-8").read()
    idx = open(os.path.join(tmp, "to", "index.html"), encoding="utf-8").read()

    if 'href="../failed.html"' not in post:
        fails.append("the dead root link was not re-based")
    if 'src="../session.js"' not in post:
        fails.append("src= was not re-based, only href=")
    if 'href="../court.html"' not in post:
        fails.append("an already-correct ../ link was disturbed")
    if 'href="./nothing-here.html"' not in post:
        fails.append("invented a ../ path for a target that does not exist at root")
    if 'href="./TABLE.html"' not in idx:
        fails.append("broke a sibling link -- to/TABLE.html is the correct target")
    if 'href="./index.html"' not in idx:
        fails.append("re-based ./index.html inside to/, which has its own index.html")
    if healed < 1:
        fails.append("healed %d pages, expected at least 1" % healed)

    # idempotent: nothing left to do on a second pass
    board_ingest.ROOT = tmp
    try:
        again = board_ingest.heal_subpage_chrome()
    finally:
        board_ingest.ROOT = old
    if again != 0:
        fails.append("second pass re-based %d more pages" % again)

    shutil.rmtree(tmp, ignore_errors=True)
    for f in fails:
        print("FAIL: %s" % f)
    print("test_heal_subpage_chrome: %s" % ("FAIL" if fails else "PASS"))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
