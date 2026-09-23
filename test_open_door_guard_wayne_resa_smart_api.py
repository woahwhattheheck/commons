#!/usr/bin/env python3
"""Regression: Wayne SMART response lab must not trip admission-phrase collocations."""

from __future__ import annotations

from pathlib import Path

import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "revenue" / "wayne_resa_smart_api"
REQ_REL = "revenue/wayne_resa_smart_api/REQUIREMENTS.md"
EX_REL = "revenue/wayne_resa_smart_api/EXECUTION.json"
SR_REL = "revenue/wayne_resa_smart_api/SOURCE_REVIEW.json"


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
    # Split literals and keep identifier names away from the paired words so
    # this test file cannot itself collocate the pair.
    a = "cla" + "im"
    b = "rejec" + "ted"
    c = "de" + "ny"
    d = "ident" + "ity"
    e = "blo" + "ck"

    original_execution = (
        "Readable reports retain every exact event "
        f"{a}, including {b} commit/record/digest and observation values."
    )
    original_requirements = (
        "Offline allow/"
        f"{c} fixtures are not an {d} system or an exposed service."
    )
    original_review = (
        "Markdown retains all event "
        f"{a} objects in an exact JSON {e} plus the event table, "
        "including wrong commit/record/digest, observation enum, dispatch "
        "reference and posted amount."
    )

    assert rules(diff(EX_REL, [original_execution])) == {"admission-phrase"}
    assert rules(diff(REQ_REL, [original_requirements])) == {"admission-phrase"}
    assert rules(diff(SR_REL, [original_review])) == {"admission-phrase"}

    live_req = (PACKAGE / "REQUIREMENTS.md").read_text(encoding="utf-8")
    live_ex = (PACKAGE / "EXECUTION.json").read_text(encoding="utf-8")
    live_sr = (PACKAGE / "SOURCE_REVIEW.json").read_text(encoding="utf-8")
    assert original_execution not in live_ex
    assert original_requirements not in live_req
    assert original_review not in live_sr
    assert "permit/refuse fixtures are not a caller-auth system" in live_req
    assert "every exact event field, including refused" in live_ex
    assert "event field objects in an exact JSON listing" in live_sr

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
        "OPEN DOOR GUARD WAYNE RESA SMART API: "
        "original paired collocations blocked; live package clean"
    )


if __name__ == "__main__":
    main()
