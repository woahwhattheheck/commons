#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Evidence-only current-a612 composition screen for B11 mirror-adaptive horizon.

Materialize the exact shipped a612 package, then compare it with the exact reviewed
B11 public mirror classifier scoped around that same current R04/H4/L3 parent.
The candidate changes only SALE_HORIZON per callback: H8 unless eight consecutive
validated public farm structures are exact mirrors, H10 after certification.

The paired gate uses exact a612 self plus vendored Arlene over eight frozen seeds
and both seats. Arlene must remain byte-behavior identity; self must show a
nonnegative realized effect before B11 earns any wider current-stack work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile

CANONICAL_HEAD = "a6120d0ea1bdb75eb0da2239220efce551f624a6"
CANONICAL_SHA256 = "5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1"
BASE_ARCHIVE_SHA256 = "400ae640f3258b6a6ff19f9da99c66ef9c433e315febb1d72c75296cddeb277c"
ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
DONOR_COMMIT = "d8fb85e7dd510cb816e616864760446332e5be7b"
DONOR_PATH = "revenue/kaggriculture/cloud-execution-lab/candidates/v3/experiments/b11_mirror_horizon/b11_mirror_horizon.py"
DONOR_BLOB = "94b270f36c4a27b3d958ac3420bbe5764ac327a1"
ARLENE_SHA256 = "1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4"
SEEDS = tuple(range(2611151001, 2611151009))
OPPONENTS = ("a612_self", "arlene")
EXPECTED_KEYS = frozenset((opponent, seed, seat) for opponent in OPPONENTS for seed in SEEDS for seat in (0, 1))

LAB_REL = Path("revenue/kaggriculture/cloud-execution-lab")
V3_REL = LAB_REL / "candidates" / "v3"
CANONICAL_REL = LAB_REL / "exports" / "titan-current.tar.gz"
EVALUATOR_REL = LAB_REL / "reference" / "evaluator" / "evaluate.py"
ENGINE_REL = LAB_REL / "reference" / "engine"
ARLENE_REL = LAB_REL / "reference" / "next-panel" / "vendor" / "arlene.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=repo)


def run(repo: Path, *args: object) -> None:
    command = [str(value) for value in args]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=repo, check=True)


def strict_number(value, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise AssertionError(f"{label}: finite JSON number required, got {value!r}")
    return float(value)


def write_package(files: dict[str, bytes], root: Path) -> None:
    for name, data in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


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
    }
    for key, want in expected.items():
        got = config.get(key)
        if type(got) is not type(want) or got != want:
            raise AssertionError(f"canonical config drift {key}: {got!r} != {want!r}")


def materialize(repo: Path, root: Path) -> tuple[Path, Path]:
    canonical = repo / CANONICAL_REL
    if sha256(canonical) != CANONICAL_SHA256:
        raise AssertionError("canonical archive SHA drift")
    v3 = repo / V3_REL
    sys.path.insert(0, str(v3))
    import build_v3  # noqa: E402

    files = build_v3.package_files(canonical)
    archive = build_v3.build_bytes(files)
    if hashlib.sha256(archive).hexdigest() != BASE_ARCHIVE_SHA256:
        raise AssertionError("materialized a612 package digest drift")

    control = root / "control"
    candidate = root / "candidate"
    write_package(files, control)
    write_package(files, candidate)
    for package in (control, candidate):
        assert_current_config(package)
        for required in ("main.py", "r04_full_router.py", "r04_h4_strawberry.py", "r04_no_late_sale_advance.py"):
            if not (package / required).is_file():
                raise AssertionError(f"materialized package missing {required}")

    donor = git(repo, "show", f"{DONOR_COMMIT}:{DONOR_PATH}")
    header = f"blob {len(donor)}\0".encode()
    if hashlib.sha1(header + donor).hexdigest() != DONOR_BLOB:
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
        b11.REPORT["trace"].append({"step": step, "horizon": selected, "streak": streak, "reason": reason})
    prior = base.SALE_HORIZON
    base.SALE_HORIZON = selected
    try:
        return _PARENT(observation, configuration)
    finally:
        base.SALE_HORIZON = prior
