#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Official-interpreter B11 current-a612 composition gate.

Materialize the exact shipped a612 package, evaluate it as the H8 control, then copy
that same package and add only the exact reviewed B11 classifier plus the tiny a612
composition entrypoint.  Pair both arms against exact shipped a612 and vendored Arlene.

This is evidence only: it does not edit overlay/**, TITAN-CONFIG, apply_v3, package
manifests, defaults, or Kaggle submissions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile

CANONICAL_HEAD = "a6120d0ea1bdb75eb0da2239220efce551f624a6"
CANONICAL_SHA256 = "5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1"
SHIPPED_ARCHIVE_SHA256 = "400ae640f3258b6a6ff19f9da99c66ef9c433e315febb1d72c75296cddeb277c"
ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
ARLENE_SHA256 = "1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4"
DONOR_BLOB = "94b270f36c4a27b3d958ac3420bbe5764ac327a1"
SEEDS = tuple(range(2611151001, 2611151005))

LAB_REL = Path("revenue/kaggriculture/cloud-execution-lab")
V3_REL = LAB_REL / "candidates" / "v3"
EXPERIMENT_REL = V3_REL / "experiments" / "b11_a612_currentstack"
CANONICAL_REL = LAB_REL / "exports" / "titan-current.tar.gz"
EVALUATOR_REL = LAB_REL / "reference" / "evaluator" / "evaluate.py"
ENGINE_DIR_REL = LAB_REL / "reference" / "engine"
ARLENE_REL = LAB_REL / "reference" / "next-panel" / "vendor" / "arlene.py"

CURRENT_CONFIG = {
    "r04_sale_window": True,
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
    "r04_kill_late_water": False,
    "r04_strawberry_endgame": False,
    "r04_strawberry_max_plants": 8,
    "r04_no_late_sale_advance": True,
    "r04_no_late_sale_advance_step": 648,
    "r04_strawberry_topup": True,
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(args, *, cwd: Path) -> None:
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run([str(arg) for arg in args], cwd=cwd, check=True)


def write_tree(files: dict[str, bytes], root: Path) -> None:
    for name, blob in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)


def assert_current_config(package: Path) -> dict:
    config = json.loads((package / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
    if type(config) is not dict:
        raise AssertionError("TITAN-CONFIG.json must be an object")
    for key, want in CURRENT_CONFIG.items():
        got = config.get(key)
        if type(got) is not type(want) or got != want:
            raise AssertionError(f"current score tuple drift {key}: {got!r} != {want!r}")
    return config


def materialize(repo: Path, work: Path) -> tuple[Path, Path, str]:
    canonical = repo / CANONICAL_REL
    if sha256_file(canonical) != CANONICAL_SHA256:
        raise AssertionError("canonical titan-current archive SHA drift")

    v3 = repo / V3_REL
    sys.path.insert(0, str(v3))
    import build_v3  # noqa: E402

    files = build_v3.package_files(canonical)
    blob = build_v3.build_bytes(files)
    digest = sha256_bytes(blob)
    if digest != SHIPPED_ARCHIVE_SHA256:
        raise AssertionError(f"not exact shipped a612 package: {digest}")

    control = work / "control"
    candidate = work / "candidate"
    write_tree(files, control)
    write_tree(files, candidate)
    assert_current_config(control)
    assert_current_config(candidate)

    experiment = repo / EXPERIMENT_REL
    donor = experiment / "b11_mirror_horizon.py"
    entry = experiment / "candidate.py"
    if not donor.is_file() or not entry.is_file():
        raise AssertionError("B11 current-stack source files missing")
    shutil.copy2(donor, candidate / donor.name)
    shutil.copy2(entry, candidate / entry.name)

    for root in (control, candidate):
        for required in (
            "main.py",
            "r04_full_router.py",
            "r04_h4_strawberry.py",
            "r04_no_late_sale_advance.py",
        ):
            if not (root / required).is_file():
                raise AssertionError(f"materialized package missing {required}")
    return control, candidate, digest


def evaluate(repo: Path, candidate: Path, control: Path, output: Path) -> dict:
    args = [
        sys.executable,
        "-B",
        repo / EVALUATOR_REL,
        "--engine-dir",
        repo / ENGINE_DIR_REL,
        "--candidate",
        candidate,
        "--opponent",
        f"current_self={control}",
        "--opponent",
        f"arlene={repo / ARLENE_REL}",
        "--seeds",
        ",".join(map(str, SEEDS)),
        "--game-timeout",
        "180",
        "--recheck-first",
        "--output",
        output,
    ]
    run(args, cwd=repo)
    report = json.loads(output.read_text(encoding="utf-8"))
    if report.get("engine_ref") != ENGINE_REF:
        raise AssertionError(f"engine ref drift: {report.get('engine_ref')!r}")
    return report


def _strict_number(value) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise AssertionError(f"score is not strict numeric: {value!r}")
    value = float(value)
    if not math.isfinite(value):
        raise AssertionError(f"score is nonfinite: {value!r}")
    return value


def indexed(report: dict) -> dict[tuple[str, int, int], dict]:
    games = report.get("games")
    if type(games) is not list:
        raise AssertionError("evaluator report missing games list")
    expected = {
        (opponent, seed, seat)
        for opponent in ("current_self", "arlene")
        for seed in SEEDS
        for seat in (0, 1)
    }
    rows: dict[tuple[str, int, int], dict] = {}
    for game in games:
        opponent = game.get("opponent")
        seed = game.get("seed")
        seat = game.get("candidate_seat")
        if type(seed) is not int or isinstance(seed, bool):
            raise AssertionError(f"invalid seed type: {seed!r}")
        if type(seat) is not int or isinstance(seat, bool) or seat not in (0, 1):
            raise AssertionError(f"invalid seat: {seat!r}")
        key = (opponent, seed, seat)
        if key not in expected or key in rows:
            raise AssertionError(f"unexpected or duplicate evaluator cell: {key}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise AssertionError(f"incomplete evaluator cell {key}: {game.get('failure')!r}")
        scores = game.get("scores")
        if type(scores) is not list or len(scores) != 2:
            raise AssertionError(f"invalid scores for {key}: {scores!r}")
        _strict_number(scores[0])
        _strict_number(scores[1])
        trace = game.get("trace_sha256")
        if type(trace) is not str or len(trace) != 64:
            raise AssertionError(f"invalid trace hash for {key}: {trace!r}")
        rows[key] = game
    if set(rows) != expected:
        raise AssertionError(f"missing evaluator cells: {sorted(expected - set(rows))}")
    return rows


def components(game: dict) -> tuple[float, float, float]:
    seat = game["candidate_seat"]
    scores = game["scores"]
    own = _strict_number(scores[seat])
    rival = _strict_number(scores[1 - seat])
    return own, rival, own - rival


def paired(control: dict, candidate: dict, opponent: str) -> tuple[dict, list[dict]]:
    rows = []
    for seed in SEEDS:
        for seat in (0, 1):
            key = (opponent, seed, seat)
            own0, rival0, margin0 = components(control[key])
            own1, rival1, margin1 = components(candidate[key])
            rows.append(
                {
                    "seed": seed,
                    "candidate_seat": seat,
                    "control_scores": control[key]["scores"],
                    "candidate_scores": candidate[key]["scores"],
                    "control_trace_sha256": control[key]["trace_sha256"],
                    "candidate_trace_sha256": candidate[key]["trace_sha256"],
                    "trace_changed": control[key]["trace_sha256"] != candidate[key]["trace_sha256"],
                    "delta_own": own1 - own0,
                    "delta_rival": rival1 - rival0,
                    "delta_margin": margin1 - margin0,
                }
            )
    dm = [row["delta_margin"] for row in rows]
    do = [row["delta_own"] for row in rows]
    dr = [row["delta_rival"] for row in rows]
    summary = {
        "cells": len(rows),
        "positive": sum(value > 0 for value in dm),
        "zero": sum(value == 0 for value in dm),
        "negative": sum(value < 0 for value in dm),
        "mean_delta_margin": statistics.mean(dm),
        "min_delta_margin": min(dm),
        "max_delta_margin": max(dm),
        "mean_delta_own": statistics.mean(do),
        "mean_delta_rival": statistics.mean(dr),
        "trace_changed_cells": sum(row["trace_changed"] for row in rows),
    }
    return summary, rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)

    arlene = repo / ARLENE_REL
    if sha256_file(arlene) != ARLENE_SHA256:
        raise AssertionError("Arlene source SHA drift")

    with tempfile.TemporaryDirectory(prefix="titan-a612-b11-") as tmp:
        work = Path(tmp)
        control_dir, candidate_dir, archive_digest = materialize(repo, work)
        control_raw = out / "control-raw.json"
        candidate_raw = out / "b11-raw.json"
        control_report = evaluate(repo, control_dir / "main.py", control_dir / "main.py", control_raw)
        candidate_report = evaluate(repo, candidate_dir / "candidate.py", control_dir / "main.py", candidate_raw)
        control = indexed(control_report)
        candidate = indexed(candidate_report)

        arlene_summary, arlene_rows = paired(control, candidate, "arlene")
        self_summary, self_rows = paired(control, candidate, "current_self")

        arlene_exact = all(
            row["delta_own"] == 0
            and row["delta_rival"] == 0
            and row["delta_margin"] == 0
            and not row["trace_changed"]
            for row in arlene_rows
        )
        self_clean = self_summary["negative"] == 0 and self_summary["mean_delta_margin"] > 0
        if arlene_exact and self_clean and self_summary["trace_changed_cells"] > 0:
            disposition = "PASS_current_stack_selector_screen_expand"
        elif not arlene_exact:
            disposition = "HOLD_arlene_identity_regressed"
        else:
            disposition = "HOLD_current_self_not_clean_positive"

        receipt = {
            "schema": "titan-v31-a612-b11-currentstack/v1",
            "truth_boundary": (
                "Evidence-only exact-a612 composition screen. The classifier source is the exact "
                "reviewed frozen B11 blob; this runner changes no production/package/default bytes. "
                "PASS earns a wider/current-canonical consumer only, not promotion."
            ),
            "canonical_head": CANONICAL_HEAD,
            "shipped_archive_sha256": archive_digest,
            "engine_ref": ENGINE_REF,
            "seeds": list(SEEDS),
            "opponents": ["current_self", "arlene"],
            "score_tuple": CURRENT_CONFIG,
            "donor_blob": DONOR_BLOB,
            "arlene": {"summary": arlene_summary, "rows": arlene_rows},
            "current_self": {"summary": self_summary, "rows": self_rows},
            "decision": disposition,
        }
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(receipt, indent=2, sort_keys=True))
        if disposition.startswith("HOLD_"):
            return 3
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
