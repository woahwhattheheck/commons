# SPDX-License-Identifier: Apache-2.0
"""Fail-closed provenance audit for the V1 -> V2/current carry-value seam."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
V1 = LAB / "runtime/variants/v1/scheduler.py"
V2 = LAB / "runtime/variants/v2/scheduler.py"
CURRENT = LAB / "scheduler.py"
ABLATION = HERE / "liquidity_haircut.py"
V1_NEEDLE = "carry=.95*self.single(inv,remaining)[0]"
FULL_NEEDLE = "carry=float(self.single(inv,remaining)[0])"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _score_ast(path: Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    matches = [
        item
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "MarketPath"
        for item in node.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "score"
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected one MarketPath.score in {path}; found {len(matches)}")
    return ast.dump(matches[0], include_attributes=False)


def build_report(lab: Path = LAB) -> dict[str, Any]:
    paths = {
        "v1": lab / "runtime/variants/v1/scheduler.py",
        "v2": lab / "runtime/variants/v2/scheduler.py",
        "current": lab / "scheduler.py",
        "ablation": HERE / "liquidity_haircut.py",
        "candidate": HERE / "candidate.py",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing source: " + ", ".join(missing))

    text = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    checks = {
        "v1_has_one_095_carry": text["v1"].count(V1_NEEDLE) == 1,
        "v1_has_no_full_carry": FULL_NEEDLE not in text["v1"],
        "v2_has_one_full_carry": text["v2"].count(FULL_NEEDLE) == 1,
        "v2_has_no_095_carry": V1_NEEDLE not in text["v2"],
        "current_has_one_full_carry": text["current"].count(FULL_NEEDLE) == 1,
        "current_has_no_095_carry": V1_NEEDLE not in text["current"],
        "v2_current_score_ast_equal": _score_ast(paths["v2"]) == _score_ast(paths["current"]),
        "ablation_declares_095": "DEFAULT_CARRY_DISCOUNT = 0.95" in text["ablation"],
        "candidate_delegates_canonical_agent": (
            "return _CANONICAL.agent(observation, configuration)" in text["candidate"]
            and "instance.act(observation" not in text["candidate"]
        ),
    }
    report = {
        "schema_version": 1,
        "operation": "titan-v3-horizon-liquidity-20260909-sol-kepler-01",
        "decision": "PASS" if all(checks.values()) else "FAIL",
        "claim": {
            "v1_artificial_horizon_carry_factor": 0.95,
            "v2_artificial_horizon_carry_factor": 1.0,
            "current_artificial_horizon_carry_factor": 1.0,
            "candidate_artificial_horizon_carry_factor": 0.95,
            "canonical_files_modified": False,
        },
        "checks": checks,
        "sources": {
            name: {
                "path": str(path.relative_to(lab.parent.parent.parent)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for name, path in paths.items()
        },
    }
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    report = build_report()
    payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(payload, encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "checks": report["checks"]}, sort_keys=True))
    return 0 if report["decision"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
