#!/usr/bin/env python3
"""Record deterministic synthetic observations from a chosen calculator source.

This runner records outcomes, not correctness verdicts; test_coverage_contract.py
contains independent expectations. Only load trusted calculator source.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import inspect
import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path


HEADER = ["deployment_id", "service", "commit_at", "deployed_at",
          "intervention_required", "recovered_at", "unplanned_rework", "notes"]
ROW = ["SYN-1", "synthetic-service", "2026-09-01T09:00:00Z",
       "2026-09-01T12:00:00Z", "false", "", "false", "SYNTHETIC only"]


def run(calculator_path: Path) -> dict:
    source = calculator_path.read_bytes()
    spec = importlib.util.spec_from_file_location("coverage_rehearsal_target", calculator_path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load calculator source")
    calc = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = calc
    spec.loader.exec_module(calc)
    time = lambda s: calc._required_time(s, "synthetic time")
    start = time("2026-09-01T00:00:00Z")
    end = time("2026-09-15T00:00:00Z")
    row = calc.Deployment("SYN-1", "synthetic-service", time(ROW[2]), time(ROW[3]),
                          False, None, False, "SYNTHETIC only")
    unknown = replace(row, deployment_id="SYN-UNKNOWN", intervention_required=None)
    known = replace(row, deployment_id="SYN-FAILED", intervention_required=True,
                    recovered_at=time("2026-09-01T15:00:00Z"))
    observations = {}

    def observe(name, fn):
        try:
            observations[name] = {"outcome": "RETURNED", "value": fn()}
        except Exception as exc:
            observations[name] = {"outcome": "RAISED", "exception": type(exc).__name__,
                                  "message": str(exc)}

    def report(rows, **kwargs):
        return calc.calculate(rows, window_start=start, window_end=end, **kwargs)

    recovery = lambda rows: report(rows)["metrics"]["failed_deployment_recovery_time"]
    observe("known_recovery_plus_unknown_eligibility", lambda: recovery([known, unknown]))
    observe("unknown_eligibility_only", lambda: recovery([unknown]))
    observe("direct_negative_lead_time", lambda: report([
        replace(row, commit_at=time("2026-09-01T13:00:00Z"))
    ])["metrics"]["change_lead_time"])
    observe("direct_integer_boolean", lambda: report([
        replace(row, intervention_required=1)
    ])["metrics"]["change_fail_rate"])
    observe("direct_duplicate_deployment", lambda: report([row, row])["scope"])

    with tempfile.TemporaryDirectory(prefix="uiowa64-rehearsal-") as tmp:
        path = Path(tmp) / "synthetic.csv"
        def csv_case(headers, values):
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(headers)
                writer.writerow(values)
            return len(calc.load_deployments(path))
        observe("short_csv_row", lambda: csv_case(HEADER, ROW[:-1]))
        observe("extra_csv_cell", lambda: csv_case(HEADER, ROW + ["unheaded extra"]))
        observe("duplicate_csv_header", lambda: csv_case(HEADER + ["notes"], ROW + ["overwritten"]))
        observe("blank_notes", lambda: csv_case(HEADER, ROW[:-1] + [""]))

    late = replace(known, deployment_id="SYN-LATE",
                   recovered_at=time("2026-09-16T15:00:00Z"))
    observe("late_recovery_retrospective", lambda: recovery([known, late]))
    if "recovery_observed_through" in inspect.signature(calc.calculate).parameters:
        observe("late_recovery_explicit_cutoff", lambda: report(
            [known, late], recovery_observed_through=end
        )["metrics"]["failed_deployment_recovery_time"])
    else:
        observations["late_recovery_explicit_cutoff"] = {"outcome": "UNSUPPORTED"}
    return {
        "authority": "SYNTHETIC_REHEARSAL_NOT_UNIVERSITY_FINDINGS",
        "source_git_blob_sha1": hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest(),
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "observations": observations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calculator", type=Path, default=Path(__file__).with_name("calculator.py"))
    args = parser.parse_args()
    print(json.dumps(run(args.calculator), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
