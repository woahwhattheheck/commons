#!/usr/bin/env python3
"""Resume the frozen ROADEF lanes on three exact set-A rank-1 gaps."""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any

CASES = {
    "setA-04": {
        "input_sha256": {
            "net": "fbab36e356e73d8660f2a1a1aa3c110a3037938d834583d46707722b767c1559",
            "tm": "eae88eb99c495a5a4fa6f42717867169f2dbd12babb51520a0a26aa40be4be84",
            "scenario": "2a1b2744591d2707b2fb0ed7844a07ec2f5a61f6790df3ae0b60e392c950ad7e",
        },
        "incumbent_sha256": "600d4deee27022cb0f80e13e6336a9e6e233203890c6ca1a8311575980a41448",
        "rank1": {"t": 1, "from": 43, "to": 12, "sat": "0.587276"},
        "reference_mlu": "0.581237",
    },
    "setA-14": {
        "input_sha256": {
            "net": "779364ffbae366e1943dcf913f61ce8cc0928fcd52c158660b4eb7c68b1446cb",
            "tm": "244b41ce8d5a1cf19e7a42c1b86a0ef4de18a173ccfa24a61a602c3200032d28",
            "scenario": "e891294997f9580cd976b164faaeb1e182f76338d727a5eb7dbb5f0aba32505a",
        },
        "incumbent_sha256": "ba77a167bd449cf98a1af0ebbdcc074970d368ee27ae2447534889f6358cbdce",
        "rank1": {"t": 1, "from": 215, "to": 122, "sat": "0.533147"},
        "reference_mlu": "0.517621",
    },
    "setA-16": {
        "input_sha256": {
            "net": "341c874ba43a464f1140944fbde8b0b22afc70557acb9a1ed37c13116c748268",
            "tm": "db98d522634230e15337dc81ddca15a9922e1f505056f8c696db9b6cd6e00d3f",
            "scenario": "a992e5ddc30bdcdc33a2f64737abfd0f20231f272419a038e76582b49db7b7f0",
        },
        "incumbent_sha256": "f6e917ddb2fec5b5ecf2063c2200126e85184a82e459460f4351c3c16d30d2a8",
        "rank1": {"t": 1, "from": 131, "to": 228, "sat": "0.079918"},
        "reference_mlu": "0.044262",
    },
}

LANES = ("candidate", "sedge", "flora")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, default=str, sort_keys=True) + "\n",
                    encoding="utf-8")


