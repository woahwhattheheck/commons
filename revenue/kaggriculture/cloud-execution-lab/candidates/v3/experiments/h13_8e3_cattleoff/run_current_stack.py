#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Evidence-only H13 horizon8->10 screen on shipped 8e3 with cattle OFF.

Both arms inherit the exact current deterministic V3 package, then use the reviewed
#12505 score-facing transform.  They differ only in strict integer sale horizon 8 vs
10 while cattle remains OFF and shipped B5/JIT/H4/gated-L3/sale-fertilizer stay ON.
This is an official-interpreter evidence gate, not a default/package/Kaggle mutation.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile


CURRENT_COMMIT = "8e3d92a286806f9f9525973ee7d359b629a11487"
CURRENT_PACKAGE_SHA256 = "4d920b2d8948488dc4f491a3a2b3d038c830d723baaaaba1e4470799b66f7d13"
DONOR_BLOB = "9c5e46428f0a2357d7db6e46c4aa5f1f4748717d"
ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
EXPECTED_RNG_SEED = 20260911
SEEDS = tuple(range(2611151001, 2611151009))
OPPONENTS = ("h8_self", "arlene")

LAB_REL = Path("revenue/kaggriculture/cloud-execution-lab")
V3_REL = LAB_REL / "candidates" / "v3"
HERE_REL = V3_REL / "experiments" / "h13_8e3_cattleoff"
EVALUATOR_REL = LAB_REL / "reference" / "evaluator" / "evaluate.py"
ARLENE_REL = LAB_REL / "reference" / "next-panel" / "vendor" / "arlene.py"
ARLENE_SHA256 = "1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4"
TRACE_HEX = frozenset("0123456789abcdef")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, *, cwd: Path) -> None:
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run([str(a) for a in args], cwd=cwd, check=True)


def typed(value):
    if type(value) is dict:
        if not all(type(k) is str for k in value):
            raise TypeError("configuration has non-string key")
        return ("dict", tuple((k, typed(value[k])) for k in sorted(value)))
    if type(value) is list:
        return ("list", tuple(typed(v) for v in value))
    if value is None:
        return ("none", None)
    if type(value) is bool:
        return ("bool", value)
    if type(value) is int:
        return ("int", value)
    if type(value) is float:
        return ("float", value)
    if type(value) is str:
        return ("str", value)
    raise TypeError(f"unsupported config type {type(value).__name__}")


def write_tree(files: dict[str, bytes], root: Path) -> None:
    for name, blob in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)


def config(files: dict[str, bytes]) -> dict:
    value = json.loads(files["TITAN-CONFIG.json"].decode("utf-8"))
    if type(value) is not dict:
        raise AssertionError("TITAN-CONFIG.json must decode to object")
    return value


def require_score_stack(cfg: dict, horizon: int, label: str) -> None:
    expected = {
        "r04_sale_window": True,
        "r04_sale_horizon": horizon,
        "r04_open_roundtrip": 0,
        "r04_row_order": True,
        "r04_evening_flush": True,
        "r04_sale_fertilizer": True,
        "r04_cattle_early": False,
        "r04_no_late_sale_advance": True,
        "r04_no_late_sale_advance_step": 648,
        "r04_strawberry_topup": True,
        "r04_b5_carrot_fertilizer": True,
        "r04_b5_jit_fertilize": True,
    }
    for key, want in expected.items():
        got = cfg.get(key)
        if type(got) is not type(want) or got != want:
            raise AssertionError(f"{label} config drift {key}: {got!r} != {want!r}")


