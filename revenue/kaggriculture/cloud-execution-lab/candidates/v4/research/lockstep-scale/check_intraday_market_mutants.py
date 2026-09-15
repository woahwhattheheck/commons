# SPDX-License-Identifier: Apache-2.0
"""Run green controls first; require assertion rejection of every semantic fault.

A crashed or missing runner, import error, timeout, or identity failure is NOT a
successful behavioral kill. Both Python normal and optimized modes are exercised.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

MUTANTS = (
    "allow_hinge_buys", "forbid_negative_inventory", "quote_prebuy_inventory",
    "disable_buy_capacity", "cap_hand_inventory", "retain_eod_overflow",
    "admit_floor_sales", "town_before_market", "cap_pickup_quantity",
)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--runtime-root", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args(argv)
    here = Path(__file__).resolve().parent
    checker = here / "check_intraday_market_contract.py"
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    all_ok = True
    for optimized in (False, True):
        mode = "optimized" if optimized else "normal"
        for mutation in (None, *MUTANTS):
            label = mutation or "green"
            target = output / f"{mode}-{label}.json"
            # A failed child must never inherit a prior successful/failed receipt.
            target.unlink(missing_ok=True)
            cmd = [sys.executable, *(["-O"] if optimized else []), str(checker),
                   "--runtime-root", str(args.runtime_root.resolve()), "--output", str(target)]
            if mutation:
                cmd.extend(["--mutation", mutation])
            cp = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            (output / f"{mode}-{label}.log").write_text(cp.stdout+cp.stderr)
            try:
                result = json.loads(target.read_text())
            except (OSError, ValueError):
                result = {}
            failures, errors = result.get("failures", []), result.get("errors", [])
            identity_ok = result.get("optimized") is optimized and result.get("tests_run") == 18
            if mutation is None:
                ok = cp.returncode == 0 and result.get("passed") is True and not errors and not failures and identity_ok
            else:
                ok = (cp.returncode == 1 and result.get("passed") is False and
                      bool(failures) and not errors and identity_ok and
                      all("AssertionError" in f["traceback"] for f in failures) and
                      isinstance(result.get("mutation"), dict) and result["mutation"].get("name") == mutation)
            row = {"mode": mode, "mutation": mutation, "returncode": cp.returncode,
                   "ok": ok, "failures": len(failures), "errors": len(errors),
                   "tests_run": result.get("tests_run"),
                   "engine_calls": result.get("engine_calls"),
                   "receipt": target.name,
                   "receipt_sha256": hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None}
            rows.append(row)
            print(json.dumps(row))
            all_ok = all_ok and ok
            # Never count faults when the same mode's unmodified control failed.
            if mutation is None and not ok:
                break
    summary = {"schema": "titan.intraday-market-negative-controls.v1", "passed": all_ok,
               "checker_sha256": hashlib.sha256(checker.read_bytes()).hexdigest(),
               "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "baseline_engine_unmodified": True, "mutants_are_in_memory_scratch_faults": True,
               "full_games": 0, "promotion_claim": False, "rows": rows}
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
