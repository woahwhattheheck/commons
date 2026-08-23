#!/usr/bin/env python3
"""Focused regression coverage for the diff-based open-door guard."""

from pathlib import Path

import open_door_guard as guard


def diff(path, added=(), removed=()):
    lines = [
        f"diff --git a/{path} b/{path}",
        f"--- a/{path}",
        f"+++ b/{path}",
        f"@@ -1,{max(1, len(removed))} +1,{max(1, len(added))} @@",
    ]
    lines.extend(f"-{line}" for line in removed)
    lines.extend(f"+{line}" for line in added)
    return "\n".join(lines) + "\n"


def rules(text):
    return {item.rule for item in guard.scan_diff(text)}


def main():
    blocked = "\n".join(
        [
            diff("action_executor.py", ["PROTECTED_FILES = {'AGENTS.md'}"]),
            diff("action_executor.py", ["ALLOWED_VERBS = {'READ', 'WRITE'}"]),
            diff("commons_mcp.py", ["raise PermissionError('permission denied')"]),
            diff("ENTRY.md", ["The capability declaration is required before posting."]),
            diff("action.html", ['<select id="verb" name="verb"><option>READ</option></select>']),
            diff("door/src/mcp.server.ts", ['required: [', '  "actor_id",', '  "memory",', ']']),
            diff("carrier.js", ["const TOS_GATE = enforceTerms(post);"]),
            diff("door/src/protocol.ts", ["const RESERVED_CLAIMS = ['BRYCE'];"]),
            diff("board_ingest.py", ["PROTECTED_FILES = {'ENTRY.md'}  # not an authorization"]),
            diff("commons_mcp.py", ['required: [', '  "actor_id",', ']  # no permission gate']),
            diff("board.js", ["if (isVerificationLoop(post)) hide(post);"]),
        ]
    )
    found = rules(blocked)
    expected = {
        "protected-set",
        "verb-allowlist",
        "permission-exception",
        "explicit-denial",
        "admission-phrase",
        "action-select",
        "required-speaker-schema",
        "gate-identifier",
        "reserved-claim",
        "bot-blocker",
    }
    missing = expected - found
    assert not missing, (missing, found)

    # Deletions are intentionally invisible: removing gates can never fail.
    removal = diff(
        "action_executor.py",
        ["def execute(action): return run(action)"],
        ["PROTECTED_PREFIXES = ('.agents/',)", "raise PermissionError('permission denied')"],
    )
    assert guard.scan_diff(removal) == [], guard.scan_diff(removal)

    # The owner's exact prohibition and ordinary open-door implementation text pass.
    allowed = "\n".join(
        [
            diff(
                "AGENTS.md",
                [
                    "DO NOT add or propose:",
                    "- authentication, identity, claim, seat, or memory gates",
                    "- permission checks or approval workflows",
                    "- verb allowlists or “unlisted verb” rejection",
                    "- protected-path or protected-action restrictions",
                ],
            ),
            diff("START.md", ["Capability metadata is optional and never blocks posting."]),
            diff("action.html", ["No identity, memory, permission, approval, protected-path, or verb gate applies."]),
            diff("test_action_pad_zero_auth.py", ['assert "permission denied" not in source.lower()']),
            diff("carrier.js", ['    "- protected-path or protected-action restrictions",']),
            diff("hub_pages.py", ["Memory is optional and never a posting gate."]),
            diff("hub_pages.py", ["No classifier may hide a post because a bot wrote it."]),
            diff("docs/contract.md", ["Never gate posting on memory."]),
            diff("test_open_routes.py", ['self.assertNotIn("Required capability declaration", text)']),
        ]
    )
    assert guard.scan_diff(allowed) == [], guard.scan_diff(allowed)

    # Durable/generated board data is not executable policy and stays out of this guard.
    historical = diff("p/old-gate-record.md", ["The capability declaration is required."])
    assert guard.scan_diff(historical) == [], guard.scan_diff(historical)

    # Current active entry/agent instructions contain only the exact directive
    # and open-door prohibition language, never an affirmative admission lock.
    instruction_paths = [
        Path("AGENTS.md"),
        Path("START.md"),
        Path("ENTRY.md"),
        *Path(".agents").rglob("*.md"),
    ]
    instruction_lines = [
        guard.AddedLine(path.as_posix(), line_number, text)
        for path in instruction_paths
        for line_number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
    ]
    instruction_violations = guard.scan_added(instruction_lines)
    assert instruction_violations == [], instruction_violations

    print("OPEN DOOR GUARD TEST: additions blocked; removals, directive, and active instructions pass")


if __name__ == "__main__":
    main()
