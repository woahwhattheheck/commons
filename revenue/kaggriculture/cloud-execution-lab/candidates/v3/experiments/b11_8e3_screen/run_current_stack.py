#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Evidence-only current-8e3 composition screen for B11 mirror-adaptive horizon.

Materialize the exact shipped 8e3 B5+JIT package through the #12535 immutable-base
builder, then compare exact current R04 controls with the reviewed B11 public mirror
classifier scoped around the same H4/L3/B5/JIT parent. The candidate changes only
SALE_HORIZON per callback: H8 unless eight consecutive validated public farm
structures are exact mirrors, H10 after certification.

This is an evidence carrier only. It does not mutate production/default/package
sources and it deliberately holds cattle_early=True so the cattle decision remains
owned by the separate current-root A/B lane.
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

CANONICAL_HEAD = "8e3d92a286806f9f9525973ee7d359b629a11487"
STACK_PARENT = "ccb128a10c40cb71c4f8ff07b05a88578679dc6c"
EXPECTED_PACKAGE_SHA256 = "4d920b2d8948488dc4f491a3a2b3d038c830d723baaaaba1e4470799b66f7d13"
ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
EXPECTED_RNG_SEED = 20260911
DONOR_COMMIT = "d8fb85e7dd510cb816e616864760446332e5be7b"
DONOR_PATH = "revenue/kaggriculture/cloud-execution-lab/candidates/v3/experiments/b11_mirror_horizon/b11_mirror_horizon.py"
DONOR_BLOB = "94b270f36c4a27b3d958ac3420bbe5764ac327a1"
ARLENE_SHA256 = "1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4"
SEEDS = tuple(range(2611151001, 2611151009))
OPPONENTS = ("8e3_self", "arlene")
EXPECTED_KEYS = frozenset(
    (opponent, seed, seat)
    for opponent in OPPONENTS
    for seed in SEEDS
    for seat in (0, 1)
)

LAB_REL = Path("revenue/kaggriculture/cloud-execution-lab")
V3_REL = LAB_REL / "candidates" / "v3"
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
    if type(value) not in (int, float) or not math.isfinite(value):
        raise AssertionError(f"{label}: finite JSON number required, got {value!r}")
    return float(value)


