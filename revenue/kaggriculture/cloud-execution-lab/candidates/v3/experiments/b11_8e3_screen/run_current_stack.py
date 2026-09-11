#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Evidence-only current-root B11 mirror-adaptive horizon screen.

This consumes the exact reviewed B11 public mirror classifier on the shipped 8e3
B5+JIT gameplay lineage plus #12535 immutable build custody. Both evaluator arms
are first materialized as the exact score-facing cattle-ON H8 tuple via the
reviewed #12505 submission transform. Candidate then changes only SALE_HORIZON
per callback: H8 normally, H10 after eight validated exact public farm mirrors,
restoring the prior horizon in finally.
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

GAMEPLAY_ROOT = "8e3d92a286806f9f9525973ee7d359b629a11487"
STACK_HEAD = "6e5e3c7cc5302d6db4b702cc4fd7c8ca721d7b8a"
PACKAGE_SHA256 = "4d920b2d8948488dc4f491a3a2b3d038c830d723baaaaba1e4470799b66f7d13"
ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
RNG_SEED = 20260911
DONOR_COMMIT = "d8fb85e7dd510cb816e616864760446332e5be7b"
DONOR_PATH = "revenue/kaggriculture/cloud-execution-lab/candidates/v3/experiments/b11_mirror_horizon/b11_mirror_horizon.py"
DONOR_BLOB = "94b270f36c4a27b3d958ac3420bbe5764ac327a1"
SCORE_DONOR_COMMIT = "dd41984ec477d6a1b07bbab2779a2e9f54f879c4"
SCORE_DONOR_PATH = "revenue/kaggriculture/cloud-execution-lab/candidates/v3/make_submission.py"
SCORE_DONOR_BLOB = "9c5e46428f0a2357d7db6e46c4aa5f1f4748717d"
ARLENE_SHA256 = "1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4"
SEEDS = tuple(range(2611151001, 2611151009))
OPPONENTS = ("current_self", "arlene")
EXPECTED_KEYS = frozenset((opponent, seed, seat) for opponent in OPPONENTS for seed in SEEDS for seat in (0, 1))

LAB_REL = Path("revenue/kaggriculture/cloud-execution-lab")
V3_REL = LAB_REL / "candidates" / "v3"
BUILD_REL = V3_REL / "build_v3.py"
EVALUATOR_REL = LAB_REL / "reference" / "evaluator" / "evaluate.py"
ENGINE_REL = LAB_REL / "reference" / "engine"
ARLENE_REL = LAB_REL / "reference" / "next-panel" / "vendor" / "arlene.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=repo)


def git_blob_sha(source: bytes) -> str:
    header = f"blob {len(source)}\0".encode()
    return hashlib.sha1(header + source).hexdigest()


def run(repo: Path, *args: object) -> None:
    command = [str(value) for value in args]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=repo, check=True)


def strict_int(value, label: str) -> int:
    if type(value) is not int:
        raise AssertionError(f"{label}: exact integer required, got {value!r}")
    return value


