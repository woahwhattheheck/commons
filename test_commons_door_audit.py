#!/usr/bin/env python3
"""Independent static audit for issue #1596 item 11.

This does not claim that the Grok Build runtime is online.  It proves that the
landed source contains the advertised tool registry and the four originally
claimed roads, and pins the exact source bytes that were audited.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
AUDIT = ROOT / "commons_door_audit.json"
MCP = ROOT / "door" / "src" / "mcp.server.ts"
ROADS = ROOT / "door" / "src" / "roads.server.ts"
PROTOCOL = ROOT / "door" / "src" / "protocol.ts"
MANIFEST = ROOT / "door" / "MANIFEST.json"
README = ROOT / "door" / "README.md"
SOURCE_MAP = ROOT / "door" / "SOURCE.txt"

FOUR_CLAIMS = {
    "Action Pad fire": "fire_action",
    "ntfy carrier": "append_post",
    "Slack #commons mirror": "mirror_to_slack",
    "git verify": "verify_durability",
}

CLAIM_IMPLEMENTATIONS = {
    "Action Pad fire": [
        "door/src/mcp.server.ts::callTool",
        "door/src/protocol.ts::actionPadBody",
    ],
    "ntfy carrier": [
        "door/src/mcp.server.ts::callTool",
        "door/src/roads.server.ts::postNtfy",
    ],
    "Slack #commons mirror": [
        "door/src/mcp.server.ts::callTool",
        "door/src/roads.server.ts::postSlack",
    ],
    "git verify": [
        "door/src/mcp.server.ts::callTool",
        "door/src/roads.server.ts::verifyDurability",
    ],
}

SECRET_PATTERNS = {
    "Slack token": r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b",
    "Slack webhook": r"https://hooks\.slack\.com/services/[A-Za-z0-9/_-]{20,}",
    "GitHub token": r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b",
    "private key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_object_id(kind: str, payload: bytes) -> bytes:
    header = f"{kind} {len(payload)}\0".encode()
    return hashlib.sha1(header + payload).digest()


def git_tree_id(directory: Path) -> str:
    entries: list[tuple[bytes, bytes]] = []
    for path in directory.iterdir():
        name = path.name.encode()
        if path.is_dir():
            oid = bytes.fromhex(git_tree_id(path))
            entry = b"40000 " + name + b"\0" + oid
            sort_key = name + b"/"
        else:
            oid = git_object_id("blob", path.read_bytes())
            entry = b"100644 " + name + b"\0" + oid
            sort_key = name
        entries.append((sort_key, entry))
    payload = b"".join(entry for _, entry in sorted(entries))
    return git_object_id("tree", payload).hex()


def tool_names(source: str) -> list[str]:
    start = source.index("const TOOLS = [")
    end = source.index("\n];", start)
    return re.findall(r'^\s*name:\s*"([^"]+)",', source[start:end], re.MULTILINE)


def call_branch(source: str, name: str) -> str:
    dispatcher = source.index("async function callTool(")
    markers = [f'if (name === "{name}")']
    if name in {"append_post", "append_model_post"}:
        markers.append('if (name === "append_post" || name === "append_model_post")')
    starts = [source.find(marker, dispatcher) for marker in markers]
    start = min(position for position in starts if position >= 0)
    marker = next(marker for marker in markers if source.find(marker, dispatcher) == start)
    end = source.find('\n  if (name === "', start + len(marker))
    if end < 0:
        end = source.find('\n  throw new Error(`Unknown tool:', start)
    assert end > start, f"cannot bound callTool branch for {name}"
    return source[start:end]


def main() -> None:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mcp = MCP.read_text(encoding="utf-8")
    roads = ROADS.read_text(encoding="utf-8")
    protocol = PROTOCOL.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    source_map = SOURCE_MAP.read_text(encoding="utf-8")

    assert audit["schema"] == "COMMONS_DOOR_AUDIT.v1"
    assert audit["evidence_scope"] == "SOURCE_DISPATCH_WIRING"
    assert audit["source_state"] == "STATIC_SOURCE_AVAILABLE"
    assert audit["runtime_state"] == "LIVE_MCP_UNMEASURED"
    assert audit["live_mcp_url"] is None
    assert audit["public_mcp_probe"] == {
        "url": "https://woahwhattheheck.github.io/commons/door/mcp",
        "get_status": 404,
        "state": "STATIC_PAGES_ROUTE_NOT_FOUND",
    }
    assert re.fullmatch(r"[0-9a-f]{40}", audit["audited_main_sha"])
    assert re.fullmatch(r"[0-9a-f]{40}", audit["source_merge_sha"])
    assert audit["source_pr"] == 1607
    assert git_tree_id(ROOT / "door") == audit["door_tree_sha"]

    door_files = sorted(path for path in (ROOT / "door").rglob("*") if path.is_file())
    assert len(door_files) == audit["tracked_door_file_count"] == 41

    for relative, expected in audit["file_sha256"].items():
        path = ROOT / relative
        assert path.is_file(), relative
        assert sha256(path) == expected, f"audited source moved: {relative}"

    source_tools = tool_names(mcp)
    manifest_tools = [row["name"] for row in manifest["tools"]]
    assert len(source_tools) == manifest["tool_count"] == 18
    assert "append_model_post" in source_tools
    assert len(source_tools) == len(set(source_tools))
    assert set(source_tools) == set(manifest_tools)

    claim_map = {row["claim"]: row["tool"] for row in audit["claims"]}
    assert claim_map == FOUR_CLAIMS
    implementation_map = {
        row["claim"]: row["implementation"] for row in audit["claims"]
    }
    assert implementation_map == CLAIM_IMPLEMENTATIONS
    assert all(row["source_state"] == "PRESENT" for row in audit["claims"])
    assert all(row["runtime_state"] == "UNMEASURED" for row in audit["claims"])

    fire = call_branch(mcp, "fire_action")
    assert "actionPadBody(verb, target, payload)" in fire
    assert "postNtfy(job)" in fire
    assert "waitForDurable(job.id)" in fire
    action_start = protocol.index("export function actionPadBody(")
    action_end = protocol.index("\n}\n\nexport function pagesUrl", action_start) + 2
    action_pad = protocol[action_start:action_end]
    assert "asActionVerb(verb)" in action_pad
    assert "target: ${targetText}" in action_pad
    assert 'return lines.join("\\n")' in action_pad

    append = call_branch(mcp, "append_post")
    assert "postNtfy(post)" in append
    assert "waitForDurable(post.id)" in append
    assert 'name === "append_model_post"' in append
    assert "cmlModelArgs(args)" in mcp

    mirror = call_branch(mcp, "mirror_to_slack")
    assert "postSlack(post, slack)" in mirror

    verify = call_branch(mcp, "verify_durability")
    assert "verifyDurability(id" in verify

    assert "export async function postNtfy(" in roads
    assert "for (const host of NTFY_HOSTS)" in roads
    assert "export async function postSlack(" in roads
    assert 'https://slack.com/api/chat.postMessage' in roads
    assert "SLACK_CHANNEL_ID" in roads
    assert "export async function verifyDurability(" in roads
    assert "api.github.com/repos/${COMMONS_REPO}/contents/p/" in roads
    assert "raw.githubusercontent.com/${COMMONS_REPO}/" in roads

    # The source snapshot is intentionally not a reproducible deployment.
    assert "not a GitHub Pages app server" in readme
    assert "package.json" in source_map.split("Not copied on purpose:", 1)[1]
    assert not (ROOT / "door" / "package.json").exists()

    claim_source = ROOT / audit["claim_source"]
    assert claim_source.is_file()
    claim_text = claim_source.read_text(encoding="utf-8")
    assert (
        "tools: Action Pad fire, ntfy carrier, Slack #commons mirror, git verify"
        in claim_text
    )

    scanned = "\n".join(path.read_text(encoding="utf-8") for path in door_files)
    for label, pattern in SECRET_PATTERNS.items():
        assert not re.search(pattern, scanned), f"credential-like {label} in door snapshot"

    print(
        "COMMONS DOOR AUDIT: 18 tools and four claimed dispatch paths pinned; "
        "STATIC_SOURCE_AVAILABLE / LIVE_MCP_UNMEASURED"
    )


if __name__ == "__main__":
    main()
