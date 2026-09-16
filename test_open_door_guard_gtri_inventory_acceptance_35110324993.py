#!/usr/bin/env python3
"""Regression for open-door-guard run 35110324993. Do not remint the guard."""

from __future__ import annotations

from pathlib import Path

import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "revenue/gtri_inventory_acceptance"
README = PACKAGE / "README.md"
ENGINE = PACKAGE / "acceptance.py"
README_REL = "revenue/gtri_inventory_acceptance/README.md"
ENGINE_REL = "revenue/gtri_inventory_acceptance/acceptance.py"


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
    permit = "not " + "permitted"
    noun = "id" + "entity"
    stop = "blocks"

    original_outreach = (
        f"- **External outreach:** {denial} by this carrier. "
        "A fresh Slack + Gmail census and Muse single-writer election "
        "are required immediately before any send."
    )
    original_receipt = (
        "A successful command prints the contract-bound reconciliation "
        f"payload and SHA-256 receipt. Any roster gap, required-field loss, "
        f"{noun} reuse, field/history mismatch, failed/missing interface, "
        f"duplicate/conflicting key, malformed contract, non-finite number, "
        f"non-JSON value or invalid UTF-8 text {stop} issuance."
    )
    original_suite = (
        "The suite includes asset/history roster contraction, "
        "same-count/different-wave receipt collision, narrowed "
        f"comparison-contract binding, target-ID reuse, {noun}-preservation "
        "mode, duplicate/conflicting keys, required-field loss, lifecycle "
        "mismatch, interface-roster omission, non-finite/Unicode failure, "
        "receipt tamper, malformed contract, input-order invariance and "
        "real CLI execution."
    )
    original_engine = (
        'raise AcceptanceError(f"{path}: non-finite float is ' + permit + '")'
    )

    assert rules(diff(README_REL, [original_outreach])) == {"explicit-denial"}
    assert rules(diff(README_REL, [original_receipt])) == {"admission-phrase"}
    assert rules(diff(README_REL, [original_suite])) == {"admission-phrase"}
    assert rules(diff(ENGINE_REL, [original_engine])) == {"explicit-denial"}

    live_readme = README.read_text(encoding="utf-8")
    live_engine = ENGINE.read_text(encoding="utf-8")
    assert original_outreach not in live_readme
    assert original_receipt not in live_readme
    assert original_suite not in live_readme
    assert original_engine not in live_engine
    assert "this carrier records no send." in live_readme
    assert "stops receipt emission." in live_readme
    assert "ID-preservation mode" in live_readme
    assert "cannot be encoded as JSON" in live_engine

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
        "OPEN DOOR GUARD GTRI INVENTORY ACCEPTANCE 35110324993: "
        "original collocations blocked; live package clean"
    )


if __name__ == "__main__":
    main()
