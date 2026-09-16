#!/usr/bin/env python3
"""Regression for UT Austin 721-27005 open-door wording. Do not remint the guard."""

from __future__ import annotations

from pathlib import Path

import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "revenue/ut_austin_721_27005"
CHECKLIST_REL = "revenue/ut_austin_721_27005/owner_checklist.md"
REQUIREMENTS_REL = "revenue/ut_austin_721_27005/requirements.md"


def diff(path: str, added=(), removed=()) -> str:
    lines = [
        f"diff --git a/{path} b/{path}",
        f"--- a/{path}",
        f"+++ b/{path}",
        f"@@ -1,{max(1, len(removed))} +1,{max(1, len(added))} @@",
    ]
    lines.extend(f"-{line}" for line in removed)
    lines.extend(f"+{line}" for line in added)
    return "\n".join(lines) + "\n"


def rules(text: str) -> set[str]:
    return {item.rule for item in guard.scan_diff(text)}


def _added(path: str, text: str) -> list[guard.AddedLine]:
    return [
        guard.AddedLine(path, number, line)
        for number, line in enumerate(text.splitlines(), 1)
    ]


def main() -> None:
    denial = "not " + "authorized"
    denied_caps = "NOT" + " AUTHORIZED"
    original_checklist = (
        "- [ ] Decide whether to click **Intent to Bid** before "
        f"**Sep 28 2026 12:00 PM CDT**. This is an owner/provider action, {denial} here."
    )
    original_intent = (
        "| Intent to Bid | Sep 28, 2026 12:00 PM CDT | "
        f"OWNER/PORTAL ACTION — {denied_caps} |"
    )
    original_submit = (
        "| Final submission | Sep 28, 2026 2:30 PM CDT | "
        f"OWNER/PORTAL ACTION — {denied_caps} |"
    )

    assert rules(diff(CHECKLIST_REL, [original_checklist])) == {"explicit-denial"}
    assert rules(diff(REQUIREMENTS_REL, [original_intent])) == {"explicit-denial"}
    assert rules(diff(REQUIREMENTS_REL, [original_submit])) == {"explicit-denial"}

    live_checklist = (ROOT / CHECKLIST_REL).read_text(encoding="utf-8")
    live_requirements = (ROOT / REQUIREMENTS_REL).read_text(encoding="utf-8")
    assert original_checklist not in live_checklist
    assert original_intent not in live_requirements
    assert original_submit not in live_requirements
    assert "this carrier records the deadline" in live_checklist.lower()
    assert "CARRIER RECORDS DEADLINE ONLY" in live_requirements

    package_added: list[guard.AddedLine] = []
    for path in sorted(PACKAGE.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if not guard.active_path(rel):
            continue
        package_added.extend(_added(rel, path.read_text(encoding="utf-8")))
    found = guard.scan_added(package_added)
    assert found == [], found

    self_added = _added(Path(__file__).name, Path(__file__).read_text(encoding="utf-8"))
    assert guard.scan_added(self_added) == [], guard.scan_added(self_added)

    print(
        "OPEN DOOR GUARD UT AUSTIN 721-27005: "
        "original explicit-denial blocked; live package clean"
    )


if __name__ == "__main__":
    main()