def strict_sha256(value, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise AssertionError(f"{label}: sha256 required")
    try:
        int(value, 16)
    except ValueError as exc:
        raise AssertionError(f"{label}: sha256 required") from exc
    return value


def strict_fingerprint(value, label: str, *, expected_entry: str | None = None) -> dict:
    if not isinstance(value, dict):
        raise AssertionError(f"{label}: fingerprint object required")
    entry = value.get("entry")
    callable_name = value.get("callable")
    if not isinstance(entry, str) or not entry:
        raise AssertionError(f"{label}.entry: nonempty string required")
    if expected_entry is not None and entry != expected_entry:
        raise AssertionError(f"{label}.entry drift: {entry!r} != {expected_entry!r}")
    if callable_name != "agent":
        raise AssertionError(f"{label}.callable drift: {callable_name!r}")
    strict_sha256(value.get("sha256"), f"{label}.sha256")
    return value


def write_package(files: dict[str, bytes], root: Path) -> None:
    for name, data in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def assert_shipped_stack(root: Path) -> None:
    config = json.loads((root / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
    required_true = (
        "r04_row_order",
        "r04_evening_flush",
        "r04_sale_fertilizer",
        "r04_cattle_early",
        "r04_no_late_sale_advance",
        "r04_strawberry_topup",
        "r04_b5_carrot_fertilizer",
        "r04_b5_jit_fertilize",
    )
    for key in required_true:
        if config.get(key) is not True:
            raise AssertionError(f"8e3 package must retain {key}=true")
    if type(config.get("r04_sale_horizon")) is not int or config["r04_sale_horizon"] != 8:
        raise AssertionError("8e3 package must retain literal r04_sale_horizon=8")
    if type(config.get("r04_open_roundtrip")) is not int or config["r04_open_roundtrip"] != 0:
        raise AssertionError("8e3 package must retain literal r04_open_roundtrip=0")
    if (
        type(config.get("r04_no_late_sale_advance_step")) is not int
        or config["r04_no_late_sale_advance_step"] != 648
    ):
        raise AssertionError("8e3 package must retain literal L3 threshold 648")


CURRENT_ADAPTER = r"""# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import r04_full_router as base

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

def agent(observation, configuration=None):
    return _PARENT(observation, configuration)
"""


CANDIDATE_ADAPTER = r"""# SPDX-License-Identifier: Apache-2.0
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
"""


def materialize(repo: Path, root: Path) -> tuple[Path, Path]:
    v3 = repo / V3_REL
    sys.path.insert(0, str(v3))
    import build_v3  # noqa: E402

    files = build_v3.package_files()
    archive = build_v3.build_bytes(files)
    digest = hashlib.sha256(archive).hexdigest()
    if digest != EXPECTED_PACKAGE_SHA256:
        raise AssertionError(f"materialized 8e3 package digest drift: {digest}")

    control = root / "control"
    candidate = root / "candidate"
    write_package(files, control)
    write_package(files, candidate)

    required = (
        "main.py",
        "r04_full_router.py",
        "r04_h4_strawberry.py",
        "r04_no_late_sale_advance.py",
        "b5_fertilize.py",
        "jit_pass_fertilize.py",
    )
    for package in (control, candidate):
        assert_shipped_stack(package)
        for name in required:
            if not (package / name).is_file():
                raise AssertionError(f"materialized package missing {name}")

    donor = git(repo, "show", f"{DONOR_COMMIT}:{DONOR_PATH}")
    header = f"blob {len(donor)}\0".encode()
    if hashlib.sha1(header + donor).hexdigest() != DONOR_BLOB:
        raise AssertionError("reviewed B11 donor blob drift")
    (candidate / "b11_mirror_horizon.py").write_bytes(donor)

    (control / "b11_control.py").write_text(CURRENT_ADAPTER, encoding="utf-8")
    (candidate / "b11_candidate.py").write_text(CANDIDATE_ADAPTER, encoding="utf-8")
    return control, candidate


def evaluate(
    repo: Path,
    candidate: Path,
    control: Path,
    arlene: Path,
    output: Path,
    *,
    recheck: bool,
) -> dict:
    args: list[object] = [
        sys.executable,
        "-B",
        repo / EVALUATOR_REL,
        "--engine-dir",
        repo / ENGINE_REL,
        "--candidate",
        candidate,
        "--opponent",
        f"8e3_self={control}",
        "--opponent",
        f"arlene={arlene}",
        "--seeds",
        ",".join(map(str, SEEDS)),
        "--rng-seed",
        str(EXPECTED_RNG_SEED),
        "--game-timeout",
        "180",
        "--output",
        output,
    ]
    if recheck:
        args.append("--recheck-first")
    run(repo, *args)
    return json.loads(output.read_text(encoding="utf-8"))


def normalize(report: dict, label: str, *, candidate_entry: str) -> dict[tuple[str, int, int], dict]:
    if not isinstance(report, dict):
        raise AssertionError(f"{label}: report must be object")
    if type(report.get("schema_version")) is not int or report.get("schema_version") != 1:
        raise AssertionError(f"{label}: schema_version drift")
    if report.get("engine_ref") != ENGINE_REF:
        raise AssertionError(f"{label}: engine ref drift {report.get('engine_ref')!r}")
    if type(report.get("agent_rng_seed")) is not int or report.get("agent_rng_seed") != EXPECTED_RNG_SEED:
        raise AssertionError(f"{label}: agent_rng_seed drift")

    seeds = report.get("seeds")
    opponents = report.get("opponents")
    games = report.get("games")
    if seeds != list(SEEDS) or any(type(seed) is not int for seed in seeds or []):
        raise AssertionError(f"{label}: seed metadata drift {seeds!r}")
    if not isinstance(opponents, dict) or set(opponents) != set(OPPONENTS):
        raise AssertionError(f"{label}: native opponent fingerprint mapping drift")
    strict_fingerprint(report.get("candidate"), f"{label}.candidate", expected_entry=candidate_entry)
    strict_fingerprint(
        opponents["8e3_self"],
        f"{label}.opponents.8e3_self",
        expected_entry="b11_control.py",
    )
    strict_fingerprint(
        opponents["arlene"],
        f"{label}.opponents.arlene",
        expected_entry="arlene.py",
    )

    reproducibility = report.get("reproducibility")
    if not isinstance(reproducibility, dict) or reproducibility.get("same_trace_and_scores") is not True:
        raise AssertionError(f"{label}: reproducibility recheck failed")
    if not isinstance(games, list):
        raise AssertionError(f"{label}: games missing")

    rows: dict[tuple[str, int, int], dict] = {}
    for index, game in enumerate(games):
        if not isinstance(game, dict):
            raise AssertionError(f"{label}[{index}]: game must be object")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise AssertionError(f"{label}[{index}]: incomplete/failed game")

        opponent = game.get("opponent")
        seed = game.get("seed")
        seat = game.get("candidate_seat")
        if not isinstance(opponent, str) or opponent not in OPPONENTS:
            raise AssertionError(f"{label}[{index}]: opponent drift {opponent!r}")
        if type(seed) is not int or seed not in SEEDS:
            raise AssertionError(f"{label}[{index}]: bad seed {seed!r}")
        if type(seat) is not int or seat not in (0, 1):
            raise AssertionError(f"{label}[{index}]: bad seat {seat!r}")

        key = (opponent, seed, seat)
        if key in rows:
            raise AssertionError(f"{label}: duplicate cell {key!r}")
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2:
            raise AssertionError(f"{label}: invalid scores {key!r}")
        strict_number(scores[0], f"{label}:{key}:score0")
        strict_number(scores[1], f"{label}:{key}:score1")
        strict_sha256(game.get("trace_sha256"), f"{label}:{key}:trace")
        rows[key] = game

    if frozenset(rows) != EXPECTED_KEYS:
        missing = sorted(EXPECTED_KEYS - frozenset(rows))
        extra = sorted(frozenset(rows) - EXPECTED_KEYS)
        raise AssertionError(
            f"{label}: exact cell set mismatch missing={missing!r} extra={extra!r}"
        )
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
            cells.append(
                {
                    "seed": seed,
                    "candidate_seat": seat,
                    "control_scores": c["scores"],
                    "candidate_scores": b["scores"],
                    "trace_changed": c["trace_sha256"] != b["trace_sha256"],
                    "delta_own": b_own - c_own,
                    "delta_rival": b_rival - c_rival,
                    "delta_margin": b_margin - c_margin,
                }
            )
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
        control_dir, candidate_dir = materialize(repo, Path(temp))
        control_raw = output / "control-raw.json"
        candidate_raw = output / "candidate-raw.json"

        control_report = evaluate(
            repo,
            control_dir / "b11_control.py",
            control_dir / "b11_control.py",
            arlene,
            control_raw,
            recheck=True,
        )
        candidate_report = evaluate(
            repo,
            candidate_dir / "b11_candidate.py",
            control_dir / "b11_control.py",
            arlene,
            candidate_raw,
            recheck=True,
        )

        if control_report.get("opponents") != candidate_report.get("opponents"):
            raise AssertionError("fixed opponent fingerprints drifted across arms")

        control = normalize(
            control_report,
            "control",
            candidate_entry="b11_control.py",
        )
        candidate = normalize(
            candidate_report,
            "candidate",
            candidate_entry="b11_candidate.py",
        )

        self_summary, self_cells = paired(control, candidate, "8e3_self")
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
            "canonical_head": CANONICAL_HEAD,
            "stack_parent": STACK_PARENT,
            "package_sha256": EXPECTED_PACKAGE_SHA256,
            "engine_ref": ENGINE_REF,
            "reviewed_b11_donor": {
                "commit": DONOR_COMMIT,
                "blob": DONOR_BLOB,
            },
            "held_current_tuple": {
                "horizon": 8,
                "opening": 0,
                "row_order": True,
                "evening_flush": True,
                "sale_fertilizer": True,
                "cattle_early": True,
                "no_late_sale_advance": True,
                "no_late_sale_advance_step": 648,
                "strawberry_topup": True,
                "b5_carrot_fertilizer": True,
                "b5_jit_fertilize": True,
            },
            "seeds": list(SEEDS),
            "opponents": list(OPPONENTS),
            "arlene_exact_h8_identity": arlene_identity,
            "self": {"summary": self_summary, "cells": self_cells},
            "arlene": {"summary": arlene_summary, "cells": arlene_cells},
            "disposition": disposition,
            "truth_boundary": (
                "Official-interpreter current-8e3 B5+JIT composition evidence only. "
                "B11 changes callback-local SALE_HORIZON only; cattle remains ON and owned "
                "by the separate current-root cattle A/B. Any surviving B11 selector must "
                "recompose through the then-current #12535/#12541/cattle/row-shed convergence "
                "root before production/default/submission authority."
            ),
        }
        (output / "receipt.json").write_text(
            json.dumps(receipt, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        lines = [
            "## B11 mirror-adaptive horizon — exact 8e3 B5+JIT composition",
            "",
            f"Arlene H8 identity: **{'PASS' if arlene_identity else 'FAIL'}**.",
            (
                f"8e3 mirror: **{self_summary['positive']}+ / "
                f"{self_summary['negative']}- / {self_summary['zero']}=**, "
                f"trace deltas **{self_summary['trace_changed_cells']}/{self_summary['cells']}**, "
                f"mean Δown **{self_summary['mean_delta_own']:+.3f}**, "
                f"mean Δrival **{self_summary['mean_delta_rival']:+.3f}**, "
                f"mean ΔM **{self_summary['mean_delta_margin']:+.3f}**."
            ),
            (
                f"Arlene: **{arlene_summary['positive']}+ / "
                f"{arlene_summary['negative']}- / {arlene_summary['zero']}=**, "
                f"trace deltas **{arlene_summary['trace_changed_cells']}/{arlene_summary['cells']}**, "
                f"mean ΔM **{arlene_summary['mean_delta_margin']:+.3f}**."
            ),
            "",
            f"**Disposition: `{disposition}`**",
            "",
            "Current-root evidence only; no default/package/submission authority.",
        ]
        (output / "receipt.md").write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "self": self_summary,
                    "arlene": arlene_summary,
                    "disposition": disposition,
                },
                sort_keys=True,
                allow_nan=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
