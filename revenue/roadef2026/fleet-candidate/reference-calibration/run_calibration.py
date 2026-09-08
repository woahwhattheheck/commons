#!/usr/bin/env python3
"""Run the frozen ROADEF portfolio serially on set A and compare sprint vectors."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any

FROZEN_COMMIT = "6feb9c0566b8f203c5d1a2ffdfbf1cb6d11be055"
CANDIDATE_SHA256 = "758977095f8f34263bbcd9ed043ac4ab7943f04f65fae530c78ee64787c34f8f"
SPRINT_SHA256 = "b6218e41ac204e73c4688aa9e0e56825c1f5b864440675c4f7ffba27a75f45ca"
OFFICIAL_COMMIT = "d84d319a7fdb8de3b1866830d2eaa2937871e5ae"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, env: dict[str, str] | None = None,
        stdout: Path | None = None, stderr: Path | None = None,
        timeout: float | None = None) -> subprocess.CompletedProcess[bytes]:
    out_handle = stdout.open("wb") if stdout else subprocess.PIPE
    err_handle = stderr.open("wb") if stderr else subprocess.PIPE
    try:
        return subprocess.run(command, env=env, stdout=out_handle, stderr=err_handle,
                              timeout=timeout, check=False)
    finally:
        if stdout:
            out_handle.close()
        if stderr:
            err_handle.close()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def instance_paths(official: Path, label: str) -> tuple[Path, Path, Path]:
    root = official / "setA"
    return (root / f"{label}-net.json", root / f"{label}-tm.json",
            root / f"{label}-scenario.json")


def validate_inputs(official: Path) -> list[dict[str, Any]]:
    records = []
    for number in range(1, 21):
        label = f"setA-{number:02d}"
        paths = instance_paths(official, label)
        missing = [str(path) for path in paths if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"{label}: missing {missing}")
        records.append({
            "instance": label,
            "network": {"bytes": paths[0].stat().st_size, "sha256": sha256(paths[0])},
            "traffic": {"bytes": paths[1].stat().st_size, "sha256": sha256(paths[1])},
            "scenario": {"bytes": paths[2].stat().st_size, "sha256": sha256(paths[2])},
        })
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-root", type=Path, required=True,
                        help="fleet-candidate directory checked out at the frozen commit")
    parser.add_argument("--context", type=Path, required=True,
                        help="built verified context containing run.sh and bin/checker")
    parser.add_argument("--official-root", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--case-timeout", type=float, default=75.0)
    args = parser.parse_args()

    frozen = args.frozen_root.resolve()
    context = args.context.resolve()
    official = args.official_root.resolve()
    reference = args.reference.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    candidate = frozen / "main.cpp"
    if sha256(candidate) != CANDIDATE_SHA256:
        raise ValueError("frozen candidate source hash mismatch")
    if sha256(reference) != SPRINT_SHA256:
        raise ValueError("sprint reference hash mismatch")
    for path in (context / "run.sh", context / "bin" / "checker"):
        if not path.is_file():
            raise FileNotFoundError(path)

    inputs = validate_inputs(official)
    run_records: list[dict[str, Any]] = []
    started = time.time()
    for number in range(1, 21):
        label = f"setA-{number:02d}"
        network, traffic, scenario = instance_paths(official, label)
        case = output / label
        case.mkdir(parents=True, exist_ok=True)
        solution = case / "solution.json"
        receipt = case / "portfolio.json"
        artifacts = case / "artifacts"
        artifacts.mkdir(exist_ok=True)
        env = os.environ.copy()
        env.update({
            "PORTFOLIO_SECONDS": str(args.seconds),
            "PORTFOLIO_ARTIFACTS": str(artifacts),
            "PORTFOLIO_RECEIPT": str(receipt),
            "FLEET_DIRECTED": "1",
            "FLEET_JOINT": "1",
            "FLEET_WAYPOINT_LIMIT": "0",
            "OMP_NUM_THREADS": "1",
        })
        for key in ("SEDGE_MAX_ROUNDS", "SEDGE_STATS", "CLOUD_INITIAL_SOLUTION"):
            env.pop(key, None)
        t0 = time.monotonic()
        try:
            result = run([str(context / "run.sh"), str(network), str(traffic),
                          str(scenario), str(solution)], env=env,
                         stdout=case / "portfolio.stdout", stderr=case / "portfolio.stderr",
                         timeout=args.case_timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            result = None
            timed_out = True
        elapsed = time.monotonic() - t0
        if timed_out or result is None or result.returncode != 0 or not solution.is_file():
            record = {"instance": label, "elapsed_seconds": elapsed, "timeout": timed_out,
                      "returncode": None if result is None else result.returncode,
                      "solution_exists": solution.is_file(),
                      "receipt_exists": receipt.is_file()}
            run_records.append(record)
            (output / "RUN-PARTIAL.json").write_text(
                json.dumps({"runs": run_records}, indent=2) + "\n", encoding="utf-8")
            raise RuntimeError(f"{label}: portfolio failed: {record}")

        checker = case / "checker-6.json"
        check = run([str(context / "bin" / "checker"), "--net", str(network),
                     "--tm", str(traffic), "--scenario", str(scenario),
                     "--srpaths", str(solution), "--max-decimal-places", "6"],
                    stdout=checker, stderr=case / "checker.stderr", timeout=30)
        checker_doc = read_json(checker) if checker.is_file() else None
        if check.returncode != 0 or not isinstance(checker_doc, dict) or checker_doc.get("valid") is not True:
            raise RuntimeError(f"{label}: official checker failed with {check.returncode}")
        receipt_doc = read_json(receipt)
        saturations = checker_doc["saturations"]
        record = {
            "instance": label,
            "elapsed_seconds": round(elapsed, 6),
            "portfolio_returncode": result.returncode,
            "solution_sha256": sha256(solution),
            "checker_sha256": sha256(checker),
            "load_count": len(saturations),
            "mlu": str(max(float(row["sat"]) for row in saturations)),
            "total_cost_diagnostic": checker_doc.get("total_cost"),
            "portfolio_status": receipt_doc.get("status"),
            "selected_lane": receipt_doc.get("selected_lane"),
            "receipt_sha256": sha256(receipt),
        }
        run_records.append(record)
        (output / "RUN-PARTIAL.json").write_text(
            json.dumps({"runs": run_records}, indent=2) + "\n", encoding="utf-8")
        print(f"{label}: valid {record['mlu']} {elapsed:.2f}s", flush=True)

    comparison = output / "A-vs-sprint.json"
    compare = run([sys.executable, str(frozen / "compare_checker.py"), str(output),
                   str(reference), "--sprint", "--output", str(comparison)],
                  stdout=output / "compare.stdout", stderr=output / "compare.stderr", timeout=60)
    if compare.returncode != 0 or not comparison.is_file():
        raise RuntimeError("sprint comparison failed")
    comparison_doc = read_json(comparison)
    metadata = {
        "schema_version": 1,
        "purpose": "historical set-A calibration only; resource budgets are unequal",
        "submission_performed": False,
        "frozen_commit": FROZEN_COMMIT,
        "candidate_source_sha256": CANDIDATE_SHA256,
        "official_commit": OFFICIAL_COMMIT,
        "sprint_reference_sha256": SPRINT_SHA256,
        "seconds_per_case": args.seconds,
        "serial": True,
        "started_unix": started,
        "finished_unix": time.time(),
        "input_files": inputs,
        "context": {
            "candidate_binary_sha256": sha256(context / "bin" / "candidate"),
            "sedge_binary_sha256": sha256(context / "bin" / "sedge"),
            "flora_binary_sha256": sha256(context / "bin" / "flora"),
            "checker_binary_sha256": sha256(context / "bin" / "checker"),
        },
        "runs": run_records,
        "comparison_counts": comparison_doc.get("counts"),
        "invalid_candidate_count": comparison_doc.get("invalid_candidate_count"),
    }
    (output / "RUN.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# ROADEF set-A sprint-reference calibration",
        "",
        "This is a historical reference calibration, not a qualification ranking. The",
        "current 30-second serial portfolio runs and the published sprint best-team rows",
        "used unequal resource budgets. No submission or tuning occurred.",
        "",
        f"- Frozen source: `{FROZEN_COMMIT}` / `{CANDIDATE_SHA256}`",
        f"- Official data: `{OFFICIAL_COMMIT}`",
        f"- Reference CSV: `{SPRINT_SHA256}`",
        f"- Valid runs: {len(run_records)}/20",
        f"- Comparison counts: `{json.dumps(comparison_doc.get('counts'), sort_keys=True)}`",
        "",
        "| Instance | Result vs sprint | First rank | Candidate | Reference | MLU | Lane |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    by_instance = {row["instance"]: row for row in comparison_doc["instances"]}
    for record in run_records:
        row = by_instance[record["instance"]]
        lines.append(
            f"| {record['instance']} | {row['winner']} | {row.get('first_changed_rank') or '-'} | "
            f"{row.get('candidate_at_first_change', '-')} | {row.get('reference_at_first_change', '-')} | "
            f"{row.get('candidate_mlu', record['mlu'])} | {record.get('selected_lane') or '-'} |"
        )
    (output / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    shutil.copy2(reference, output / "REFERENCE.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
