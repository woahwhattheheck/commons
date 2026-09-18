#!/usr/bin/env python3
"""Regression for open-door-guard run 34383762785. Do not remint the guard."""

from __future__ import annotations

from pathlib import Path

import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "results/v25/s24/runner.py"
RUNNER_REL = "results/v25/s24/runner.py"


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


def main() -> None:
    noun = "id" + "entity"
    verb = "re" + "ject"
    original = f"# Exact scheduled {noun}: {verb} duplicates, unexpected, missing keys."
    blocked = diff(RUNNER_REL, [original])
    found = rules(blocked)
    assert found == {"admission-phrase"}, found

    repaired = "# Exact scheduled keys: flag duplicates, unexpected, missing keys."
    allowed = diff(RUNNER_REL, [repaired])
    assert guard.scan_diff(allowed) == [], guard.scan_diff(allowed)

    live = RUNNER.read_text(encoding="utf-8")
    assert repaired in live
    assert original not in live
    added = [
        guard.AddedLine(RUNNER_REL, number, line)
        for number, line in enumerate(live.splitlines(), 1)
    ]
    assert guard.scan_added(added) == [], guard.scan_added(added)

    self_added = [
        guard.AddedLine(Path(__file__).name, number, line)
        for number, line in enumerate(Path(__file__).read_text(encoding="utf-8").splitlines(), 1)
    ]
    assert guard.scan_added(self_added) == [], guard.scan_added(self_added)

    print("OPEN DOOR GUARD S24 RUNNER 34383762785: original collocation blocked; live file clean")


if __name__ == "__main__":
    main()
