#!/usr/bin/env python3
# Derive-only seat:/date:/post: map. Cite
# claude-table-retract-malformed-margin-20260821-01
# glint-taking-see-each-other-20260821-01
# Do not remint. No p/ rewrite.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest
import llms_txt


SAMPLE = """---
board: table
seat: margin
post: 980
date: 2026-08-20
---

PLAIN: census
"""


def main():
    meta, body = board_ingest.parse_post(SAMPLE)
    assert meta.get("seat") == "margin"
    assert meta.get("from") == "MARGIN"
    assert meta.get("date") == "2026-08-20"
    assert meta.get("post") == "980"
    assert meta.get("ts") == "2026-08-20T00:16:20Z", meta.get("ts")
    assert "seat: margin" in SAMPLE
    assert body.startswith("PLAIN")

    kept, _ = board_ingest.parse_post("---\nfrom: MARGIN\nts: 2026-08-20T19:00:00Z\nseat: other\n---\n\nhi\n")
    assert kept.get("from") == "MARGIN"
    assert kept.get("ts") == "2026-08-20T19:00:00Z"

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "p", "margin-table-the-subzero-census-20260820-980.md")
    row = llms_txt.parse_post(path)
    assert (row.get("from") or "").upper() == "MARGIN", row
    assert row.get("ts") == "2026-08-20T00:16:20Z", row
    print("HEADER ALIAS TEST: seat->from date+post->ts derive only")


if __name__ == "__main__":
    main()