'''
    (candidate / "b11_candidate.py").write_text(adapter, encoding="utf-8")
    return control, candidate


def evaluate(repo: Path, candidate: Path, control: Path, arlene: Path, output: Path, *, recheck: bool) -> dict:
    args: list[object] = [
        sys.executable, "-B", repo / EVALUATOR_REL,
        "--engine-dir", repo / ENGINE_REL,
        "--candidate", candidate,
        "--opponent", f"a612_self={control}",
        "--opponent", f"arlene={arlene}",
        "--seeds", ",".join(map(str, SEEDS)),
        "--rng-seed", "20260911",
        "--game-timeout", "180",
        "--output", output,
    ]
    if recheck:
        args.append("--recheck-first")
    run(repo, *args)
    report = json.loads(output.read_text(encoding="utf-8"))
    if report.get("engine_ref") != ENGINE_REF:
        raise AssertionError(f"engine ref drift {report.get('engine_ref')!r}")
    return report


def normalize(report: dict, label: str) -> dict[tuple[str, int, int], dict]:
    seeds = report.get("seeds")
    opponents = report.get("opponents")
    games = report.get("games")
    if seeds != list(SEEDS) or any(type(seed) is not int for seed in seeds or []):
        raise AssertionError(f"{label}: seed metadata drift {seeds!r}")
    if opponents != list(OPPONENTS):
        raise AssertionError(f"{label}: opponent metadata drift {opponents!r}")
    if not isinstance(games, list):
        raise AssertionError(f"{label}: games missing")
    rows = {}
    for index, game in enumerate(games):
        if not isinstance(game, dict):
            raise AssertionError(f"{label}[{index}]: game must be object")
        opponent, seed, seat = game.get("opponent"), game.get("seed"), game.get("candidate_seat")
        if not isinstance(opponent, str) or opponent not in OPPONENTS:
            raise AssertionError(f"{label}[{index}]: opponent drift {opponent!r}")
        if type(seed) is not int or seed not in SEEDS or type(seat) is not int or seat not in (0, 1):
            raise AssertionError(f"{label}[{index}]: bad seed/seat {seed!r}/{seat!r}")
        key = (opponent, seed, seat)
        if key in rows:
            raise AssertionError(f"{label}: duplicate cell {key!r}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise AssertionError(f"{label}: incomplete cell {key!r}: {game.get('failure')!r}")
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2:
            raise AssertionError(f"{label}: invalid scores {key!r}")
        strict_number(scores[0], f"{label}:{key}:score0")
        strict_number(scores[1], f"{label}:{key}:score1")
        trace = game.get("trace_sha256")
        if not isinstance(trace, str) or len(trace) != 64:
            raise AssertionError(f"{label}: invalid trace {key!r}")
        rows[key] = game
    if frozenset(rows) != EXPECTED_KEYS:
        raise AssertionError(f"{label}: exact cell set mismatch")
    return rows


def components(game: dict) -> tuple[float, float, float]:
    seat = game["candidate_seat"]
    own = strict_number(game["scores"][seat], "own")
    rival = strict_number(game["scores"][1 - seat], "rival")
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

    with tempfile.TemporaryDirectory(prefix="titan-a612-b11-") as temp:
        control_dir, candidate_dir = materialize(repo, Path(temp))
        control_raw = output / "control-raw.json"
        candidate_raw = output / "candidate-raw.json"
        control_report = evaluate(repo, control_dir / "main.py", control_dir / "main.py", arlene, control_raw, recheck=True)
        candidate_report = evaluate(repo, candidate_dir / "b11_candidate.py", control_dir / "main.py", arlene, candidate_raw, recheck=True)
        control = normalize(control_report, "control")
        candidate = normalize(candidate_report, "candidate")

        self_summary, self_cells = paired(control, candidate, "a612_self")
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
            disposition = "REJECT_NO_CURRENT_A612_REALIZATION"
        elif self_summary["negative"]:
            disposition = "HOLD_NEGATIVE_CURRENT_A612_MIRROR_CELL"
        elif self_summary["positive"]:
            disposition = "PROMISING_CURRENT_A612_SELECTOR_SURVIVES"
        else:
            disposition = "HOLD_CURRENT_A612_MARGIN_NEUTRAL"

        receipt = {
            "schema": "titan-v31-b11-a612-screen/v1",
            "canonical_head": CANONICAL_HEAD,
            "engine_ref": ENGINE_REF,
            "reviewed_b11_donor": {"commit": DONOR_COMMIT, "blob": DONOR_BLOB},
            "seeds": list(SEEDS),
            "opponents": list(OPPONENTS),
            "arlene_exact_h8_identity": arlene_identity,
            "self": {"summary": self_summary, "cells": self_cells},
            "arlene": {"summary": arlene_summary, "cells": arlene_cells},
            "disposition": disposition,
            "truth_boundary": (
                "Official-interpreter current-a612 composition evidence only. Trace delta is an action-realization proxy; "
                "the evaluator does not expose B11's private module telemetry. Any surviving selector still requires "
                "interaction evidence with the then-current H13/cattle/package stack before score-facing integration."
            ),
        }
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        lines = [
            "## B11 mirror-adaptive horizon — exact a612 composition",
            "",
            f"Arlene H8 identity: **{'PASS' if arlene_identity else 'FAIL'}**.",
            f"a612 mirror: **{self_summary['positive']}+ / {self_summary['negative']}- / {self_summary['zero']}=**, "
            f"trace deltas **{self_summary['trace_changed_cells']}/{self_summary['cells']}**, mean Δown **{self_summary['mean_delta_own']:+.3f}**, "
            f"mean Δrival **{self_summary['mean_delta_rival']:+.3f}**, mean ΔM **{self_summary['mean_delta_margin']:+.3f}**.",
            f"Arlene: **{arlene_summary['positive']}+ / {arlene_summary['negative']}- / {arlene_summary['zero']}=**, "
            f"trace deltas **{arlene_summary['trace_changed_cells']}/{arlene_summary['cells']}**, mean ΔM **{arlene_summary['mean_delta_margin']:+.3f}**.",
            "",
            f"**Disposition: `{disposition}`**",
            "",
            "Current-stack evidence only; no default/package/submission authority.",
        ]
        (output / "receipt.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(json.dumps({"self": self_summary, "arlene": arlene_summary, "disposition": disposition}, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