def finite_number(value, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise AssertionError(f"{label}: finite number required, got {value!r}")
    return float(value)


def strict_trace(value, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise AssertionError(f"{label}: sha256 required")
    try:
        int(value, 16)
    except ValueError as exc:
        raise AssertionError(f"{label}: sha256 required") from exc
    return value


def strict_fingerprint(value, label: str) -> dict:
    if not isinstance(value, dict):
        raise AssertionError(f"{label}: fingerprint object required")
    entry = value.get("entry")
    if not isinstance(entry, str) or not entry:
        raise AssertionError(f"{label}: nonempty entry required")
    if value.get("callable") != "agent":
        raise AssertionError(f"{label}: agent callable required")
    strict_trace(value.get("sha256"), f"{label}.sha256")
    return value


def read_tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def write_tree(files: dict[str, bytes], root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name, blob in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)


def parse_config(files: dict[str, bytes], label: str) -> dict:
    config = json.loads(files["TITAN-CONFIG.json"].decode("utf-8"))
    if not isinstance(config, dict):
        raise AssertionError(f"{label}: TITAN-CONFIG.json must decode to object")
    return config


def set_config(files: dict[str, bytes], config: dict) -> dict[str, bytes]:
    out = dict(files)
    out["TITAN-CONFIG.json"] = (json.dumps(config, indent=2) + "\n").encode("utf-8")
    return out


def load_score_transform(repo: Path):
    source = git(repo, "show", f"{SCORE_DONOR_COMMIT}:{SCORE_DONOR_PATH}")
    if git_blob_sha(source) != SCORE_DONOR_BLOB:
        raise AssertionError("reviewed #12505 score-transform donor blob drift")
    namespace = {
        "__name__": "titan_b11_score_transform_12505",
        "__file__": SCORE_DONOR_PATH,
    }
    exec(compile(source, SCORE_DONOR_PATH, "exec"), namespace)
    transform = namespace.get("apply_submission_config")
    if not callable(transform):
        raise AssertionError("#12505 donor missing apply_submission_config")
    return transform


def assert_current_config(root: Path) -> None:
    config = json.loads((root / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
    expected = {
        "r04_sale_window": True,
        "r04_sale_horizon": 8,
        "r04_open_roundtrip": 0,
        "r04_row_order": True,
        "r04_evening_flush": True,
        "r04_sale_fertilizer": True,
        "r04_cattle_early": True,
        "r04_no_late_sale_advance": True,
        "r04_no_late_sale_advance_step": 648,
        "r04_strawberry_topup": True,
        "r04_b5_carrot_fertilizer": True,
        "r04_b5_jit_fertilize": True,
    }
    for key, want in expected.items():
        got = config.get(key)
        if type(got) is not type(want) or got != want:
            raise AssertionError(f"current config drift {key}: {got!r} != {want!r}")


def materialize(repo: Path, root: Path) -> tuple[Path, Path, dict]:
    raw = root / "raw"
    control = root / "control"
    candidate = root / "candidate"
    run(repo, sys.executable, "-B", repo / BUILD_REL, "--tree", raw)

    raw_files = read_tree(raw)
    raw_cfg = parse_config(raw_files, "raw 8e3 package")
    if raw_cfg.get("r04_sale_window") is not False:
        raise AssertionError("raw 8e3 package must keep r04_sale_window=false before score transform")
    if raw_cfg.get("r04_cattle_early") is not True:
        raise AssertionError("raw 8e3 package must keep cattle ON before score transform")

    transform = load_score_transform(repo)
    score_off, off_cfg = transform(raw_files, 8)
    if off_cfg.get("r04_sale_window") is not True:
        raise AssertionError("score-facing transform must enable sale window")
    if off_cfg.get("r04_sale_horizon") != 8 or type(off_cfg.get("r04_sale_horizon")) is not int:
        raise AssertionError("score-facing transform must use literal H8")
    if off_cfg.get("r04_cattle_early") is not False:
        raise AssertionError("#12505 score-facing transform must produce cattle OFF before control derivation")

    control_cfg = dict(off_cfg)
    control_cfg["r04_cattle_early"] = True
    control_files = set_config(score_off, control_cfg)

    if set(raw_files) != set(score_off) or set(raw_files) != set(control_files):
        raise AssertionError("score-facing materialization changed package membership")
    raw_to_control = sorted(name for name in raw_files if raw_files[name] != control_files[name])
    if raw_to_control != ["TITAN-CONFIG.json"]:
        raise AssertionError(f"score-facing ON control changed unexpected members: {raw_to_control}")
    raw_to_control_keys = sorted(
        key for key in set(raw_cfg) | set(control_cfg)
        if raw_cfg.get(key) != control_cfg.get(key)
    )
    if raw_to_control_keys != ["r04_sale_window"]:
        raise AssertionError(f"score-facing ON control changed unexpected config keys: {raw_to_control_keys}")
    off_to_control_keys = sorted(
        key for key in set(off_cfg) | set(control_cfg)
        if off_cfg.get(key) != control_cfg.get(key)
    )
    if off_to_control_keys != ["r04_cattle_early"]:
        raise AssertionError(f"cattle ON control derivation drift: {off_to_control_keys}")

    write_tree(control_files, control)
    shutil.copytree(control, candidate)

    for package in (control, candidate):
        assert_current_config(package)
        required = (
            "main.py",
            "r04_full_router.py",
            "r04_h4_strawberry.py",
            "r04_no_late_sale_advance.py",
            "b5_fertilize.py",
            "jit_pass_fertilize.py",
        )
        for name in required:
            if not (package / name).is_file():
                raise AssertionError(f"materialized package missing {name}")

    donor = git(repo, "show", f"{DONOR_COMMIT}:{DONOR_PATH}")
    if git_blob_sha(donor) != DONOR_BLOB:
        raise AssertionError("reviewed B11 donor blob drift")
    (candidate / "b11_mirror_horizon.py").write_bytes(donor)

    adapter = r'''# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import r04_full_router as base
import b11_mirror_horizon as b11

CURRENT = dict(
    horizon=8,
    opening=0,
    row_order=True,
    evening_flush=True,
    sale_fertilizer=True,
    cattle_early=True,
    kill_late_water=False,
    strawberry_endgame=False,
    strawberry_max_plants=8,
    no_late_sale_advance=True,
    no_late_sale_advance_step=648,
    strawberry_topup=True,
    b5_carrot_fertilizer=True,
    b5_jit_fertilize=True,
)
_PARENT = base.install(None, **CURRENT)
b11.reset_state()


def agent(observation, configuration=None):
    certified, streak, reason = b11.mirror_certificate(observation)
    selected = b11.MIRROR_HORIZON if certified else b11.BASE_HORIZON
    if selected == b11.MIRROR_HORIZON:
        b11.REPORT["h10_callbacks"] += 1
    else:
        b11.REPORT["h8_callbacks"] += 1
    if len(b11.REPORT["trace"]) < 512:
        step = observation.get("step") if isinstance(observation, dict) else None
        b11.REPORT["trace"].append(
            {"step": step, "horizon": selected, "streak": streak, "reason": reason}
        )
    prior = base.SALE_HORIZON
    base.SALE_HORIZON = selected
    try:
        return _PARENT(observation, configuration)
    finally:
        base.SALE_HORIZON = prior
'''
    (candidate / "b11_candidate.py").write_text(adapter, encoding="utf-8")

    held_keys = (
        "r04_sale_window",
        "r04_sale_horizon",
        "r04_sale_fertilizer",
        "r04_cattle_early",
        "r04_strawberry_topup",
        "r04_no_late_sale_advance",
        "r04_no_late_sale_advance_step",
        "r04_b5_carrot_fertilizer",
        "r04_b5_jit_fertilize",
    )
    materialization = {
        "score_transform_donor": {
            "commit": SCORE_DONOR_COMMIT,
            "blob": SCORE_DONOR_BLOB,
        },
        "raw_to_control_changed_members": raw_to_control,
        "raw_to_control_changed_config_keys": raw_to_control_keys,
        "off_to_control_changed_config_keys": off_to_control_keys,
        "control_config": {key: control_cfg[key] for key in held_keys},
    }
    return control, candidate, materialization


def evaluate(repo: Path, candidate: Path, control: Path, arlene: Path, output: Path) -> dict:
    args: list[object] = [
        sys.executable, "-B", repo / EVALUATOR_REL,
        "--engine-dir", repo / ENGINE_REL,
        "--candidate", candidate,
        "--opponent", f"current_self={control}",
        "--opponent", f"arlene={arlene}",
        "--seeds", ",".join(map(str, SEEDS)),
        "--rng-seed", str(RNG_SEED),
        "--game-timeout", "180",
        "--recheck-first",
        "--output", output,
    ]
    run(repo, *args)
    report = json.loads(output.read_text(encoding="utf-8"))
    if report.get("engine_ref") != ENGINE_REF:
        raise AssertionError(f"engine ref drift {report.get('engine_ref')!r}")
    return report


def normalize(report: dict, label: str) -> dict[tuple[str, int, int], dict]:
    if report.get("schema_version") != 1 or type(report.get("schema_version")) is not int:
        raise AssertionError(f"{label}: schema_version drift")
    if report.get("engine_ref") != ENGINE_REF:
        raise AssertionError(f"{label}: engine ref drift")
    if report.get("agent_rng_seed") != RNG_SEED or type(report.get("agent_rng_seed")) is not int:
        raise AssertionError(f"{label}: rng seed drift")

    seeds = report.get("seeds")
    opponents = report.get("opponents")
    games = report.get("games")
    if not isinstance(seeds, list) or len(seeds) != len(SEEDS):
        raise AssertionError(f"{label}: seed metadata missing")
    for index, (got, want) in enumerate(zip(seeds, SEEDS)):
        if strict_int(got, f"{label}.seeds[{index}]") != want:
            raise AssertionError(f"{label}: seed metadata drift")
    if not isinstance(opponents, dict) or set(opponents) != set(OPPONENTS):
        raise AssertionError(f"{label}: native opponent fingerprint map drift")
    for opponent in OPPONENTS:
        strict_fingerprint(opponents[opponent], f"{label}.opponents[{opponent!r}]")
    strict_fingerprint(report.get("candidate"), f"{label}.candidate")

    reproducibility = report.get("reproducibility")
    if not isinstance(reproducibility, dict) or reproducibility.get("same_trace_and_scores") is not True:
        raise AssertionError(f"{label}: reproducibility recheck failed")
    if not isinstance(games, list):
        raise AssertionError(f"{label}: games missing")

    rows: dict[tuple[str, int, int], dict] = {}
    for index, game in enumerate(games):
        if not isinstance(game, dict):
            raise AssertionError(f"{label}.games[{index}]: object required")
        if game.get("status") != "complete" or not isinstance(game.get("status"), str):
            raise AssertionError(f"{label}.games[{index}]: incomplete status")
        if game.get("failure") is not None:
            raise AssertionError(f"{label}.games[{index}]: failure present")
        opponent = game.get("opponent")
        if opponent not in OPPONENTS or not isinstance(opponent, str):
            raise AssertionError(f"{label}.games[{index}]: opponent drift")
        seed = strict_int(game.get("seed"), f"{label}.games[{index}].seed")
        seat = strict_int(game.get("candidate_seat"), f"{label}.games[{index}].candidate_seat")
        if seed not in SEEDS or seat not in (0, 1):
            raise AssertionError(f"{label}.games[{index}]: undeclared seed/seat")
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2:
            raise AssertionError(f"{label}.games[{index}]: two scores required")
        normalized_scores = [
            finite_number(scores[0], f"{label}.games[{index}].scores[0]"),
            finite_number(scores[1], f"{label}.games[{index}].scores[1]"),
        ]
        trace = strict_trace(game.get("trace_sha256"), f"{label}.games[{index}].trace_sha256")
        key = (opponent, seed, seat)
        if key in rows:
            raise AssertionError(f"{label}: duplicate cell {key!r}")
        normalized = dict(game)
        normalized["scores"] = normalized_scores
        normalized["trace_sha256"] = trace
        rows[key] = normalized

    if frozenset(rows) != EXPECTED_KEYS:
        missing = sorted(EXPECTED_KEYS - frozenset(rows))
        extra = sorted(frozenset(rows) - EXPECTED_KEYS)
        raise AssertionError(f"{label}: exact coverage mismatch missing={missing!r} extra={extra!r}")
    return rows


def components(game: dict) -> tuple[float, float, float]:
    seat = game["candidate_seat"]
    own = finite_number(game["scores"][seat], "own")
    rival = finite_number(game["scores"][1 - seat], "rival")
    return own, rival, own - rival


def paired(control: dict, candidate: dict, opponent: str) -> tuple[dict, list[dict]]:
    cells = []
    for seed in SEEDS:
        for seat in (0, 1):
            key = (opponent, seed, seat)
            c, b = control[key], candidate[key]
            c_own, c_rival, c_margin = components(c)
            b_own, b_rival, b_margin = components(b)
            cells.append({
                "seed": seed,
                "candidate_seat": seat,
                "control_scores": c["scores"],
                "candidate_scores": b["scores"],
                "trace_changed": c["trace_sha256"] != b["trace_sha256"],
                "delta_own": b_own - c_own,
                "delta_rival": b_rival - c_rival,
                "delta_margin": b_margin - c_margin,
            })
    margins = [row["delta_margin"] for row in cells]
    summary = {
        "cells": len(cells),
        "trace_changed_cells": sum(row["trace_changed"] for row in cells),
        "positive": sum(value > 0 for value in margins),
        "zero": sum(value == 0 for value in margins),
        "negative": sum(value < 0 for value in margins),
        "mean_delta_own": statistics.mean(row["delta_own"] for row in cells),
        "mean_delta_rival": statistics.mean(row["delta_rival"] for row in cells),
        "mean_delta_margin": statistics.mean(margins),
        "min_delta_margin": min(margins),
        "max_delta_margin": max(margins),
    }
    return summary, cells


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    arlene = repo / ARLENE_REL
    if sha256(arlene) != ARLENE_SHA256:
        raise AssertionError("Arlene source SHA drift")

    with tempfile.TemporaryDirectory(prefix="titan-8e3-b11-") as temp:
        control_dir, candidate_dir, materialization = materialize(repo, Path(temp))
        control_raw = output / "control-raw.json"
        candidate_raw = output / "candidate-raw.json"
        control_report = evaluate(repo, control_dir / "main.py", control_dir / "main.py", arlene, control_raw)
        candidate_report = evaluate(repo, candidate_dir / "b11_candidate.py", control_dir / "main.py", arlene, candidate_raw)

        if control_report.get("opponents") != candidate_report.get("opponents"):
            raise AssertionError("fixed opponent fingerprints drifted across arms")
        if control_report.get("candidate", {}).get("sha256") == candidate_report.get("candidate", {}).get("sha256"):
            raise AssertionError("control/candidate fingerprints identical; B11 did not materialize")

        control = normalize(control_report, "control")
        candidate = normalize(candidate_report, "candidate")
        self_summary, self_cells = paired(control, candidate, "current_self")
        arlene_summary, arlene_cells = paired(control, candidate, "arlene")

        arlene_identity = all(
            not row["trace_changed"]
            and row["delta_own"] == 0
            and row["delta_rival"] == 0
            and row["delta_margin"] == 0
            for row in arlene_cells
        )
        if not arlene_identity:
            disposition = "HOLD_ARLENE_NOT_H8_IDENTITY"
        elif self_summary["trace_changed_cells"] == 0:
            disposition = "REJECT_NO_CURRENT_8E3_REALIZATION"
        elif self_summary["negative"]:
            disposition = "HOLD_NEGATIVE_CURRENT_8E3_MIRROR_CELL"
        elif self_summary["positive"]:
            disposition = "PROMISING_CURRENT_8E3_SELECTOR_SURVIVES"
        else:
            disposition = "HOLD_CURRENT_8E3_MARGIN_NEUTRAL"

        receipt = {
            "schema": "titan-v31-b11-8e3-screen/v1",
            "gameplay_root": GAMEPLAY_ROOT,
            "stack_head": STACK_HEAD,
            "package_sha256": PACKAGE_SHA256,
            "engine_ref": ENGINE_REF,
            "reviewed_b11_donor": {"commit": DONOR_COMMIT, "blob": DONOR_BLOB},
            "materialization": materialization,
            "seeds": list(SEEDS),
            "opponents": list(OPPONENTS),
            "arlene_exact_h8_identity": arlene_identity,
            "self": {"summary": self_summary, "cells": self_cells},
            "arlene": {"summary": arlene_summary, "cells": arlene_cells},
            "disposition": disposition,
            "truth_boundary": (
                "Official-interpreter score-facing current-8e3 B5+JIT cattle-ON H8 composition evidence only. "
                "Trace delta is an action-realization proxy. Any surviving selector still "
                "requires interaction evidence on the then-current L3/cattle/row-shed stack "
                "and opponent-diverse D3 before score-facing integration."
            ),
        }
        (output / "receipt.json").write_text(
            json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        lines = [
            "## B11 mirror-adaptive horizon — score-facing current 8e3 B5+JIT composition",
            "",
            "Control/candidate share the exact #12505-derived cattle-ON H8 score-facing package.",
            f"Arlene H8 identity: **{'PASS' if arlene_identity else 'FAIL'}**.",
            f"current self: **{self_summary['positive']}+ / {self_summary['negative']}- / {self_summary['zero']}=**, "
            f"trace deltas **{self_summary['trace_changed_cells']}/{self_summary['cells']}**, "
            f"mean Δown **{self_summary['mean_delta_own']:+.3f}**, "
            f"mean Δrival **{self_summary['mean_delta_rival']:+.3f}**, "
            f"mean ΔM **{self_summary['mean_delta_margin']:+.3f}**.",
            f"Arlene: **{arlene_summary['positive']}+ / {arlene_summary['negative']}- / {arlene_summary['zero']}=**, "
            f"trace deltas **{arlene_summary['trace_changed_cells']}/{arlene_summary['cells']}**, "
            f"mean ΔM **{arlene_summary['mean_delta_margin']:+.3f}**.",
            "",
            f"**Disposition: `{disposition}`**",
            "",
            "Evidence only; no production/default/package/submission authority.",
        ]
        (output / "receipt.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(json.dumps(
            {"self": self_summary, "arlene": arlene_summary, "disposition": disposition},
            sort_keys=True,
            allow_nan=False,
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