def load_donor(repo: Path):
    path = repo / HERE_REL / "make_submission_12505.py"
    spec = importlib.util.spec_from_file_location("h13_make_submission_12505", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load exact #12505 donor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def materialize(repo: Path) -> tuple[dict[str, bytes], dict[str, bytes], dict]:
    v3 = repo / V3_REL
    sys.path.insert(0, str(v3))
    import build_v3  # noqa: E402

    base = build_v3.package_files()
    base_blob = build_v3.build_bytes(base)
    base_sha = sha256_bytes(base_blob)
    if base_sha != CURRENT_PACKAGE_SHA256 or len(base) != 139:
        raise AssertionError(f"wrong current package {base_sha} / {len(base)} files")

    donor = load_donor(repo)
    h8, cfg8 = donor.apply_submission_config(base, 8)
    h10, cfg10 = donor.apply_submission_config(base, 10)
    require_score_stack(cfg8, 8, "h8")
    require_score_stack(cfg10, 10, "h10")

    if set(h8) != set(h10) or set(h8) != set(base):
        raise AssertionError("package membership drift")
    changed = sorted(name for name in h8 if h8[name] != h10[name])
    if changed != ["TITAN-CONFIG.json"]:
        raise AssertionError(f"h8/h10 differ outside config: {changed}")
    base_to_h8 = sorted(name for name in base if base[name] != h8[name])
    if base_to_h8 != ["TITAN-CONFIG.json"]:
        raise AssertionError(f"score transform changed unexpected package members: {base_to_h8}")

    left, right = copy.deepcopy(cfg8), copy.deepcopy(cfg10)
    if left.pop("r04_sale_horizon", None) != 8 or right.pop("r04_sale_horizon", None) != 10:
        raise AssertionError("horizon isolation failed")
    if typed(left) != typed(right):
        raise AssertionError("typed config differs outside r04_sale_horizon")

    h8_main_sha = sha256_bytes(h8["main.py"])
    h10_main_sha = sha256_bytes(h10["main.py"])
    if h8_main_sha != h10_main_sha:
        raise AssertionError("config-only treatment unexpectedly changed main.py bytes")

    receipt = {
        "schema": "titan-v31-8e3-h13-cattleoff-materialization/v1",
        "current_commit": CURRENT_COMMIT,
        "current_package_sha256": base_sha,
        "package_members": len(base),
        "submission_transform_donor_blob": DONOR_BLOB,
        "base_to_h8_changed_members": base_to_h8,
        "h8_to_h10_changed_members": changed,
        "h8_package_sha256": sha256_bytes(build_v3.build_bytes(h8)),
        "h10_package_sha256": sha256_bytes(build_v3.build_bytes(h10)),
        "h8_main_sha256": h8_main_sha,
        "h10_main_sha256": h10_main_sha,
        "arlene_sha256": ARLENE_SHA256,
        "h8_config": cfg8,
        "h10_config": cfg10,
    }
    return h8, h10, receipt


def is_sha256(value) -> bool:
    return type(value) is str and len(value) == 64 and all(ch in TRACE_HEX for ch in value)


def strict_int(value, label: str) -> int:
    if type(value) is not int:
        raise AssertionError(f"{label} must be JSON integer/non-bool")
    return value


def strict_score(value, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise AssertionError(f"{label} must be finite JSON number")
    return float(value)


def strict_fingerprint(value, label: str) -> dict:
    if type(value) is not dict:
        raise AssertionError(f"{label}: fingerprint must be object")
    if value.get("entry") != "main.py" or value.get("callable") != "agent":
        raise AssertionError(f"{label}: expected main.py/agent fingerprint")
    if not is_sha256(value.get("sha256")):
        raise AssertionError(f"{label}: malformed fingerprint sha256")
    return value


def expected_keys() -> frozenset[tuple[str, int, int]]:
    return frozenset((opp, seed, seat) for opp in OPPONENTS for seed in SEEDS for seat in (0, 1))


def normalized_games(report: dict, label: str) -> dict[tuple[str, int, int], dict]:
    if type(report) is not dict:
        raise AssertionError(f"{label}: report must be object")
    if report.get("engine_ref") != ENGINE_REF:
        raise AssertionError(f"{label}: engine_ref drift {report.get('engine_ref')!r}")
    if strict_int(report.get("agent_rng_seed"), f"{label}.agent_rng_seed") != EXPECTED_RNG_SEED:
        raise AssertionError(f"{label}: rng drift")
    seeds = report.get("seeds")
    if type(seeds) is not list or [strict_int(v, f"{label}.seed") for v in seeds] != list(SEEDS):
        raise AssertionError(f"{label}: exact seed metadata mismatch")
    strict_fingerprint(report.get("candidate"), f"{label}.candidate")
    opponents = report.get("opponents")
    if type(opponents) is not dict or set(opponents) != set(OPPONENTS):
        raise AssertionError(f"{label}: opponent metadata mismatch")
    for name in OPPONENTS:
        strict_fingerprint(opponents[name], f"{label}.opponents[{name!r}]")
    repro = report.get("reproducibility")
    if type(repro) is not dict or repro.get("same_trace_and_scores") is not True:
        raise AssertionError(f"{label}: reproducibility must be literal true")

    games = report.get("games")
    if type(games) is not list:
        raise AssertionError(f"{label}: games must be list")
    expected = expected_keys()
    rows: dict[tuple[str, int, int], dict] = {}
    for i, game in enumerate(games):
        if type(game) is not dict:
            raise AssertionError(f"{label}: game[{i}] must be object")
        opp = game.get("opponent")
        if type(opp) is not str:
            raise AssertionError(f"{label}: opponent must be string")
        seed = strict_int(game.get("seed"), f"{label}.game[{i}].seed")
        seat = strict_int(game.get("candidate_seat"), f"{label}.game[{i}].candidate_seat")
        if seat not in (0, 1):
            raise AssertionError(f"{label}: invalid seat {seat}")
        key = (opp, seed, seat)
        if key not in expected:
            raise AssertionError(f"{label}: unexpected cell {key}")
        if key in rows:
            raise AssertionError(f"{label}: duplicate cell {key}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise AssertionError(f"{label}: incomplete/failed cell {key}")
        scores = game.get("scores")
        if type(scores) is not list or len(scores) != 2:
            raise AssertionError(f"{label}: malformed scores {key}")
        strict_score(scores[0], f"{label}.{key}.score0")
        strict_score(scores[1], f"{label}.{key}.score1")
        if not is_sha256(game.get("trace_sha256")):
            raise AssertionError(f"{label}: malformed trace {key}")
        rows[key] = game
    if frozenset(rows) != expected:
        raise AssertionError(f"{label}: exact 32-cell Cartesian set missing")
    return rows


def validate_actual_fingerprint_custody(control_report: dict, candidate_report: dict, materialization: dict) -> None:
    expected_h8 = materialization.get("h8_main_sha256")
    expected_h10 = materialization.get("h10_main_sha256")
    expected_arlene = materialization.get("arlene_sha256")
    if not is_sha256(expected_h8) or not is_sha256(expected_h10):
        raise AssertionError("materialization missing exact candidate main.py fingerprints")
    if expected_arlene != ARLENE_SHA256:
        raise AssertionError("materialization Arlene fingerprint drift")

    h8_fp = strict_fingerprint(control_report.get("candidate"), "h8.candidate")
    h8_self_fp = strict_fingerprint(control_report.get("opponents", {}).get("h8_self"), "h8.opponents['h8_self']")
    h8_arlene_fp = strict_fingerprint(control_report.get("opponents", {}).get("arlene"), "h8.opponents['arlene']")
    h10_fp = strict_fingerprint(candidate_report.get("candidate"), "h10.candidate")
    h10_self_fp = strict_fingerprint(candidate_report.get("opponents", {}).get("h8_self"), "h10.opponents['h8_self']")
    h10_arlene_fp = strict_fingerprint(candidate_report.get("opponents", {}).get("arlene"), "h10.opponents['arlene']")

    if h8_fp["sha256"] != expected_h8 or h8_self_fp["sha256"] != expected_h8:
        raise AssertionError("h8 report fingerprint is not bound to materialized h8/main.py")
    if h10_fp["sha256"] != expected_h10:
        raise AssertionError("h10 report fingerprint is not bound to materialized h10/main.py")
    if h10_self_fp["sha256"] != expected_h8:
        raise AssertionError("h10 fixed h8_self fingerprint is not bound to materialized h8/main.py")
    if h8_arlene_fp["sha256"] != ARLENE_SHA256 or h10_arlene_fp["sha256"] != ARLENE_SHA256:
        raise AssertionError("Arlene report fingerprint is not bound to pinned vendored source")
    if control_report.get("opponents") != candidate_report.get("opponents"):
        raise AssertionError("fixed opponent fingerprints drifted across arms")


def components(game: dict) -> tuple[float, float, float]:
    seat = strict_int(game["candidate_seat"], "candidate_seat")
    scores = game["scores"]
    own = strict_score(scores[seat], "own")
    rival = strict_score(scores[1 - seat], "rival")
    return own, rival, own - rival


def evaluate(repo: Path, engine_dir: Path, candidate: Path, h8_opponent: Path, output: Path) -> dict:
    args = [
        sys.executable,
        "-B",
        repo / EVALUATOR_REL,
        "--engine-dir",
        engine_dir,
        "--candidate",
        candidate,
        "--opponent",
        f"h8_self={h8_opponent}",
        "--opponent",
        f"arlene={repo / ARLENE_REL}",
        "--seeds",
        ",".join(map(str, SEEDS)),
        "--rng-seed",
        str(EXPECTED_RNG_SEED),
        "--recheck-first",
        "--output",
        output,
    ]
    run(args, cwd=repo)
    return json.loads(output.read_text(encoding="utf-8"))


def summarize(control: dict, candidate: dict, opponent: str) -> tuple[dict, list[dict]]:
    rows = []
    for seed in SEEDS:
        for seat in (0, 1):
            key = (opponent, seed, seat)
            own8, rival8, margin8 = components(control[key])
            own10, rival10, margin10 = components(candidate[key])
            rows.append({
                "opponent": opponent,
                "seed": seed,
                "candidate_seat": seat,
                "h8_scores": control[key]["scores"],
                "h10_scores": candidate[key]["scores"],
                "h8_trace_sha256": control[key]["trace_sha256"],
                "h10_trace_sha256": candidate[key]["trace_sha256"],
                "trace_changed": control[key]["trace_sha256"] != candidate[key]["trace_sha256"],
                "delta_own": own10 - own8,
                "delta_rival": rival10 - rival8,
                "delta_margin": margin10 - margin8,
            })
    deltas = [r["delta_margin"] for r in rows]
    summary = {
        "cells": len(rows),
        "positive": sum(v > 0 for v in deltas),
        "zero": sum(v == 0 for v in deltas),
        "negative": sum(v < 0 for v in deltas),
        "trace_changed": sum(r["trace_changed"] for r in rows),
        "mean_delta_margin": statistics.mean(deltas),
        "median_delta_margin": statistics.median(deltas),
        "min_delta_margin": min(deltas),
        "max_delta_margin": max(deltas),
        "mean_delta_own": statistics.mean(r["delta_own"] for r in rows),
        "mean_delta_rival": statistics.mean(r["delta_rival"] for r in rows),
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

    if sha256_file(repo / ARLENE_REL) != ARLENE_SHA256:
        raise AssertionError("Arlene source SHA drift")

    h8, h10, materialization = materialize(repo)
    (out / "materialization.json").write_text(json.dumps(materialization, indent=2) + "\n", encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="titan-v31-h13-8e3-") as tmp:
        work = Path(tmp)
        h8_dir, h10_dir = work / "h8", work / "h10"
        write_tree(h8, h8_dir)
        write_tree(h10, h10_dir)
        for package in (h8_dir, h10_dir):
            for required in ("main.py", "r04_full_router.py", "r04_h4_strawberry.py", "b5_fertilize.py", "jit_pass_fertilize.py"):
                if not (package / required).is_file():
                    raise AssertionError(f"materialized package missing {required}")

        engine_dir = work / "engine"
        run([sys.executable, "-B", repo / EVALUATOR_REL, "--prepare-engine", engine_dir], cwd=repo)
        raw8 = out / "h8-control-raw.json"
        raw10 = out / "h10-candidate-raw.json"
        report8 = evaluate(repo, engine_dir, h8_dir / "main.py", h8_dir / "main.py", raw8)
        report10 = evaluate(repo, engine_dir, h10_dir / "main.py", h8_dir / "main.py", raw10)
        rows8 = normalized_games(report8, "h8")
        rows10 = normalized_games(report10, "h10")
        validate_actual_fingerprint_custody(report8, report10, materialization)

        self_summary, self_rows = summarize(rows8, rows10, "h8_self")
        arlene_summary, arlene_rows = summarize(rows8, rows10, "arlene")
        all_rows = self_rows + arlene_rows
        any_negative = any(row["delta_margin"] < 0 for row in all_rows)
        changed = sum(row["trace_changed"] for row in all_rows)
        means = (self_summary["mean_delta_margin"], arlene_summary["mean_delta_margin"])
        if changed == 0:
            disposition = "REJECT_ZERO_HORIZON10_POLICY_DELTA"
        elif any_negative:
            disposition = "HOLD_ANY_NEGATIVE_CELL"
        elif all(value > 0 for value in means):
            disposition = "PROMISING_BOTH_REGIMES_POSITIVE_NO_NEGATIVE_WIDEN"
        elif means[0] * means[1] < 0:
            disposition = "HOLD_REGIME_SIGN_SPLIT"
        else:
            disposition = "HOLD_NONPOSITIVE_REGIME_MEAN"

        receipt = {
            "schema": "titan-v31-8e3-h13-cattleoff/v1",
            "truth_boundary": "Offline official-interpreter evidence only; no default/package/Kaggle authority.",
            "current_commit": CURRENT_COMMIT,
            "materialization": materialization,
            "engine_ref": ENGINE_REF,
            "rng_seed": EXPECTED_RNG_SEED,
            "seeds": list(SEEDS),
            "opponents": list(OPPONENTS),
            "h8_entry_fingerprint_sha256": materialization["h8_main_sha256"],
            "h10_entry_fingerprint_sha256": materialization["h10_main_sha256"],
            "arlene_fingerprint_sha256": ARLENE_SHA256,
            "h8_self": {"summary": self_summary, "rows": self_rows},
            "arlene": {"summary": arlene_summary, "rows": arlene_rows},
            "all_negative_cells": [row for row in all_rows if row["delta_margin"] < 0],
            "trace_changed_cells": changed,
            "disposition": disposition,
        }
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        md = [
            "## TITAN V3.1 8e3 H13 cattle-OFF horizon gate",
            "",
            f"- disposition: **{disposition}**",
            f"- current root: `{CURRENT_COMMIT}`",
            f"- current deterministic package: `{CURRENT_PACKAGE_SHA256}` / 139 files",
            "- both arms: cattle OFF; B5 CARROT + JIT + H4 + gated-L3 + sale-fertilizer ON",
            "- sole treatment: `r04_sale_horizon` strict integer `8 -> 10`",
            f"- bound h8/h10 main.py fingerprint: `{materialization['h8_main_sha256']}`",
            f"- bound Arlene fingerprint: `{ARLENE_SHA256}`",
            f"- trace-changed cells: {changed}/32",
            "",
            f"- h8-self: {self_summary['positive']}+/{self_summary['negative']}-/{self_summary['zero']}=; mean ΔM {self_summary['mean_delta_margin']:.3f}; mean Δown {self_summary['mean_delta_own']:.3f}; mean Δrival {self_summary['mean_delta_rival']:.3f}",
            f"- Arlene: {arlene_summary['positive']}+/{arlene_summary['negative']}-/{arlene_summary['zero']}=; mean ΔM {arlene_summary['mean_delta_margin']:.3f}; mean Δown {arlene_summary['mean_delta_own']:.3f}; mean Δrival {arlene_summary['mean_delta_rival']:.3f}",
            "",
            "Any negative cell HOLDS. A positive/no-negative result only authorizes broader current-root/opponent-diverse composition; it does not authorize default-on or submission.",
        ]
        (out / "receipt.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
