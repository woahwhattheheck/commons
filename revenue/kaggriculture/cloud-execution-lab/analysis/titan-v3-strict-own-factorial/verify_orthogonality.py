#!/usr/bin/env python3
"""Prove that the combined archive is the bytewise union of two source factors."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ARMS = ("incumbent", "strict-only", "own-only", "combined")
EXPECTED = {
    "strict-only": {"pressure_priority.py", "titan_runtime.py"},
    "own-only": {"selected_sell_core.py"},
    "combined": {"pressure_priority.py", "titan_runtime.py", "selected_sell_core.py"},
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def runtime_map(root: Path, arm: str) -> dict[str, dict]:
    manifest = read_json(root / "arms" / arm / "CURRENT-SOURCE.json")
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict) or not runtime:
        raise ValueError(f"{arm}: missing runtime map")
    return runtime


def changed_members(base: dict[str, dict], other: dict[str, dict]) -> set[str]:
    if set(base) != set(other):
        raise AssertionError("runtime member set changed between arms")
    return {
        name
        for name in base
        if (base[name].get("sha256"), base[name].get("bytes"))
        != (other[name].get("sha256"), other[name].get("bytes"))
    }


def verify(root: Path) -> dict:
    root = root.resolve()
    maps = {arm: runtime_map(root, arm) for arm in ARMS}
    base = maps["incumbent"]
    changes = {arm: changed_members(base, maps[arm]) for arm in ARMS[1:]}
    for arm, expected in EXPECTED.items():
        if changes[arm] != expected:
            raise AssertionError(
                f"{arm}: changed runtime members {sorted(changes[arm])}; "
                f"expected {sorted(expected)}"
            )

    for member in base:
        combined = maps["combined"][member]
        if member in EXPECTED["strict-only"]:
            expected = maps["strict-only"][member]
        elif member in EXPECTED["own-only"]:
            expected = maps["own-only"][member]
        else:
            expected = base[member]
        if combined != expected:
            raise AssertionError(
                f"combined member {member!r} is not the exact owning arm's bytes"
            )

    receipts = {
        arm: read_json(root / "arms" / arm / "CURRENT-ARCHIVE.json") for arm in ARMS
    }
    digests = {arm: receipt.get("sha256") for arm, receipt in receipts.items()}
    if len(set(digests.values())) != len(ARMS):
        raise AssertionError(f"archive arms are not byte-distinct: {digests}")
    file_counts = {receipt.get("runtime_files") for receipt in receipts.values()}
    if len(file_counts) != 1:
        raise AssertionError("runtime file count changed across factor arms")

    report = {
        "schema": "titan-v3-factorial-orthogonality/v1",
        "status": "PASS",
        "changed_runtime_members": {
            arm: sorted(members) for arm, members in changes.items()
        },
        "combined_is_exact_factor_union": True,
        "archive_sha256": digests,
        "runtime_files": file_counts.pop(),
        "gameplay_claim": None,
        "promotion_authorized": False,
    }
    (root / "ORTHOGONALITY.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.matrix), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
