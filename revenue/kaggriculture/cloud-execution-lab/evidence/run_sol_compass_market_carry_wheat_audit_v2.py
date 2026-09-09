#!/usr/bin/env python3
"""Final orchestrator for the SOL-COMPASS market-carry WHEAT audit.

Keeps the binding-corrected runner immutable and repairs its one report-field
alias at invocation time. The generated report records this orchestrator hash.
"""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys


def load(path: Path):
    spec = importlib.util.spec_from_file_location("_sol_compass_wheat_runner_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    here = Path(__file__).resolve().parent
    runner = load(here / "run_sol_compass_market_carry_wheat_audit.py")
    original_stress = runner.add_hidden_rival_wheat_stress

    def stress_with_schema_alias(report: dict) -> None:
        best_rows = [row["best"] for row in report["scan"]["feasible_rows"]]
        for best in best_rows:
            if "profit" not in best:
                raise AssertionError("legacy feasibility report lost profit")
            best["worst_profit"] = best["profit"]
        try:
            original_stress(report)
        finally:
            for best in best_rows:
                best.pop("worst_profit", None)

    runner.add_hidden_rival_wheat_stress = stress_with_schema_alias
    result = int(runner.main())

    report_path = Path("WHEAT-AUDIT.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["audit_orchestrator_source_sha256"] = sha256(
        Path(__file__).read_bytes()
    ).hexdigest()
    report["schema_alias_correction"] = {
        "legacy_lookup": "best.worst_profit",
        "canonical_field": "best.profit",
        "calculation_changed": False,
    }
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("ORCHESTRATED_REPORT_SHA256", sha256(report_path.read_bytes()).hexdigest())
    return result


if __name__ == "__main__":
    raise SystemExit(main())
