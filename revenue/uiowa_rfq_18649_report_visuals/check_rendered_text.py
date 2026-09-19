#!/usr/bin/env python3
"""Detect mid-word truncation and incomplete content-sized text groups.

OP5-CONTROL's original detector compares visible text with the retained desc.
Complete wrapped groups are now compared as a whole, so a line break in a long
identifier is not itself mistaken for lost content. The visible children must
also match the group's declared source; metadata alone is never a pass.
This is a semantic/structural check, not browser or screen-reader testing.

    python3 check_rendered_text.py <dir-of-svgs>
"""
import glob
import html
import os
import re
import sys
import xml.etree.ElementTree as ET


def strip_markup(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def truncated_texts(svg_source, min_len=12):
    """Report visible runs cut mid-word or missing their declared content."""
    root = ET.fromstring(svg_source)
    desc = " ".join("".join(node.itertext()) for node in root.iter()
                    if _local(node.tag) == "desc").strip()
    found = []
    consumed = set()
    runs = []
    for node in root.iter():
        if node.get("data-text-layout") != "full" or node.get("data-source-text") is None:
            continue
        children = [child for child in node.iter() if _local(child.tag) == "text"]
        visible = "".join("".join(child.itertext()) for child in children)
        expected = node.get("data-source-text").replace("\r\n", "\n").replace("\r", "\n")
        consumed.update(id(child) for child in children)
        if visible != expected.replace("\n", ""):
            found.append(visible.strip() or "<missing wrapped text>")
        else:
            runs.append(visible.strip())
    for node in root.iter():
        if _local(node.tag) == "text" and id(node) not in consumed:
            runs.append("".join(node.itertext()).strip())
    for visible in runs:
        if len(visible) < min_len:
            continue
        at = desc.find(visible)
        if at == -1:
            continue
        nxt = desc[at + len(visible):at + len(visible) + 1]
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
        try:
            with open(path, encoding="utf-8") as fh:
                cut = truncated_texts(fh.read())
        except (OSError, UnicodeError, ET.ParseError) as exc:
            print(f"INVALID {os.path.basename(path)}: {exc}")
            return 2
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
