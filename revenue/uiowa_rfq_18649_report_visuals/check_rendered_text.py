#!/usr/bin/env python3
"""Detect visible figure text that was truncated mid-word.

Why this exists: this lane's suite validates XML structure, WCAG contrast
arithmetic, canvas bounds and a real monochrome conversion -- 90 tests, all
green -- and none of it can see that a label does not fit. The lane's own
README said so honestly: no rasteriser was found in the container, so nobody
had looked at the figures as pixels.

There is one (headless Chromium at /opt/pw-browsers). Rendering them showed
labels cut off mid-word. This check finds that case without needing a browser,
by exploiting a property the figures already have: the <desc> accessibility
text carries the full sentence, so any visible <text> that is a strict prefix
of the desc and breaks on a word character was cut.

The inversion is the point. The plain-text alternative is complete while the
visible figure is not, so a screen-reader user receives MORE than a sighted
reader -- the reverse of the usual accessibility failure, and invisible to
every structural check.

    python3 check_rendered_text.py <dir-of-svgs>
"""
import glob
import os
import re
import sys


def strip_markup(fragment):
    return re.sub(r"<[^>]+>", "", fragment).strip()


def truncated_texts(svg_source, min_len=12):
    """Visible <text> runs that the <desc> shows were cut mid-word."""
    desc = " ".join(re.findall(r"<desc[^>]*>(.*?)</desc>", svg_source, re.S))
    desc = strip_markup(desc)
    found = []
    for raw in re.findall(r"<text[^>]*>(.*?)</text>", svg_source, re.S):
        visible = strip_markup(raw)
        if len(visible) < min_len:
            continue
        at = desc.find(visible)
        if at == -1:
            continue
        nxt = desc[at + len(visible):at + len(visible) + 1]
        # The full text continues with a word character, so the visible copy
        # stopped inside a word. A deliberate abbreviation would end on a
        # boundary or carry an ellipsis.
        if nxt and nxt.isalnum():
            found.append(visible)
    return found


def main(argv):
    root = argv[1] if len(argv) > 1 else "."
    files = sorted(glob.glob(os.path.join(root, "*.svg")))
    if not files:
        print(f"no .svg files under {root}")
        return 2
    affected, total = 0, 0
    for path in files:
        with open(path, encoding="utf-8") as fh:
            cut = truncated_texts(fh.read())
        if cut:
            affected += 1
            total += len(cut)
            print(f"TRUNCATED {os.path.basename(path)}  ({len(cut)})")
            for visible in cut:
                print(f"    ...{visible[-60:]!r}")
    print("-" * 70)
    print(f"files={len(files)}  affected={affected}  truncated-text-runs={total}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
