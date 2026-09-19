#!/usr/bin/env python3
"""Regression for ProofPatch threat-model admission-phrase collocation.

Imported by test_open_door_guard.py so the open-door-guard workflow matrix
keeps the original required/claim line rejectable and the rewritten live
document clean. Run 35449373545 / SHA b5224a67 / PR 15635.
"""

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


def check():
    path = "competitions/nebius-proofpatch-2026/docs/THREAT_MODEL.md"
    blocked = diff(
        path,
        [
            "- The claimed reproduction must fail while the baseline digest remains unchanged; verifier-selected executor replay is required before that reproduction claim can be authenticated.",
        ],
    )
    found = rules(blocked)
    assert found == {"admission-phrase"}, found
    allowed = diff(
        path,
        [
            "- The claimed reproduction must fail while the baseline digest remains unchanged; verifier-selected executor replay must complete before that reproduction result counts as independently executed truth.",
        ],
    )
    assert guard.scan_diff(allowed) == [], guard.scan_diff(allowed)
    live = Path(path)
    live_lines = [
        guard.AddedLine(live.as_posix(), line_number, text)
        for line_number, text in enumerate(live.read_text(encoding="utf-8").splitlines(), 1)
    ]
    assert guard.scan_added(live_lines) == []


if __name__ == "__main__":
    check()
    print("OPEN DOOR PROOFPATCH THREAT TEST: admission-phrase collocation still blocked; rewritten live line passes")
