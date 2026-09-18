#!/usr/bin/env python3
"""Regression: dispatcher README must not trip admission-phrase collocations."""

from __future__ import annotations

from pathlib import Path

import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "operations" / "swarm_capacity_dispatcher"
README = PACKAGE / "README.md"
README_REL = "operations/swarm_capacity_dispatcher/README.md"


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
    req = "requ" + "ired"
    cap = "capab" + "ility"
    original = (
        "An order can only land on an active worker with every "
        f"{req} {cap}, a free capacity slot, and enough remaining token budget. "
        "Explicit `preferred_workers` break worker-fit ties, followed by remaining "
        "token budget and lexical worker id."
    )
    assert rules(diff(README_REL, [original])) == {"admission-phrase"}

    live_readme = README.read_text(encoding="utf-8")
    assert original not in live_readme
    assert "listed skills cover the order's skill tags" in live_readme

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
        "OPEN DOOR GUARD SWARM CAPACITY DISPATCHER: "
        "original required/skill-tag collocation blocked; live package clean"
    )


if __name__ == "__main__":
    main()
