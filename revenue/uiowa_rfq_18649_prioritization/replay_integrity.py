#!/usr/bin/env python3
"""Reproduce UIOWA-084's integrity repair and synthetic decision change offline."""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import random
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

HERE = Path(__file__).resolve().parent
BASELINE_BLOB = "007697dd2485f7470107d1962c8f660873b4dd84"
FIXTURE_BLOBS = {
    "recommendations.synthetic.csv": "2fa2751292642124d323525a6c5f84ca1f74aad5",
    "weights.json": "6e699f243338df7477519c48592c4f8b8eb784b8",
}


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


class ReplaySnapshot(NamedTuple):
    """The exact source and fixture bytes used throughout one replay."""
    baseline: bytes
    current: bytes
    recommendations: bytes
    weights: bytes


def _capture(baseline_path: Path) -> ReplaySnapshot:
    # Path reads happen only here, once per input. Later edits cannot change the
    # checked baseline, executed source, fixture comparisons or receipt identity.
    snapshot = ReplaySnapshot(
        Path(baseline_path).read_bytes(),
        (HERE / "prioritize.py").read_bytes(),
        (HERE / "recommendations.synthetic.csv").read_bytes(),
        (HERE / "weights.json").read_bytes(),
    )
    require(git_blob(snapshot.baseline) == BASELINE_BLOB,
            "baseline does not match the retained Git blob")
    for name, data in (("recommendations.synthetic.csv", snapshot.recommendations),
                       ("weights.json", snapshot.weights)):
        require(git_blob(data) == FIXTURE_BLOBS[name], f"synthetic fixture changed: {name}")
    return snapshot


def _module_from_bytes(name: str, source: bytes) -> ModuleType:
    """Load these trusted repository source bytes, not a pathname or cached pyc.

    This is execution provenance, not a sandbox. The baseline has a fixed pin;
    current calculator source is operator-controlled repository code. No identity
    is inferred from a previously imported module or a later disk read.
    """
    module = ModuleType(name)
    module.__file__ = f"<uiowa084:{name}:{git_blob(source)}>"
    code = compile(source, module.__file__, "exec", dont_inherit=True,
                   optimize=sys.flags.optimize)
    exec(code, module.__dict__)
    return module


def replay(baseline_path: Path, out: Path) -> dict:
    out = Path(out)
    require(not out.exists() and not out.is_symlink(), "choose a fresh output directory")
    snapshot = _capture(baseline_path)
    old = _module_from_bytes("uiowa084_retained_baseline", snapshot.baseline)
    current = _module_from_bytes("uiowa084_current_snapshot", snapshot.current)
    # The legacy run APIs take file paths. Give them private copies of captured
    # fixtures, never the live operator files which were validated earlier.
    with tempfile.TemporaryDirectory(prefix="uiowa084-snapshots-") as temp:
        inputs = Path(temp)
        (inputs / "recommendations.synthetic.csv").write_bytes(snapshot.recommendations)
        (inputs / "weights.json").write_bytes(snapshot.weights)
        return _replay_captured(snapshot, old, current, inputs, out)


def _replay_captured(snapshot: ReplaySnapshot, old: ModuleType,
                     prioritize: ModuleType, inputs: Path, out: Path) -> dict:
    config = prioritize.load_weights(inputs / "weights.json")
    records = prioritize.load_recommendations(inputs / "recommendations.synthetic.csv")
    rng = random.Random(20260919)
    for case in range(250):
        items = copy.deepcopy(records)
        for item in items:
            for dimension in (*prioritize.DIMENSIONS, "complexity"):
                item[dimension] = None if rng.randrange(10) == 0 else rng.randrange(501) / 100
        weights = config["profiles"][rng.choice(list(config["profiles"]))]
        epsilon = rng.choice([0, 0.02, 0.1, 1, 4])
        require(old.rank_profile(items, "equivalence", weights, epsilon) ==
                prioritize.rank_profile(items, "equivalence", weights, epsilon),
                f"ranking changed in seeded case {case}")
    with tempfile.TemporaryDirectory(prefix="uiowa084-reference-") as temp:
        temp = Path(temp)
        original = old.run(inputs / "recommendations.synthetic.csv", inputs / "weights.json", temp / "old")
        repaired = prioritize.run(inputs / "recommendations.synthetic.csv", inputs / "weights.json", temp / "new")
        require(original == repaired, "original fixture rows changed")
        original_outputs = {path.name: path.read_bytes() for path in (temp / "old").iterdir()}
        require(len(original_outputs) == 7, "unexpected baseline output count")
        require(all((temp / "new" / name).read_bytes() == data for name, data in original_outputs.items()),
                "original exported bytes changed")
    # Only now create persistent demonstration artifacts, all with exclusive paths.
    out.mkdir(parents=True, exist_ok=False)
    rows = list(csv.reader(io.StringIO((inputs / "recommendations.synthetic.csv").read_text(encoding="utf-8"), newline="")))
    for row in rows[1:]:
        if row[0] == "R006":
            row[3] = "5"
            row[-1] = "SYNTHETIC WHAT-IF: security effect assumed 5; not observed evidence"
    changed = out / "security_assumption.synthetic.csv"
    with changed.open("x", encoding="utf-8", newline="") as stream:
        csv.writer(stream).writerows(rows)
    before = prioritize.run(inputs / "recommendations.synthetic.csv", inputs / "weights.json", out / "baseline")
    after = prioritize.run(changed, inputs / "weights.json", out / "security_assumption")
    table = []
    for name in config["profiles"]:
        old_row = next(row for row in before[name] if row["id"] == "R006")
        new_row = next(row for row in after[name] if row["id"] == "R006")
        require(old_row["status"] == "HOLD_MISSING_ESTIMATE" and old_row["priority_score"] is None,
                "missing estimate lost its HOLD")
        table.append({"profile": name, "before_status": old_row["status"],
                      "after_rank": new_row["rank"], "after_score": new_row["priority_score"],
                      "leaders_before": [row["id"] for row in before[name] if row["rank"] == 1],
                      "leaders_after": [row["id"] for row in after[name] if row["rank"] == 1]})
    receipt = {"provenance": "SYNTHETIC PLANNING EXPERIMENT; no University findings or decisions",
               "seed": 20260919, "seeded_comparisons_passed": 250,
               "unchanged_profile_record_rows": sum(map(len, before.values())),
               "unchanged_output_files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(original_outputs.items())},
               "baseline_blob": BASELINE_BLOB,
               "tested_source_blob": git_blob(snapshot.current),
               "fixture_blobs": {
                   "recommendations.synthetic.csv": git_blob(snapshot.recommendations),
                   "weights.json": git_blob(snapshot.weights)},
               "source_binding": "captured source compiled directly; captured fixtures used throughout",
               "python": sys.version, "optimized": bool(sys.flags.optimize), "change": table}
    with (out / "replay_receipt.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print("PASS: 250 seeded comparisons; 35 unchanged profile/record rows; 7 byte-identical original outputs")
    for row in table:
        print(f"{row['profile']}: R006 HOLD -> rank {row['after_rank']}, score {row['after_score']:.4f}")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        replay(args.baseline, args.out)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
