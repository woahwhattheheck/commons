#!/usr/bin/env python3
"""Compare official checker outputs generated with --max-decimal-places 6.

Rules 2.5 defines lexicographic saturation ordering, with NO cost tiebreak.
No locally reconstructed or rounded objective is substituted for checker output.
Inputs may be two files or roots containing <instance>/checker-6.json.
"""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path


def load_result(path):
    raw = path.read_bytes()
    result = json.loads(raw, parse_float=Decimal)
    if result.get("valid") not in (True, False) or type(result.get("valid")) is not bool:
        raise ValueError(f"{path}: expected checker valid boolean")
    record = {"valid": result["valid"], "path": str(path.resolve()),
              "sha256": hashlib.sha256(raw).hexdigest(), "total_cost": result.get("total_cost")}
    if not result["valid"]:
        return record
    saturations = result.get("saturations")
    if not isinstance(saturations, list) or not saturations:
        raise ValueError(f"{path}: valid output has no saturation vector")
    vector, keys = [], set()
    for row in saturations:
        value = Decimal(row["sat"])
        if not value.is_finite() or value < 0:
            raise ValueError(f"{path}: nonfinite or negative saturation")
        scaled = value * 1_000_000
        if scaled != scaled.to_integral_value():
            raise ValueError(f"{path}: saturation has >6 decimal places; rerun official checker at 6")
        key = (row["t"], str(row["from"]), str(row["to"]))
        if key in keys:
            raise ValueError(f"{path}: duplicate link/time coordinate {key}")
        keys.add(key)
        vector.append(value)
    record.update(vector=sorted(vector, reverse=True), keys=keys)
    return record


def compare(left, right):
    report = {"left_valid": left["valid"], "right_valid": right["valid"],
              "left_total_cost_diagnostic": left.get("total_cost"),
              "right_total_cost_diagnostic": right.get("total_cost"),
              "cost_used_in_ranking": False, "first_changed_rank": None}
    if not left["valid"] and not right["valid"]:
        report["winner"] = "no_feasible_solution"
        return report
    if left["valid"] != right["valid"]:
        report["winner"] = "left" if left["valid"] else "right"
        return report
    if left["keys"] != right["keys"]:
        raise ValueError("Outputs have different link/time coordinates: cannot compare instances or incomplete vectors")
    a, b = left["vector"], right["vector"]
    report.update(load_count=len(a), left_mlu=str(a[0]), right_mlu=str(b[0]))
    difference = next((i for i, pair in enumerate(zip(a, b)) if pair[0] != pair[1]), None)
    report["winner"] = "tie" if difference is None else ("left" if a[difference] < b[difference] else "right")
    if difference is not None:
        report.update(first_changed_rank=difference + 1,
                      left_at_first_change=str(a[difference]), right_at_first_change=str(b[difference]))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--checker-name", default="checker-6.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.left.is_file() and args.right.is_file():
        pairs = [("instance", args.left, args.right)]
    elif args.left.is_dir() and args.right.is_dir():
        left = {p.parent.name: p for p in args.left.glob("*/" + args.checker_name)}
        right = {p.parent.name: p for p in args.right.glob("*/" + args.checker_name)}
        if not left or left.keys() != right.keys():
            raise ValueError(f"Instance sets differ or empty: left={sorted(left)}, right={sorted(right)}")
        pairs = [(name, left[name], right[name]) for name in sorted(left)]
    else:
        raise ValueError("Provide two files or two existing benchmark roots")
    rows = []
    for name, lp, rp in pairs:
        left, right = load_result(lp), load_result(rp)
        row = {"instance": name, **compare(left, right),
               "left_checker_sha256": left["sha256"], "right_checker_sha256": right["sha256"],
               "left_checker_path": left["path"], "right_checker_path": right["path"]}
        rows.append(row)
    result = {"comparison": "official six-decimal saturation vectors; no cost tiebreak",
              "competition_rank": "unknown; these pairwise results do not establish rank against other teams",
              "counts": {outcome: sum(row["winner"] == outcome for row in rows)
                         for outcome in ("left", "right", "tie", "no_feasible_solution")}, "instances": rows}
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
