# SPDX-License-Identifier: Apache-2.0
"""Exact-current route-bank census for T02 land unlock timing."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

from land_unlock_jit import audit_routes  # noqa: E402
from frozen_selected import FrozenSelected  # noqa: E402
import scheduler  # noqa: E402


PINNED_BLOBS = {
    "frozen_selected.py": "fc7baf5c179818a55037f6a61d92984d81d1a21c",
    "scheduler.py": "a483b24dd72b580d7d8811636b54d2d44f391575",
    "mechanics.py": "044a4f9c0a4a44dde10ada57563238bcaf82075d",
    "reference/next-panel/vendor/arlene.py": "bdb9cf58148a3c7961c085f4902759537decabf6",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def route_digest(routes) -> str:
    payload = json.dumps(routes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=HERE / "CURRENT-CENSUS.json")
    parser.add_argument("--require-relocation", action="store_true")
    args = parser.parse_args()

    consumer = FrozenSelected()
    routes = consumer.controller.R
    checkpoints = tuple(int(row[0]) for row in scheduler.parent.DECISIONS)
    actual_blobs = {name: git_blob(LAB / name) for name in PINNED_BLOBS}
    mismatches = {
        name: {"expected": PINNED_BLOBS[name], "actual": actual_blobs[name]}
        for name in PINNED_BLOBS
        if actual_blobs[name] != PINNED_BLOBS[name]
    }
    if mismatches:
        print(json.dumps({"source_mismatch": mismatches}, sort_keys=True))
        return 2

    report = audit_routes(routes, checkpoints=checkpoints)
    report["source"] = {
        "git_blobs": actual_blobs,
        "sha256": {name: sha256(LAB / name) for name in PINNED_BLOBS},
        "route_bank_sha256": route_digest(routes),
        "route_lengths": {str(key): len(value) for key, value in sorted(routes.items())},
        "route_ids": sorted(str(key) for key in routes),
        "checkpoints": list(checkpoints),
        "max_market_orders": 10,
        "turns_per_day": 24,
    }
    ops = Counter(
        op
        for item in report["relocations"]
        for _step, _slot, op in item["intervening_market_ops"]
    )
    report["summary"] = {
        "intervening_market_ops": dict(sorted(ops.items())),
        "max_saved_cash_turns": max(
            (int(item["saved_cash_turns"]) for item in report["relocations"]),
            default=0,
        ),
        "land_targets": dict(
            sorted(Counter(item["target_quadrant"] for item in report["purchases"]).items())
        ),
        "effectless_purchases": sum(
            item["first_effect_step"] is None for item in report["purchases"]
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(report, sort_keys=True, indent=2) + "\n"
    args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps({
        "route_count": report["route_count"],
        "purchase_count": report["purchase_count"],
        "relocation_count": report["relocation_count"],
        "routes_with_relocations": report["routes_with_relocations"],
        **report["summary"],
        "output": str(args.output),
    }, sort_keys=True))
    if args.require_relocation and report["relocation_count"] == 0:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
