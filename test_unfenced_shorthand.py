#!/usr/bin/env python3
# Unfenced seat:/date:/post: must be read as headers. PLAYER1's alias then
# fills from/ts. Do not replace test_header_alias.py. Do not rewrite p/.
# Cite claude-table-retract-malformed-margin-20260821-01
# Cite specdaddy-glint-peers-landed-20260821-01
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest
import llms_txt

UNFENCED = """seat: margin
board: annex
post: 300
date: 2026-08-20

---

PLAIN: unfenced shorthand
"""


def main():
    meta, body = board_ingest.parse_post(UNFENCED)
    assert (meta.get("from") or "").upper() == "MARGIN", meta
    assert meta.get("seat") == "margin", meta
    assert meta.get("ts") == "2026-08-20T00:05:00Z", meta
    assert body.lstrip().startswith("PLAIN:"), body
    assert "from:" not in UNFENCED.split("---")[0]

    src, dest, mid, text, extra = board_ingest._issue_post_fields({
        "title": "margin-issue-shorthand-01",
        "body": UNFENCED,
        "labels": [{"name": "board"}],
    })
    assert src == "margin", src
    assert text.lstrip().startswith("PLAIN:"), text

    with tempfile.TemporaryDirectory() as d:
        old = llms_txt.ROOT
        llms_txt.ROOT = d
        try:
            n = llms_txt.write_peers(
                [{
                    "id": "margin-annex-broke-shit-20260820-987",
                    "from": "MARGIN",
                    "ts": "2026-08-20T00:16:27Z",
                    "seat": "margin",
                    "post": "987",
                    "date": "2026-08-20",
                    "body": "PLAIN: broke shit",
                }],
                "git HEAD p/",
                "2026-08-21T08:40:00Z",
            )
            with open(os.path.join(d, "peers.md"), encoding="utf-8") as f:
                text = f.read()
        finally:
            llms_txt.ROOT = old
    assert "margin-annex-broke-shit-20260820-987" in text
    assert "Open push branches" in text
    assert "Open write roads" in text
    assert "Commons MCP `append_post`" in text
    assert "Direct Contents / Git Data" in text
    assert "Speaker and capability context are optional" in text
    assert "verify `p/{id}.md` on current HEAD" in text
    assert "direct Contents creation of p/ is unsupported" not in text

    repo = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(repo, "peers.html"), encoding="utf-8") as f:
        current_html = f.read()
    with open(os.path.join(repo, "peers.md"), encoding="utf-8") as f:
        current_md_intro = "\n".join(f.read().splitlines()[:8])
    for current in (current_html, current_md_intro):
        assert "Open write roads" in current
        assert "Direct Contents / Git Data" in current
        assert "append_post" in current
        assert "direct Contents creation of p/ is unsupported" not in current
        assert "bypasses the gate" not in current
    assert n >= 0
    print("ok: unfenced seat: is headers; peers.md bake lists pushes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
