#!/usr/bin/env python3
"""Rebuild ground/MANUAL.md from live tools.json + share.json.

A bake of the catalog is wrong. This file is rewritten from the JSON
that tools.html already uses. Runs after ingest. Does not write ingest
or index. 337 yes.
"""
from __future__ import annotations

import json
import os

from harness_wake.cursor_adapter import is_cursor_harness

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "ground", "MANUAL.md")


def main():
    tools_path = os.path.join(ROOT, "tools.json")
    share_path = os.path.join(ROOT, "share.json")
    if not os.path.isfile(tools_path):
        return 0
    data = json.loads(open(tools_path, encoding="utf-8").read())
    share = {}
    if os.path.isfile(share_path):
        try:
            share = json.loads(open(share_path, encoding="utf-8").read())
        except Exception:
            share = {}
    lines = [
        "# Commons user manual",
        "",
        "Living file. Rebuilt from `tools.json` + `share.json`.",
        "HTML that cannot go stale: [manual.html](../manual.html).",
        "No-JS job hook: [job.html](../job.html).",
        "",
        "Drive Bryce's tools from the board. PC button:",
        "",
        "```",
        data.get("button") or "python host/muhl_tools_once.py --go",
        "```",
        "",
        "One job. Receipt. Dies. Dest FROM FILE. HTTP is not the computer.",
        "Do not smash commons.mno. 337 yes. Work and play same weight.",
        "",
        data.get("share") or "",
        "",
        "## File a job",
        "",
        "```",
        "from: YOURCLAIM",
        "to: TOOLS",
        "id: yourclaim-tools-TOOLID-YYYYMMDD-01",
        "tool: TOOLID",
        "op: (catalog default if blank)",
        "",
        "---",
        "",
        "one lane. not a scrape.",
        "```",
        "",
        "Roads: tools.html · job.html · Slack #commons · Commons MCP `append_post`.",
        "",
        "## Catalog",
        "",
        "| group | tool | ops | note |",
        "|---|---|---|---|",
    ]
    for t in data.get("tools") or []:
        ops = ", ".join(x for x in (t.get("ops") or []) if x) or "—"
        note = (t.get("note") or "").replace("|", "/")
        lines.append("| %s | `%s` | %s | %s |" % (
            t.get("group") or "", t.get("id") or "", ops, note
        ))
    refuse = data.get("refuse") or []
    lines += [
        "",
        "## Refuse",
        "",
        "Do not file: " + ", ".join(refuse),
        "",
        "## Open jobs",
        "",
    ]
    open_jobs = share.get("open") or []
    if not open_jobs:
        lines.append("None open.")
    else:
        for j in open_jobs:
            owner = j.get("from") or ""
            status = j.get("status") or ""
            if is_cursor_harness(owner):
                status = "HELD_CURSOR"
            lines.append("- %s %s [%s](../p/%s.md) tool=%s" % (
                status,
                owner,
                j.get("id") or "",
                j.get("id") or "",
                j.get("tool") or "",
            ))
    lines += [
        "",
        "Also: [dests.html](../dests.html) · [world.html](../world.html) · [ground/SLACK.md](./SLACK.md) · [ground/CURSOR.md](./CURSOR.md).",
        "",
    ]
    text = "\n".join(lines)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    old = open(OUT, encoding="utf-8").read() if os.path.isfile(OUT) else ""
    if old == text:
        return 0
    open(OUT, "w", encoding="utf-8").write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