def load_comparator(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("rank1_compare_checker", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def vector(document: dict[str, Any]) -> list[Decimal]:
    if document.get("valid") is not True:
        raise ValueError("checker result is not valid")
    values = [Decimal(str(row["sat"])) for row in document["saturations"]]
    if any(not value.is_finite() or value < 0 for value in values):
        raise ValueError("invalid saturation")
    return sorted(values, reverse=True)


def compare(left: list[Decimal], right: list[Decimal]) -> dict[str, Any]:
    if len(left) != len(right):
        raise ValueError(f"vector lengths differ: {len(left)} != {len(right)}")
    changed = next((i for i, pair in enumerate(zip(left, right)) if pair[0] != pair[1]), None)
    if changed is None:
        return {"winner": "tie", "first_changed_rank": None}
    return {
        "winner": "left" if left[changed] < right[changed] else "right",
        "first_changed_rank": changed + 1,
        "left_at_first_change": str(left[changed]),
        "right_at_first_change": str(right[changed]),
    }


def route_map(path: Path) -> dict[tuple[int, int], tuple[int, ...]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    rows = document.get("srpaths")
    if not isinstance(rows, list):
        raise ValueError(f"{path}: missing srpaths")
    result: dict[tuple[int, int], tuple[int, ...]] = {}
    for row in rows:
        key = (int(row["d"]), int(row["t"]))
        if key in result:
            raise ValueError(f"{path}: duplicate route {key}")
        waypoints = tuple(int(value) for value in row.get("w", []))
        if waypoints:
            result[key] = waypoints
    return result


def changed_routes(before: Path, after: Path) -> list[dict[str, Any]]:
    old, new = route_map(before), route_map(after)
    changes = []
    for demand, slot in sorted(set(old) | set(new)):
        left, right = old.get((demand, slot), ()), new.get((demand, slot), ())
        if left != right:
            changes.append({"d": demand, "t": slot, "before": list(left), "after": list(right)})
    return changes


def run_process(command: list[str], *, env: dict[str, str] | None, stdout: Path,
                stderr: Path, timeout: float) -> tuple[int | None, float, bool]:
    started = time.monotonic()
    try:
        with stdout.open("wb") as out, stderr.open("wb") as err:
            process = subprocess.run(command, env=env, stdout=out, stderr=err,
                                     timeout=timeout, check=False)
        return process.returncode, time.monotonic() - started, False
    except subprocess.TimeoutExpired:
        return None, time.monotonic() - started, True


def check_solution(checker: Path, paths: tuple[Path, Path, Path], solution: Path,
                   out: Path) -> dict[str, Any]:
    reports: dict[str, Any] = {}
    for places in (6, 12):
        report = out / f"checker-{places}.json"
        error = out / f"checker-{places}.stderr"
        command = [str(checker), "--net", str(paths[0]), "--tm", str(paths[1]),
                   "--scenario", str(paths[2]), "--srpaths", str(solution),
                   "--max-decimal-places", str(places)]
        code, elapsed, timed_out = run_process(command, env=None, stdout=report,
                                               stderr=error, timeout=45)
        document = read_json(report) if report.is_file() and report.stat().st_size else None
        reports[str(places)] = {
            "command": command,
            "returncode": code,
            "elapsed_seconds": elapsed,
            "timeout": timed_out,
            "stdout_sha256": sha256(report) if report.is_file() else None,
            "stderr_sha256": sha256(error) if error.is_file() else None,
            "valid": document.get("valid") if isinstance(document, dict) else None,
        }
        if code != 0 or not isinstance(document, dict) or document.get("valid") is not True:
            raise RuntimeError(f"official checker failed for {solution} at {places}dp")
    six = read_json(out / "checker-6.json")
    twelve = read_json(out / "checker-12.json")
    if len(six["saturations"]) != len(twelve["saturations"]):
        raise ValueError("six/twelve checker lengths differ")
    return {"runs": reports, "six": six, "twelve": twelve}


def exact_reference(path: Path, label: str) -> list[Decimal]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = csv.reader(stream)
        header = next(rows)
        if header[:2] != ["Instance", "Best team"]:
            raise ValueError("unexpected sprint header")
        for row in rows:
            if row and row[0] == label:
                values = [Decimal(text) for text in row[2:]]
                if any(not value.is_finite() or value < 0 for value in values):
                    raise ValueError("invalid sprint value")
                return values
    raise KeyError(label)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--official", type=Path, required=True)
    parser.add_argument("--incumbents", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--comparator", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=60)
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("--seconds must be positive")

    context, official = args.context.resolve(), args.official.resolve()
    incumbents, output = args.incumbents.resolve(), args.output.resolve()
    reference, comparator_path = args.reference.resolve(), args.comparator.resolve()
    output.mkdir(parents=True, exist_ok=False)
    load_comparator(comparator_path)

    binary_hashes = {}
    for lane in (*LANES, "checker"):
        path = context / "bin" / lane
        if not path.is_file():
            raise FileNotFoundError(path)
        binary_hashes[lane] = sha256(path)

    report: dict[str, Any] = {
        "schema": "roadef.a-rank1.resumed-lanes.v1",
        "scope": "three exact public set-A incumbents; no set-wide rerun or submission",
        "seconds_per_lane": args.seconds,
        "binary_sha256": binary_hashes,
        "comparator_sha256": sha256(comparator_path),
        "reference_sha256": sha256(reference),
        "cases": [],
    }
    write_json(output / "RESULTS.partial.json", report)

    for label, expected in CASES.items():
        paths = (
            official / "setA" / f"{label}-net.json",
            official / "setA" / f"{label}-tm.json",
            official / "setA" / f"{label}-scenario.json",
        )
        for name, path in zip(("net", "tm", "scenario"), paths):
            if sha256(path) != expected["input_sha256"][name]:
                raise ValueError(f"{label}: {name} hash mismatch")
        incumbent = incumbents / label / "solution.json"
        if sha256(incumbent) != expected["incumbent_sha256"]:
            raise ValueError(f"{label}: incumbent hash mismatch")

        case_out = output / label
        case_out.mkdir()
        baseline_out = case_out / "incumbent"
        baseline_out.mkdir()
        baseline_checks = check_solution(context / "bin" / "checker", paths, incumbent,
                                         baseline_out)
        baseline_vector = vector(baseline_checks["six"])
        top_row = max(baseline_checks["six"]["saturations"],
                      key=lambda row: Decimal(str(row["sat"])))
        advertised = expected["rank1"]
        observed = {"t": int(top_row["t"]), "from": int(top_row["from"]),
                    "to": int(top_row["to"]), "sat": str(top_row["sat"])}
        if observed != advertised:
            raise ValueError(f"{label}: advertised rank1 mismatch {observed} != {advertised}")
        reference_vector = exact_reference(reference, label)
        if len(reference_vector) != len(baseline_vector):
            raise ValueError(f"{label}: reference length mismatch")
        baseline_vs_reference = compare(baseline_vector, reference_vector)

        case_record: dict[str, Any] = {
            "instance": label,
            "input_sha256": expected["input_sha256"],
            "incumbent_sha256": expected["incumbent_sha256"],
            "rank1_coordinate": observed,
            "reference_mlu": expected["reference_mlu"],
            "incumbent_mlu": str(baseline_vector[0]),
            "incumbent_total_cost": baseline_checks["six"].get("total_cost"),
            "incumbent_vs_reference": baseline_vs_reference,
            "vector_length": len(baseline_vector),
            "lanes": [],
        }

        best_name, best_vector, best_solution = "incumbent", baseline_vector, incumbent
        for lane in LANES:
            lane_out = case_out / lane
            lane_out.mkdir()
            solution = lane_out / "solution.json"
            stats = lane_out / "statistics.json"
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith(("SEDGE_", "FLEET_", "CLOUD_INITIAL_SOLUTION"))}
            env.update({
                "SEDGE_SECONDS": str(args.seconds),
                "SEDGE_STATS": str(stats),
                "CLOUD_INITIAL_SOLUTION": str(incumbent),
                "FLEET_DIRECTED": "1",
                "FLEET_JOINT": "1",
                "FLEET_WAYPOINT_LIMIT": "0",
                "OMP_NUM_THREADS": "1",
            })
            command = [str(context / "bin" / lane), str(paths[0]), str(paths[1]),
                       str(paths[2]), str(solution)]
            code, elapsed, timed_out = run_process(
                command, env=env, stdout=lane_out / "solver.stdout",
                stderr=lane_out / "solver.stderr", timeout=args.seconds + 25)
            lane_record: dict[str, Any] = {
                "lane": lane, "command": command, "returncode": code,
                "elapsed_seconds": elapsed, "timeout": timed_out,
                "solution_exists": solution.is_file(),
                "statistics_exists": stats.is_file(),
            }
            if code != 0 or not solution.is_file():
                lane_record["status"] = "solver_failed"
                case_record["lanes"].append(lane_record)
                write_json(output / "RESULTS.partial.json", report)
                continue
            checks = check_solution(context / "bin" / "checker", paths, solution, lane_out)
            lane_vector = vector(checks["six"])
            lane_record.update({
                "status": "valid",
                "solution_sha256": sha256(solution),
                "statistics_sha256": sha256(stats) if stats.is_file() else None,
                "checker_6_sha256": sha256(lane_out / "checker-6.json"),
                "checker_12_sha256": sha256(lane_out / "checker-12.json"),
                "mlu": str(lane_vector[0]),
                "total_cost": checks["six"].get("total_cost"),
                "versus_incumbent": compare(lane_vector, baseline_vector),
                "versus_reference": compare(lane_vector, reference_vector),
                "changed_routes": changed_routes(incumbent, solution),
                "checker_runs": checks["runs"],
            })
            if lane_vector < best_vector:
                best_name, best_vector, best_solution = lane, lane_vector, solution
            case_record["lanes"].append(lane_record)
            print(f"{label} {lane}: {lane_record['versus_incumbent']['winner']} "
                  f"mlu={lane_record['mlu']} changes={len(lane_record['changed_routes'])}",
                  flush=True)

        case_record["best"] = {
            "name": best_name,
            "mlu": str(best_vector[0]),
            "solution_sha256": sha256(best_solution),
            "versus_incumbent": compare(best_vector, baseline_vector),
            "versus_reference": compare(best_vector, reference_vector),
            "changed_routes": changed_routes(incumbent, best_solution),
        }
        report["cases"].append(case_record)
        write_json(output / "RESULTS.partial.json", report)

    report["summary"] = {
        "cases": len(report["cases"]),
        "best_lane_counts": {name: sum(case["best"]["name"] == name for case in report["cases"])
                             for name in ("incumbent", *LANES)},
        "improved_cases": sum(case["best"]["versus_incumbent"]["winner"] == "left"
                              for case in report["cases"]),
        "reference_beaten_cases": sum(case["best"]["versus_reference"]["winner"] == "left"
                                     for case in report["cases"]),
    }
    write_json(output / "RESULTS.json", report)
    (output / "RESULTS.partial.json").unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
