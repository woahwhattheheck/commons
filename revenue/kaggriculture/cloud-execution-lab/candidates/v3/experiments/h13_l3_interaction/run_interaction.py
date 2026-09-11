# SPDX-License-Identifier: Apache-2.0
"""Exact H13 (R04 sale horizon 10) x L3 interaction screen.

This is an experiment harness, not a gameplay/default change.  It materializes the
reviewed L3 source commit and immutable canonical archive from Git history, builds two
submission archives whose TITAN-CONFIG.json differs only in r04_sale_horizon (8 vs 10),
and runs the repository's pinned official-interpreter evaluator on the frozen V3.1
8-seed x both-seat panel.

The candidate is horizon-10-on-L3.  The opponent is horizon-8-on-L3.  Therefore the
reported competitive margin isolates H13 inside the L3 late-reservation policy rather
than comparing either arm to a different policy family.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tarfile
import tempfile


L3_SOURCE_COMMIT = "d181d6ecf848f88885bc1cc348c456714b7360cd"
CANONICAL_CARRIER_COMMIT = "c580f7805cc7468094c0e880f4923133d45d70d0"
CANONICAL_SHA256 = "5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1"
ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
SEEDS = tuple(range(2611151001, 2611151009))

LAB_REL = Path("revenue/kaggriculture/cloud-execution-lab")
V3_REL = LAB_REL / "candidates" / "v3"
CANONICAL_REL = (
    LAB_REL
    / "exports"
    / "historical"
    / f"titan-{CANONICAL_SHA256}.tar.gz"
)
EVALUATOR_REL = LAB_REL / "reference" / "evaluator" / "evaluate.py"
ENGINE_DIR_REL = LAB_REL / "reference" / "engine"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, *, cwd: Path, capture: bool = False) -> subprocess.CompletedProcess:
    print("+", " ".join(map(str, args)), flush=True)
    return subprocess.run(
        [str(a) for a in args],
        cwd=cwd,
        check=True,
        text=True,
        capture_output=capture,
    )


def require_git_object(repo: Path, commit: str) -> None:
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=repo,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if completed.returncode:
        raise RuntimeError(
            f"required Git commit {commit} is unavailable; fetch the pinned PR refs first"
        )


def safe_extract_bytes(blob: bytes, destination: Path, *, mode: str) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with tarfile.open(fileobj=io.BytesIO(blob), mode=mode) as archive:
        for member in archive.getmembers():
            if member.issym() or member.islnk():
                raise ValueError(f"archive link is not allowed in experiment materialization: {member.name}")
            target = (destination / member.name).resolve()
            if target != root and root not in target.parents:
                raise ValueError(f"archive member escapes destination: {member.name}")
        archive.extractall(destination)


def materialize_l3_tree(repo: Path, destination: Path) -> Path:
    require_git_object(repo, L3_SOURCE_COMMIT)
    archived = subprocess.check_output(
        ["git", "archive", "--format=tar", L3_SOURCE_COMMIT, V3_REL.as_posix()],
        cwd=repo,
    )
    safe_extract_bytes(archived, destination, mode="r:")
    v3 = destination / V3_REL
    if not (v3 / "make_submission.py").is_file():
        raise RuntimeError("materialized L3 source tree is missing make_submission.py")
    return v3


def materialize_canonical(repo: Path, destination: Path) -> Path:
    require_git_object(repo, CANONICAL_CARRIER_COMMIT)
    blob = subprocess.check_output(
        ["git", "show", f"{CANONICAL_CARRIER_COMMIT}:{CANONICAL_REL.as_posix()}"],
        cwd=repo,
    )
    digest = sha256_bytes(blob)
    if digest != CANONICAL_SHA256:
        raise RuntimeError(f"canonical SHA mismatch: {digest} != {CANONICAL_SHA256}")
    destination.write_bytes(blob)
    return destination


def build_submission(repo: Path, v3: Path, canonical: Path, out: Path, horizon: int) -> None:
    run(
        [sys.executable, "-B", v3 / "make_submission.py", v3, canonical, out, str(horizon)],
        cwd=repo,
    )
    if not out.is_file():
        raise RuntimeError(f"builder did not create {out}")


def extract_package(path: Path, destination: Path) -> int:
    blob = path.read_bytes()
    safe_extract_bytes(blob, destination, mode="r:gz")
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as archive:
        return sum(member.isfile() for member in archive.getmembers())


def read_config(package: Path) -> dict:
    value = json.loads((package / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("TITAN-CONFIG.json must contain an object")
    return value


def assert_isolated_configs(h8: dict, h10: dict) -> None:
    expected = {
        "r04_sale_window": True,
        "r04_no_late_sale_advance": True,
        "r04_no_late_sale_advance_step": 648,
        "r04_row_order": True,
        "r04_evening_flush": True,
        "r04_sale_fertilizer": True,
        "r04_cattle_early": True,
        "r04_open_roundtrip": 0,
    }
    for name, cfg, horizon in (("h8", h8, 8), ("h10", h10, 10)):
        for key, value in expected.items():
            if cfg.get(key) != value or type(cfg.get(key)) is not type(value):
                raise AssertionError(f"{name} config {key}={cfg.get(key)!r}; expected {value!r}")
        if cfg.get("r04_sale_horizon") != horizon or type(cfg.get("r04_sale_horizon")) is not int:
            raise AssertionError(f"{name} horizon is not exact integer {horizon}")
    left, right = dict(h8), dict(h10)
    left.pop("r04_sale_horizon", None)
    right.pop("r04_sale_horizon", None)
    if left != right:
        changed = sorted(set(left) | set(right))
        changed = [key for key in changed if left.get(key) != right.get(key) or type(left.get(key)) is not type(right.get(key))]
        raise AssertionError(f"h8/h10 configs differ outside horizon: {changed}")


def run_evaluator(
    repo: Path,
    candidate: Path,
    opponent: Path,
    label: str,
    seeds: tuple[int, ...],
    output: Path,
    *,
    recheck_first: bool = False,
) -> dict:
    evaluator = repo / EVALUATOR_REL
    engine_dir = repo / ENGINE_DIR_REL
    args = [
        sys.executable,
        "-B",
        evaluator,
        "--engine-dir",
        engine_dir,
        "--candidate",
        candidate,
        "--opponent",
        f"{label}={opponent}",
        "--seeds",
        ",".join(map(str, seeds)),
        "--game-timeout",
        "180",
        "--output",
        output,
    ]
    if recheck_first:
        args.append("--recheck-first")
    run(args, cwd=repo)
    report = json.loads(output.read_text(encoding="utf-8"))
    if report.get("engine_ref") != ENGINE_REF:
        raise AssertionError(f"evaluator engine ref drift: {report.get('engine_ref')}")
    return report


def exact_cells(report: dict, label: str, seeds: tuple[int, ...]) -> list[dict]:
    games = report.get("games")
    if not isinstance(games, list):
        raise AssertionError("evaluator report has no games array")
    expected = {(seed, seat) for seed in seeds for seat in (0, 1)}
    seen: set[tuple[int, int]] = set()
    rows = []
    for game in games:
        if game.get("opponent") != label:
            raise AssertionError(f"unexpected opponent label {game.get('opponent')!r}")
        key = (game.get("seed"), game.get("candidate_seat"))
        if key not in expected or key in seen:
            raise AssertionError(f"unexpected/duplicate evaluator cell: {key}")
        seen.add(key)
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise AssertionError(f"incomplete evaluator cell {key}: {game.get('failure')}")
        scores = game.get("scores")
        if not (isinstance(scores, list) and len(scores) == 2):
            raise AssertionError(f"invalid scores for {key}: {scores!r}")
        rows.append(game)
    if seen != expected:
        raise AssertionError(f"missing evaluator cells: {sorted(expected - seen)}")
    return rows


def margin(game: dict) -> float:
    seat = int(game["candidate_seat"])
    scores = game["scores"]
    return float(scores[seat]) - float(scores[1 - seat])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Keep all package materialization outside the checkout.  The harness itself
    # is evidence-only and must leave the Git worktree byte-identical.
    with tempfile.TemporaryDirectory(prefix="titan-h13-l3-") as temporary:
        work = Path(temporary)
        l3_root = work / "l3-source"
        v3 = materialize_l3_tree(repo, l3_root)
        canonical = materialize_canonical(repo, work / "canonical.tar.gz")

        h8_tar, h10_tar = work / "h8-l3.tar.gz", work / "h10-l3.tar.gz"
        build_submission(repo, v3, canonical, h8_tar, 8)
        build_submission(repo, v3, canonical, h10_tar, 10)

        h8_dir, h10_dir = work / "h8", work / "h10"
        h8_files = extract_package(h8_tar, h8_dir)
        h10_files = extract_package(h10_tar, h10_dir)
        h8_config, h10_config = read_config(h8_dir), read_config(h10_dir)
        assert_isolated_configs(h8_config, h10_config)
        for package in (h8_dir, h10_dir):
            for required in ("main.py", "r04_full_router.py", "r04_no_late_sale_advance.py"):
                if not (package / required).is_file():
                    raise AssertionError(f"built package is missing {required}")

        # A small identity control catches a broken seat/candidate mapping before
        # spending the full interaction panel.  Identical deterministic packages
        # must tie on the same seed from either candidate seat.
        control_path = output_dir / "control-h8-vs-h8.json"
        control = run_evaluator(
            repo,
            h8_dir / "main.py",
            h8_dir / "main.py",
            "h8_identity",
            (SEEDS[0],),
            control_path,
        )
        control_rows = exact_cells(control, "h8_identity", (SEEDS[0],))
        control_margins = [margin(row) for row in control_rows]
        if control_margins != [0.0, 0.0]:
            raise AssertionError(f"h8 identity control is not two exact ties: {control_margins}")

        raw_path = output_dir / "h10-vs-h8-l3-raw.json"
        report = run_evaluator(
            repo,
            h10_dir / "main.py",
            h8_dir / "main.py",
            "h8_l3",
            SEEDS,
            raw_path,
            recheck_first=True,
        )
        rows = exact_cells(report, "h8_l3", SEEDS)
        replay = report.get("reproducibility") or {}
        if replay.get("same_trace_and_scores") is not True:
            raise AssertionError(f"first-cell reproducibility check failed: {replay}")

        margins = [margin(row) for row in rows]
        seat0 = [margin(row) for row in rows if row["candidate_seat"] == 0]
        seat1 = [margin(row) for row in rows if row["candidate_seat"] == 1]
        summary = {
            "scheduled": len(rows),
            "wins": sum(value > 0 for value in margins),
            "ties": sum(value == 0 for value in margins),
            "losses": sum(value < 0 for value in margins),
            "mean_margin": statistics.mean(margins),
            "median_margin": statistics.median(margins),
            "min_margin": min(margins),
            "max_margin": max(margins),
            "seat0_mean_margin": statistics.mean(seat0),
            "seat1_mean_margin": statistics.mean(seat1),
            "cells": [
                {
                    "seed": row["seed"],
                    "candidate_seat": row["candidate_seat"],
                    "scores": row["scores"],
                    "margin": margin(row),
                    "trace_sha256": row["trace_sha256"],
                }
                for row in sorted(rows, key=lambda value: (value["seed"], value["candidate_seat"]))
            ],
        }
        if summary["losses"] == 0 and summary["wins"] == len(rows):
            disposition = "interaction_positive_all_cells"
        elif summary["mean_margin"] > 0:
            disposition = "interaction_positive_mean_mixed_cells"
        else:
            disposition = "interaction_not_positive"

        receipt = {
            "schema": "titan-v31-h13-l3-interaction/v1",
            "truth_boundary": (
                "Exact offline official-interpreter isolation screen only; not a Kaggle hosted score, "
                "not a promotion decision, and not evidence that L3 itself should be enabled."
            ),
            "source": {
                "l3_source_commit": L3_SOURCE_COMMIT,
                "canonical_carrier_commit": CANONICAL_CARRIER_COMMIT,
                "canonical_path": CANONICAL_REL.as_posix(),
                "canonical_sha256": sha256_file(canonical),
                "engine_ref": ENGINE_REF,
                "evaluator_sha256": sha256_file(repo / EVALUATOR_REL),
            },
            "isolation": {
                "candidate": "horizon10-on-L3",
                "opponent": "horizon8-on-L3",
                "only_config_difference": {"r04_sale_horizon": [8, 10]},
                "l3_enabled": True,
                "l3_threshold": 648,
                "h8_archive": {
                    "sha256": sha256_file(h8_tar),
                    "bytes": h8_tar.stat().st_size,
                    "files": h8_files,
                },
                "h10_archive": {
                    "sha256": sha256_file(h10_tar),
                    "bytes": h10_tar.stat().st_size,
                    "files": h10_files,
                },
            },
            "panel": {
                "seeds": list(SEEDS),
                "seats": [0, 1],
                "games": len(rows),
                "identity_control_margins": control_margins,
                "recheck_first_same_trace_and_scores": True,
            },
            "summary": summary,
            "disposition": disposition,
            "raw_receipts": {
                "interaction": raw_path.name,
                "interaction_sha256": sha256_file(raw_path),
                "identity_control": control_path.name,
                "identity_control_sha256": sha256_file(control_path),
            },
        }
        receipt_path = output_dir / "interaction-receipt.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("H13_L3_RESULT " + json.dumps({"disposition": disposition, **summary}, sort_keys=True), flush=True)
        print("H13_L3_RECEIPT", receipt_path, sha256_file(receipt_path), flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
