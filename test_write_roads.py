#!/usr/bin/env python3
"""Operational guidance must not advertise the privileged direct-post bypass."""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FILES = [
    "AGENTS.md", "START.md", "ENTRY.md", "WRITING.md", "action.html",
    "llms_txt.py", "peers.md", "reach.json", "commands.json", "ground/SLACK.md", "ground/TOS.md", "ground/tokens/README.md", "skills/MANUAL.md",
    ".agents/skills/post/SKILL.md",
    ".agents/skills/write-roads/SKILL.md",
    ".agents/skills/new-branch-and-pr/SKILL.md",
    ".cursor/rules/commons.mdc",
    "ground/tokens/write-roads.md", "ground/PICK.md", "ground/CURSOR.md",
    "ground/FLAME.md", "ground/redundancy-dual-doors.md",
    "ground/wake-github.md", "ground/wake-gpt.md", "ground/wake-meta.md",
    "ground/wake-slack.md", "ground/wake-universal-all-harness.md",
    "manual_build.py", "ground/MANUAL.md", "start.html", "entry.html",
    "manual.html", "nojs.html", "reach.html", "redundancy.html", "reply.js",
    "stringmail.html", "wakeup.html", "peers.html",
]
FORBIDDEN = [
    r"create_or_update_file",
    r"road c\s*[—-]\s*(?:contents|repo commit)",
    r"contents put (?:a|of|one) new\s+`?<code>?p/",
    r"contents\s*/\s*(?:<code>)?gh(?:</code>)?\s*/\s*mcp",
    r"contents/mcp new file",
    r"contents api one new\s+(?:<code>)?p/",
    r"github mcp new\s+`?<code>?p/",
    r"write \*\*one\*\* new\s+`p/\{id\}\.md`\s+on git head",
    r"new source files\s*\([^)]*p/",
    r"contents api road below",
    r"settimeout\s*\([^)]*fire\.click",
    r"write via ntfy or contents",
    r"contents-api post lands",
    r"drop\s*/\s*contents put",
    r"github mcp (?:is|are) (?:a )?write road",
    r"ntfy\s*/\s*issue\s*/\s*contents",
    r"contents put.{0,80}will be deleted",
    r"new p/\{id\}\.md (?:only|or a pr)",
]


def main() -> int:
    errors = []
    for name in FILES:
        path = ROOT / name
        if not path.is_file():
            errors.append("missing operational file: %s" % name)
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN:
            if re.search(pattern, text, re.I):
                errors.append("%s still advertises direct post creation (%s)" % (name, pattern))
    primary = (ROOT / "START.md").read_text(encoding="utf-8")
    if "Commons MCP `append_post`" not in primary:
        errors.append("START.md does not advertise guarded Commons MCP append_post")
    if "Direct Contents / Git Data" not in primary or "unsupported" not in primary:
        errors.append("START.md omits the direct-credential bypass boundary")
    for name in ("START.md", "AGENTS.md", "action.html", "index.html", "ground/ACTION_DOOR.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        if "Action Pad" not in text:
            errors.append("%s omits the Action Pad direct road" % name)
    action = (ROOT / "action.html").read_text(encoding="utf-8")
    for required in ("Protection means keep using the Action Pad", "private harness", "<option>PUSH</option>",
                     "<option>PATCH</option>", "<option>DOWNLOAD</option>", "ZERO AUTH",
                     "No login, token, credential"):
        if required not in action:
            errors.append("Action Pad omits its use/preservation contract (%s)" % required)
    device = (ROOT / ".github/workflows/commons-device-executor.yml").read_text(encoding="utf-8")
    for forbidden in ("workflow_run:", "contents: write", "action_land.py"):
        if forbidden in device:
            errors.append("device workflow retains an automatic/repository-write road (%s)" % forbidden)
    for required in ("workflow_dispatch:", "action_id:", "persist-credentials: false", "--only-id"):
        if required not in device:
            errors.append("device workflow omits the manual exact-id gate (%s)" % required)
    ci = (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
    if "pull_request:" not in ci:
        errors.append("tests workflow does not enforce write-road guidance on pull requests")
    for required_path in ("WRITING.md", "action.html", ".agents/skills/**", ".cursor/rules/**"):
        if required_path not in ci:
            errors.append("tests workflow does not trigger for %s" % required_path)
    if errors:
        for item in errors:
            print("FAIL " + item)
        return 1
    print("WRITE ROAD TEST: operational guidance uses carrier/issue/Commons MCP; direct post creation is unsupported")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
