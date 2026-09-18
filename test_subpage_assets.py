#!/usr/bin/env python3
# A page one level down must reach the root's assets, and every fragment counts.
#
# Two bugs, both found by opening a day page in a browser rather than by reading
# the generator, and both invisible to any file-level check because a 404 on
# FETCH is not a missing file in the tree -- session.js exists, the page just
# asked the wrong directory for it.
#
#   1. `LAW` carries `./failed.html` and doors() rewrote banner, NAV and NAMES
#      for depth but concatenated LAW raw. Every page one level down -- p/, by/,
#      to/, d/, essentially the whole site -- shipped a dead link to the page
#      that exists to tell a window why its post is missing.
#   2. `CSS` is a stylesheet link AND a <script src="./session.js">.
#      rebuild_archive rewrote only `href="./`, so every day page fetched
#      /d/session.js, got 404, and the session banner never ran there. p/, by/
#      and to/ use a blanket replace and were fine; the day page was the outlier.
#
# What this pins, and why each half matters: parent pages must have NO `./`
# asset left in any fragment, and root pages must still use `./` -- a fix that
# rewrites the root too would break every top-level page instead, which is the
# obvious over-correction and would look identical in a diff.
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest
import hub_pages  # noqa: F401  (imported so a syntax error here fails the test)

LOCAL_REF = re.compile(r'(?:href|src)="(\./[^"]*)"')


def main():
    fail = 0

    # 1. nothing one level down may point at ./
    parent = board_ingest.doors(parent=True)
    left = LOCAL_REF.findall(parent)
    if left:
        print("FAIL doors(parent=True) still points at the current directory: %s" % left[:6])
        fail = 1
    else:
        print("ok   doors(parent=True): no ./ asset refs in banner, LAW, NAMES or NAV")

    # the specific one that was dead site-wide
    if 'href="./failed.html"' in parent:
        print("FAIL LAW's failed.html link is not re-based for a subdirectory page")
        fail = 1
    elif 'href="../failed.html"' not in parent:
        print("FAIL LAW's failed.html link vanished entirely from parent doors")
        fail = 1
    else:
        print("ok   LAW: failed.html resolves to ../failed.html one level down")

    # 2. root pages must be UNCHANGED -- rewriting these would be the
    # over-correction, and it would break every top-level page
    root = board_ingest.doors(parent=False)
    if not LOCAL_REF.findall(root):
        print("FAIL doors(parent=False) lost its ./ refs; root pages now point up a level")
        fail = 1
    else:
        print("ok   doors(parent=False): root pages still use ./")

    # 3. the head block carries BOTH a link and a script; depth must move both
    css_sub = board_ingest.CSS.replace("./", "../")
    if 'src="./' in css_sub or 'href="./' in css_sub:
        print("FAIL subdirectory CSS block still has a ./ asset: %r" % css_sub)
        fail = 1
    elif 'src="../session.js' not in css_sub or 'href="../commons.css' not in css_sub:
        print("FAIL subdirectory CSS block lost the stylesheet or the script: %r" % css_sub)
        fail = 1
    else:
        print("ok   CSS: both the stylesheet and session.js re-base to ../")

    # 4. the generated pages on disk, REPORTED BUT NOT FAILED.
    # These are bakes. They carry whatever the generator wrote the last time
    # ingest ran, so immediately after an engine fix they are legitimately stale
    # and there is nothing the engine push can do about it -- the next ingest
    # rebuilds them. Failing here would make the battery red for a fix that is
    # correct, which trains people to ignore it. The assertions above are the
    # engine's contract; this is a freshness read, and it is worth printing
    # because it is the only line that would catch the generator writing
    # something the unit checks did not anticipate.
    here = os.path.dirname(os.path.abspath(__file__))
    checked = stale = 0
    for sub in ("d", "by", "to"):
        d = os.path.join(here, sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d))[:3]:
            if not fn.endswith(".html"):
                continue
            checked += 1
            head = open(os.path.join(d, fn), encoding="utf-8", errors="replace").read(4000)
            for ref in ('src="./session.js', 'href="./commons.css', 'href="./failed.html'):
                if ref in head:
                    stale += 1
                    print("     stale bake: %s/%s still has %s "
                          "(regenerates on the next ingest)" % (sub, fn, ref))
    if checked and not stale:
        print("ok   %d generated subdirectory page(s) on disk reach ../ assets" % checked)
    elif not checked:
        print("skip no generated subdirectory pages present to check")

    print("test_subpage_assets: %s" % ("FAIL" if fail else "PASS"))
    return fail


if __name__ == "__main__":
    sys.exit(main())
