# SPDX-License-Identifier: Apache-2.0
"""Exact-current D1 public-supply SELL-order screen.

Build exact V3.1 from its frozen source base + immutable canonical archive, then compare:

  control: exact V3.1 vs exact V3.1
  D1:      D1 row-order factor vs exact V3.1

on seeds 2611151001..1008 from both candidate seats.  The paired control lets this
screen report Delta-own, Delta-rival and Delta-margin cell by cell, implementing the D3
externality rule directly.  This is offline official-interpreter evidence only; it is
never a promotion or hosted-Kaggle action.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile


V31_BASE_COMMIT = "508b342fc46fa91e3d7cdc3f0b7e44934a187c14"
CANONICAL_CARRIER_COMMIT = "c580f7805cc7468094c0e880f4923133d45d70d0"
CANONICAL_SHA256 = "5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1"
ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
AGENT_RNG_SEED = 20260907
SEEDS = tuple(range(2611151001, 2611151009))

LAB_REL = Path("revenue/kaggriculture/cloud-execution-lab")
V3_REL = LAB_REL / "candidates" / "v3"
EXPERIMENT_REL = V3_REL / "experiments" / "d1_public_supply_order"
CANONICAL_REL = LAB_REL / "exports" / "historical" / f"titan-{CANONICAL_SHA256}.tar.gz"
EVALUATOR_REL = LAB_REL / "reference" / "evaluator" / "evaluate.py"
ENGINE_DIR_REL = LAB_REL / "reference" / "engine"

D1_APPEND = r'''

# --- D1 public rival-supply SELL-order experiment -----------------------------
# Evaluation-only wrapper installed after the exact R04 output.  It changes only
# leading SELL row positions and leaves quantity, timing, debt and non-SELL rows intact.
_D1_PARENT_INSTALL = install


def install(host=None, horizon=None, opening=None, row_order=None, evening_flush=None,
            sale_fertilizer=None, cattle_early=None):
    parent = _D1_PARENT_INSTALL(host, horizon, opening, row_order, evening_flush,
                                sale_fertilizer, cattle_early)
    from d1_public_supply_order import apply_public_supply_order, REPORT as _D1_REPORT

    def d1_agent(observation, configuration=None):
        action = parent(observation, configuration)
        return apply_public_supply_order(observation, action, configuration, enabled=True)

    d1_agent.telemetry = _D1_REPORT
    return d1_agent
'''


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_sha256(value) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def run(args, *, cwd: Path) -> None:
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run([str(a) for a in args], cwd=cwd, check=True)


def require_commit(repo: Path, commit: str) -> None:
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(f"required Git commit is not locally available: {commit}")


def safe_extract_bytes(blob: bytes, destination: Path, *, mode: str) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with tarfile.open(fileobj=io.BytesIO(blob), mode=mode) as archive:
        for member in archive.getmembers():
            if member.issym() or member.islnk():
                raise ValueError(f"archive links are not accepted: {member.name}")
            target = (destination / member.name).resolve()
            if target != root and root not in target.parents:
                raise ValueError(f"archive member escapes destination: {member.name}")
        archive.extractall(destination)


def materialize_v31_source(repo: Path, destination: Path) -> Path:
    require_commit(repo, V31_BASE_COMMIT)
    archived = subprocess.check_output(
        ["git", "archive", "--format=tar", V31_BASE_COMMIT, V3_REL.as_posix()],
        cwd=repo,
    )
    safe_extract_bytes(archived, destination, mode="r:")
    v3 = destination / V3_REL
    if not (v3 / "make_submission.py").is_file():
        raise RuntimeError("frozen V3.1 source tree is incomplete")
    return v3


def materialize_canonical(repo: Path, destination: Path) -> Path:
    require_commit(repo, CANONICAL_CARRIER_COMMIT)
    blob = subprocess.check_output(
        ["git", "show", f"{CANONICAL_CARRIER_COMMIT}:{CANONICAL_REL.as_posix()}"],
        cwd=repo,
    )
    digest = sha256_bytes(blob)
    if digest != CANONICAL_SHA256:
        raise RuntimeError(f"canonical digest mismatch: {digest} != {CANONICAL_SHA256}")
    destination.write_bytes(blob)
    return destination


def build_v31(repo: Path, v3: Path, canonical: Path, output: Path) -> None:
    run([sys.executable, "-B", v3 / "make_submission.py", v3, canonical, output, "8"], cwd=repo)
    if not output.is_file():
        raise RuntimeError("V3.1 builder produced no archive")


def extract_archive(archive: Path, destination: Path) -> None:
    safe_extract_bytes(archive.read_bytes(), destination, mode="r:gz")


def read_config(package: Path) -> dict:
    value = json.loads((package / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError("TITAN-CONFIG.json is not an object")
    return value


def assert_live_v31_config(config: dict) -> None:
    expected = {
        "r04_sale_window": True,
        "r04_sale_horizon": 8,
        "r04_open_roundtrip": 0,
        "r04_row_order": True,
        "r04_evening_flush": True,
        "r04_sale_fertilizer": True,
        "r04_cattle_early": True,
    }
    for key, wanted in expected.items():
        got = config.get(key)
        if got != wanted or type(got) is not type(wanted):
            raise AssertionError(f"live V3.1 config drift: {key}={got!r}, expected {wanted!r}")


def package_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def make_candidate(repo: Path, control: Path, candidate: Path) -> dict:
    shutil.copytree(control, candidate)
    source = repo / EXPERIMENT_REL / "d1_public_supply_order.py"
    if not source.is_file():
        raise RuntimeError(f"D1 source is missing: {source}")
    shutil.copy2(source, candidate / source.name)
    router = candidate / "r04_full_router.py"
    if not router.is_file():
        raise RuntimeError("materialized V3.1 package has no r04_full_router.py")
    original = router.read_text(encoding="utf-8")
    if "_D1_PARENT_INSTALL" in original:
        raise AssertionError("candidate router unexpectedly already contains D1")
    router.write_text(original + D1_APPEND, encoding="utf-8")

    control_hashes = package_hashes(control)
    candidate_hashes = package_hashes(candidate)
    for path, digest in control_hashes.items():
        if path == "r04_full_router.py":
            continue
        if candidate_hashes.get(path) != digest:
            raise AssertionError(f"candidate changed baseline package file unexpectedly: {path}")
    if set(candidate_hashes) != set(control_hashes) | {"d1_public_supply_order.py"}:
        raise AssertionError("candidate file set differs beyond D1 module")
    return {
        "control_router_sha256": control_hashes["r04_full_router.py"],
        "candidate_router_sha256": candidate_hashes["r04_full_router.py"],
        "d1_source_sha256": candidate_hashes["d1_public_supply_order.py"],
    }


def expected_fingerprint(entry: Path) -> dict:
    return {"entry": entry.name, "callable": "agent", "sha256": sha256_file(entry)}


def validate_evaluator_report(
    report: dict,
    label: str,
    candidate_main: Path,
    opponent_main: Path,
    repo: Path,
) -> None:
    if not isinstance(report, dict):
        raise AssertionError("evaluator report is not an object")
    schema_version = report.get("schema_version")
    if type(schema_version) is not int or schema_version != 1:
        raise AssertionError(f"evaluator schema drift: {schema_version!r}")
    if report.get("engine_ref") != ENGINE_REF:
        raise AssertionError(f"evaluator engine ref drift: {report.get('engine_ref')!r}")
    evaluator_sha = report.get("evaluator_sha256")
    expected_evaluator_sha = sha256_file(repo / EVALUATOR_REL)
    if evaluator_sha != expected_evaluator_sha:
        raise AssertionError(
            f"evaluator fingerprint drift: {evaluator_sha!r} != {expected_evaluator_sha!r}"
        )

    seeds = report.get("seeds")
    if not isinstance(seeds, list) or len(seeds) != len(SEEDS):
        raise AssertionError(f"evaluator seed metadata shape drift: {seeds!r}")
    if any(type(seed) is not int for seed in seeds) or tuple(seeds) != SEEDS:
        raise AssertionError(f"evaluator seed metadata drift: {seeds!r}")
    rng_seed = report.get("agent_rng_seed")
    if type(rng_seed) is not int or rng_seed != AGENT_RNG_SEED:
        raise AssertionError(f"evaluator RNG seed drift: {rng_seed!r}")

    candidate = report.get("candidate")
    expected_candidate = expected_fingerprint(candidate_main)
    if candidate != expected_candidate:
        raise AssertionError(
            f"candidate fingerprint drift: {candidate!r} != {expected_candidate!r}"
        )
    opponents = report.get("opponents")
    expected_opponent = expected_fingerprint(opponent_main)
    if not isinstance(opponents, dict) or set(opponents) != {label}:
        raise AssertionError(f"opponent fingerprint membership drift: {opponents!r}")
    if opponents[label] != expected_opponent:
        raise AssertionError(
            f"opponent fingerprint drift: {opponents[label]!r} != {expected_opponent!r}"
        )

    reproducibility = report.get("reproducibility")
    if not isinstance(reproducibility, dict):
        raise AssertionError("evaluator report lacks replay determinism receipt")
    if reproducibility.get("checked") is not True:
        raise AssertionError("evaluator replay determinism check was not executed")
    if reproducibility.get("same_trace_and_scores") is not True:
        raise AssertionError("evaluator first-cell replay check failed")
    original_trace = reproducibility.get("original_trace")
    replay_trace = reproducibility.get("replay_trace")
    if not is_sha256(original_trace) or not is_sha256(replay_trace):
        raise AssertionError("evaluator replay trace digest is malformed")
    if original_trace != replay_trace:
        raise AssertionError("evaluator replay trace digest changed")


def run_evaluator(
    repo: Path,
    candidate_main: Path,
    opponent_main: Path,
    label: str,
    output: Path,
) -> dict:
    args = [
        sys.executable,
        "-B",
        repo / EVALUATOR_REL,
        "--engine-dir",
        repo / ENGINE_DIR_REL,
        "--candidate",
        candidate_main,
        "--opponent",
        f"{label}={opponent_main}",
        "--seeds",
        ",".join(map(str, SEEDS)),
        "--rng-seed",
        str(AGENT_RNG_SEED),
        "--game-timeout",
        "180",
        "--recheck-first",
        "--output",
        output,
    ]
    run(args, cwd=repo)
    report = json.loads(output.read_text(encoding="utf-8"))
    validate_evaluator_report(report, label, candidate_main, opponent_main, repo)
    return report


def exact_cells(report: dict, label: str) -> dict[tuple[int, int], dict]:
    games = report.get("games")
    if not isinstance(games, list):
        raise AssertionError("evaluator report has no games list")
    expected = {(seed, seat) for seed in SEEDS for seat in (0, 1)}
    result = {}
    for index, game in enumerate(games):
        if not isinstance(game, dict):
            raise AssertionError(f"game row {index} is not an object: {game!r}")
        if game.get("opponent") != label:
            raise AssertionError(f"unexpected opponent label: {game.get('opponent')!r}")
        seed = game.get("seed")
        seat = game.get("candidate_seat")
        if type(seed) is not int or type(seat) is not int:
            raise AssertionError(f"non-integer seed/seat in game row {index}: {(seed, seat)!r}")
        if seat not in (0, 1):
            raise AssertionError(f"invalid candidate seat in game row {index}: {seat!r}")
        key = (seed, seat)
        if key not in expected or key in result:
            raise AssertionError(f"unexpected/duplicate cell: {key}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise AssertionError(f"incomplete cell {key}: {game.get('failure')}")
        scores = game.get("scores")
        if not (isinstance(scores, list) and len(scores) == 2):
            raise AssertionError(f"invalid scores for {key}: {scores!r}")
        for score in scores:
            if type(score) not in (int, float) or not math.isfinite(score):
                raise AssertionError(f"non-finite/non-numeric score for {key}: {scores!r}")
        trace = game.get("trace_sha256")
        if not is_sha256(trace):
            raise AssertionError(f"invalid trace digest for {key}: {trace!r}")
        result[key] = game
    if set(result) != expected:
        raise AssertionError(f"missing cells: {sorted(expected - set(result))}")
    return result


def side_scores(game: dict) -> tuple[int | float, int | float]:
    seat = game["candidate_seat"]
    scores = game["scores"]
    return scores[seat], scores[1 - seat]


def summarize(control: dict[tuple[int, int], dict], candidate: dict[tuple[int, int], dict]) -> dict:
    rows = []
    for key in sorted(control):
        c0, r0 = side_scores(control[key])
        c1, r1 = side_scores(candidate[key])
        delta_own = c1 - c0
        delta_rival = r1 - r0
        delta_margin = delta_own - delta_rival
        rows.append({
            "seed": key[0],
            "candidate_seat": key[1],
            "control_scores": control[key]["scores"],
            "candidate_scores": candidate[key]["scores"],
            "delta_own": delta_own,
            "delta_rival": delta_rival,
            "delta_margin": delta_margin,
            "control_trace_sha256": control[key].get("trace_sha256"),
            "candidate_trace_sha256": candidate[key].get("trace_sha256"),
            "trace_changed": control[key].get("trace_sha256") != candidate[key].get("trace_sha256"),
        })
    margins = [row["delta_margin"] for row in rows]
    own = [row["delta_own"] for row in rows]
    rival = [row["delta_rival"] for row in rows]
    return {
        "scheduled": len(rows),
        "positive": sum(v > 0 for v in margins),
        "ties": sum(v == 0 for v in margins),
        "negative": sum(v < 0 for v in margins),
        "mean_delta_own": statistics.mean(own),
        "mean_delta_rival": statistics.mean(rival),
        "mean_delta_margin": statistics.mean(margins),
        "median_delta_margin": statistics.median(margins),
        "min_delta_margin": min(margins),
        "max_delta_margin": max(margins),
        "trace_changed_cells": sum(row["trace_changed"] for row in rows),
        "cells": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)

    require_commit(repo, V31_BASE_COMMIT)
    require_commit(repo, CANONICAL_CARRIER_COMMIT)

    with tempfile.TemporaryDirectory(prefix="titan-d1-") as temporary:
        work = Path(temporary)
        v3 = materialize_v31_source(repo, work / "source")
        canonical = materialize_canonical(repo, work / "canonical.tar.gz")
        built = work / "v31.tar.gz"
        build_v31(repo, v3, canonical, built)

        control_dir = work / "control"
        candidate_dir = work / "candidate"
        extract_archive(built, control_dir)
        config = read_config(control_dir)
        assert_live_v31_config(config)
        mutation = make_candidate(repo, control_dir, candidate_dir)
        if read_config(candidate_dir) != config:
            raise AssertionError("candidate config changed")

        control_raw = out / "control-v31-vs-v31.json"
        candidate_raw = out / "d1-vs-v31.json"
        control_report = run_evaluator(
            repo,
            control_dir / "main.py",
            control_dir / "main.py",
            "exact_v31_control",
            control_raw,
        )
        candidate_report = run_evaluator(
            repo,
            candidate_dir / "main.py",
            control_dir / "main.py",
            "exact_v31",
            candidate_raw,
        )
        control_cells = exact_cells(control_report, "exact_v31_control")
        candidate_cells = exact_cells(candidate_report, "exact_v31")
        summary = summarize(control_cells, candidate_cells)

        if summary["trace_changed_cells"] == 0:
            disposition = "NO_OBSERVED_TRACE_SIGNAL"
        elif summary["negative"] == 0 and summary["mean_delta_margin"] > 0:
            disposition = "D1_DIRECT_V31_SCREEN_POSITIVE"
        elif summary["mean_delta_margin"] > 0:
            disposition = "D1_DIRECT_V31_MIXED_POSITIVE_MEAN"
        else:
            disposition = "D1_DIRECT_V31_NOT_POSITIVE"

        receipt = {
            "schema": "titan-v31-d1-public-supply-order/v1",
            "truth_boundary": (
                "Exact offline official-interpreter direct-V3.1 paired externality screen. "
                "Standing rival public yield is only a supply-pressure heuristic, not hidden "
                "inventory/order knowledge or an exact future-price forecast. No promotion authority."
            ),
            "source": {
                "v31_base_commit": V31_BASE_COMMIT,
                "canonical_carrier_commit": CANONICAL_CARRIER_COMMIT,
                "canonical_sha256": sha256_file(canonical),
                "built_v31_sha256": sha256_file(built),
                "engine_ref": ENGINE_REF,
                "evaluator_sha256": sha256_file(repo / EVALUATOR_REL),
                **mutation,
            },
            "factor": {
                "mutation": "stable-partition existing leading SELL rows: visible-rival-yield products first",
                "quantity_changes": 0,
                "cross_turn_sale_moves": 0,
                "hidden_rival_state_reads": 0,
                "custom_market_params": "fail_closed",
            },
            "panel": {
                "seeds": list(SEEDS),
                "seats": [0, 1],
                "paired_cells": 16,
                "agent_rng_seed": AGENT_RNG_SEED,
                "recheck_first": True,
            },
            "summary": summary,
            "disposition": disposition,
            "raw": {
                "control": control_raw.name,
                "control_sha256": sha256_file(control_raw),
                "candidate": candidate_raw.name,
                "candidate_sha256": sha256_file(candidate_raw),
            },
        }
        receipt_path = out / "D1-PAIRED-RECEIPT.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("D1_RESULT " + json.dumps({"disposition": disposition, **{k: v for k, v in summary.items() if k != "cells"}}, sort_keys=True))
        print("D1_RECEIPT", receipt_path, sha256_file(receipt_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
