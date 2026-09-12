#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-pinned matched current-V5 evaluation for animal cadence.

Runs the same canonical archive twice for each opponent/seed/seat cell: untouched
baseline and baseline plus only the published certificate authority + candidate
entrypoint.  The script intentionally reuses the Commons official interpreter,
reference-policy bank, and pack adapter instead of implementing another engine.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import statistics
import sys
import tempfile

SCHEMA = "titan-v5/animal-cadence/matched-eval/v1"
CURRENT_ARCHIVE_SHA256 = "74c6a2e59e720609b1d216317bb9651399e05fdd045ac2129e15c000ff0f3894"
CURRENT_ARCHIVE_BYTES = 466769
CURRENT_MAIN_AT_CLAIM = "79d5268af77b0b6de80def2c10655600285dd490"
ENGINE_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
EVALUATOR_BLOB = "1fb6b655bb4ca1e1684be165a8ef513e2e6c2325"
HELPER_BLOB = "aefdc6cff09cc7693a5ae0da01e88756171a65f0"
CANDIDATE_BLOB = "e5f545c452e54337e978c3fa553535e967d50569"
BUILDER_BLOB = "e7b7e7d0372e163c1b83e481d823a82a9fbedeab"
ARCHIVE_POINTER_BLOB = "2797bf01b58803b0d0f99abfa776c78c91961fcb"
DEFAULT_SEEDS = (1209121623, 1209121625)
DEFAULT_OPPONENTS = ("apex_v7", "arlene_v14")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_blob(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def require_blob(path, expected):
    actual = git_blob(path)
    if actual != expected:
        raise ValueError(f"source_pin_mismatch:{path}:{actual}:{expected}")
    return {"git_blob": actual, "sha256": digest(path), "bytes": Path(path).stat().st_size}


def write_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def safe_copy_files(source, target, names):
    target.mkdir(parents=True, exist_ok=True)
    for name in names:
        src = source / name
        if not src.is_file():
            raise ValueError(f"missing_candidate_source:{name}")
        (target / name).write_bytes(src.read_bytes())


def animal_snapshot(farm):
    found = {}
    if not isinstance(farm, dict) or not isinstance(farm.get("tiles"), list):
        return found
    for y, row in enumerate(farm["tiles"]):
        if not isinstance(row, list):
            continue
        for x, tile in enumerate(row):
            if isinstance(tile, dict) and tile.get("animal") in ("GOOSE", "COW", "SHEEP"):
                found[f"{x},{y}"] = {
                    "animal": tile.get("animal"),
                    "consecutive_unfed": tile.get("consecutive_unfed"),
                    "fed_today": tile.get("fed_today"),
                    "cared_today": tile.get("cared_today"),
                    "pending_care_bonus": tile.get("pending_care_bonus", 0),
                }
    return found


def observe_animals(state, seat, tracker, step):
    farms = (state[0].observation.get("farms") if state and isinstance(state[0].observation, dict) else None)
    if not isinstance(farms, list) or seat >= len(farms):
        return
    current = animal_snapshot(farms[seat])
    prior = tracker.get("last", {})
    for pos, old in prior.items():
        if pos not in current and old.get("consecutive_unfed") == 1 and old.get("fed_today") is False:
            tracker["animal_escapes"].append({"step": step, "position": pos, "animal": old.get("animal")})
    pending = sum(v.get("pending_care_bonus", 0) for v in current.values()
                  if type(v.get("pending_care_bonus", 0)) is int)
    tracker["care_bonus_by_step"].append([step, pending])
    tracker["animal_count_by_step"].append([step, len(current)])
    tracker["last"] = current


def margin(game, seat):
    if game.get("status") != "complete" or game.get("steps") != 719:
        return None
    scores = game.get("scores")
    if not isinstance(scores, list) or len(scores) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in scores):
        return None
    return scores[seat] - scores[1-seat]


def own_score(game, seat):
    scores = game.get("scores")
    if game.get("status") != "complete" or not isinstance(scores, list) or len(scores) != 2:
        return None
    value = scores[seat]
    return value if isinstance(value, (int, float)) and math.isfinite(value) else None


def canonical_game(game):
    """Return only deterministic game evidence; exclude wall/CPU/process timing noise."""
    if not isinstance(game, dict):
        raise ValueError("malformed_game")
    keep = (
        "status", "steps", "episode_steps", "scores", "bank_snapshot",
        "daily_bank", "trace_sha256", "failure",
    )
    projected = {key: copy.deepcopy(game[key]) for key in keep if key in game}
    # Keep bounded deterministic resource counters when the evaluator exposes them,
    # but never copy timing fields or process identifiers into canonical evidence.
    actors = game.get("actors")
    if isinstance(actors, list):
        clean = []
        for actor in actors:
            if not isinstance(actor, dict):
                continue
            clean.append({key: copy.deepcopy(actor[key]) for key in (
                "calls", "timeouts", "errors", "invalid_actions", "exit_code"
            ) if key in actor})
        projected["actors"] = clean
    return projected


def outcome(margin_value):
    if margin_value is None:
        return None
    return "W" if margin_value > 0 else "L" if margin_value < 0 else "T"


def summarize(cells):
    valid = [c for c in cells if c.get("complete_pair")]
    deltas = [c["margin_delta"] for c in valid]
    own = [c["own_score_delta"] for c in valid]
    return {
        "scheduled_pairs": len(cells),
        "complete_pairs": len(valid),
        "failed_pairs": len(cells) - len(valid),
        "baseline_wtl": {k: sum(c["baseline_outcome"] == k for c in valid) for k in ("W", "T", "L")},
        "candidate_wtl": {k: sum(c["candidate_outcome"] == k for c in valid) for k in ("W", "T", "L")},
        "mean_margin_delta": statistics.mean(deltas) if deltas else None,
        "min_margin_delta": min(deltas) if deltas else None,
        "mean_own_score_delta": statistics.mean(own) if own else None,
        "loss_flips": sum(c["baseline_outcome"] == "L" and c["candidate_outcome"] != "L" for c in valid),
        "new_losses": sum(c["baseline_outcome"] != "L" and c["candidate_outcome"] == "L" for c in valid),
        "authority_engagements": sum(c.get("candidate_metrics", {}).get("authority_engagements", 0) for c in valid),
        "candidate_engagements": sum(c.get("candidate_metrics", {}).get("candidate_engagements", 0) for c in valid),
        "feed_actions_suppressed": sum(c.get("candidate_metrics", {}).get("feed_actions_suppressed", 0) for c in valid),
        "unique_tile_wheat_saved": sum(c.get("candidate_metrics", {}).get("unique_tile_wheat_saved", 0) for c in valid),
        "animal_escape_delta": sum(c["animal_escape_delta"] for c in valid),
        "care_bonus_divergence_steps": sum(c["care_bonus_divergence_steps"] for c in valid),
    }


def validate_report(report):
    if not isinstance(report, dict) or report.get("schema") != SCHEMA:
        raise ValueError("malformed_report")
    run = report.get("run")
    cells = report.get("cells")
    if not isinstance(run, dict) or not isinstance(cells, list) or not cells:
        raise ValueError("empty_cells")
    opponents = run.get("opponent_names")
    seeds = run.get("seeds")
    seats = run.get("seats")
    if not isinstance(opponents, list) or not isinstance(seeds, list) or not isinstance(seats, list):
        raise ValueError("malformed_run_identity")
    expected_keys = {(opponent, seed, seat) for opponent in opponents for seed in seeds for seat in seats}
    keys = set()
    for cell in cells:
        key = (cell.get("opponent"), cell.get("seed"), cell.get("seat"))
        if key in keys:
            raise ValueError("duplicate_cell")
        keys.add(key)
        if cell.get("baseline", {}).get("status") != "complete" or cell.get("candidate", {}).get("status") != "complete":
            raise ValueError("incomplete_cell")
        for field in ("baseline_margin", "candidate_margin", "margin_delta", "baseline_own_score", "candidate_own_score", "own_score_delta"):
            if not isinstance(cell.get(field), (int, float)) or not math.isfinite(cell[field]):
                raise ValueError(f"nonfinite_metric:{field}")
        metrics = cell.get("candidate_metrics")
        if (not isinstance(metrics, dict)
                or metrics.get("schema") != "titan-v5/animal-cadence/matched-eval-agent-metrics/v1"):
            raise ValueError("malformed_candidate_metrics")
        errors = metrics.get("errors")
        if not isinstance(errors, dict):
            raise ValueError("malformed_candidate_errors")
        if errors:
            raise ValueError("candidate_adapter_errors")
    expected = run.get("expected_cells")
    if type(expected) is not int or expected != len(cells) or keys != expected_keys:
        raise ValueError("unmatched_cells")
    summary = report.get("summary")
    if not isinstance(summary, dict) or summary.get("candidate_engagements", 0) <= 0:
        raise ValueError("zero_candidate_engagement")
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kg-root", type=Path, required=True, help="revenue/kaggriculture")
    p.add_argument("--engine-dir", type=Path, required=True)
    p.add_argument("--baseline", type=Path, default=None)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seeds", default=",".join(map(str, DEFAULT_SEEDS)))
    p.add_argument("--seats", default="0,1")
    p.add_argument("--opponents", default=",".join(DEFAULT_OPPONENTS))
    args = p.parse_args()
    if sys.platform != "linux":
        p.error("Linux required for process-isolated official-interpreter games")
    root = args.kg_root.resolve(strict=True)
    lab = root / "cloud-execution-lab"
    here = Path(__file__).resolve().parent
    source = here.parent
    baseline_path = (args.baseline or (lab / "exports/titan-current.tar.gz")).resolve(strict=True)
    if baseline_path.stat().st_size != CURRENT_ARCHIVE_BYTES or digest(baseline_path) != CURRENT_ARCHIVE_SHA256:
        raise ValueError("current_archive_identity_mismatch")

    helper_path = lab / "candidates/v5/joint-liquidity-bench/paired.py"
    evaluator_path = lab / "reference/evaluator/evaluate.py"
    pins = {
        "helper": require_blob(helper_path, HELPER_BLOB),
        "evaluator": require_blob(evaluator_path, EVALUATOR_BLOB),
        "candidate": require_blob(source / "alternate_feed.py", CANDIDATE_BLOB),
        "builder": require_blob(source / "certificate_builder.py", BUILDER_BLOB),
        "archive_pointer": require_blob(lab / "runtime/integrated-selected/CURRENT-ARCHIVE.json", ARCHIVE_POINTER_BLOB),
    }
    helper = load(helper_path, "cadence_existing_v5_helper")
    harness = helper.authenticate_harness(root)
    evaluator = load(evaluator_path, "cadence_existing_evaluator")
    pack = load(root / "cloud-pack/pack.py", "cadence_existing_pack")
    bridge = load(root / helper.BANK / "reference_policies.py", "cadence_existing_bank")
    loader = root / "20260907-offline-agent/evaluate.py"
    engine_hashes = evaluator.verify_sources(args.engine_dir)
    if helper.git_blob_id(args.engine_dir / "kaggriculture.py") != ENGINE_BLOB:
        raise ValueError("official_engine_blob_mismatch")

    seeds = [int(v) for v in args.seeds.split(",")]
    seats = [int(v) for v in args.seats.split(",")]
    opponents = args.opponents.split(",")
    if len(set(seeds)) != len(seeds) or not seeds or not set(seats) <= {0, 1} or len(set(seats)) != len(seats):
        p.error("seeds must be unique integers; seats a unique subset of 0,1")
    if not opponents or not set(opponents) <= {"apex_v7", "arlene_v14"} or len(set(opponents)) != len(opponents):
        p.error("opponents must be unique subset of apex_v7,arlene_v14")
    args.output.mkdir(parents=True, exist_ok=False)

    baseline_members = helper.archive_members(baseline_path)
    archive_member_sha256 = {
        name: hashlib.sha256(data).hexdigest()
        for name, data in sorted(baseline_members.items())
    }
    required_members = ("main.py", "TITAN-CONFIG.json", "titan_runtime.py", "frozen_selected.py", "exec_pace_runtime.py")
    missing_members = [name for name in required_members if name not in archive_member_sha256]
    if missing_members:
        raise ValueError("current_archive_missing_required_members:" + ",".join(missing_members))
    runtime, opponent_receipts = {}, {}
    for name in opponents:
        runtime[name] = args.output / "opponents" / name
        opponent_receipts[name] = bridge.prepare(name, root, runtime[name])

    run = {
        "schema": SCHEMA,
        "claim_main": CURRENT_MAIN_AT_CLAIM,
        "current_archive": {"sha256": CURRENT_ARCHIVE_SHA256, "bytes": CURRENT_ARCHIVE_BYTES},
        "source_pins": pins,
        "evaluation_sources_sha256": {
            "paired.py": digest(here / "paired.py"),
            "candidate_entry.py": digest(here / "candidate_entry.py"),
        },
        "archive_members_sha256": archive_member_sha256,
        "harness": harness,
        "engine": engine_hashes,
        "opponents": opponent_receipts,
        "opponent_names": opponents,
        "seeds": seeds,
        "seats": seats,
        "expected_cells": len(opponents) * len(seeds) * len(seats),
        "method": "Fresh full official-interpreter games; exact same baseline archive, opponent, seed, and seat per pair. Candidate arm adds only published source-pinned certificate authority + alternate-feed transform. Not hosted Kaggle rating.",
    }
    write_json(args.output / "run.json", run)
    cells = []
    for opponent in opponents:
        for seed in seeds:
            for seat in seats:
                cell_id = f"{opponent}-s{seed}-p{seat}"
                games, trackers, candidate_metrics = {}, {}, None
                for label in ("baseline", "candidate"):
                    with tempfile.TemporaryDirectory(prefix=cell_id + "-" + label + "-", dir=args.output) as td:
                        directory = Path(td)
                        payload = directory / "payload"
                        helper.extract_members(baseline_members, payload)
                        entry = payload / "main.py"
                        if label == "candidate":
                            (payload / "candidate_entry.py").write_bytes((here / "candidate_entry.py").read_bytes())
                            safe_copy_files(source, payload / "candidates/v5/animal-cadence", ("alternate_feed.py", "certificate_builder.py"))
                            sibling = directory / "cloud-opponent-league/lark-responsive"
                            sibling.mkdir(parents=True)
                            for name in ("pressure_priority.py", "sell_priority.py"):
                                (sibling / name).write_bytes((payload / name).read_bytes())
                            entry = payload / "candidate_entry.py"
                        adapter = directory / "adapter.py"
                        pack.write_adapter(adapter, entry)
                        rival = runtime[opponent] / "adapter.py"
                        specs = [str(adapter), str(rival)] if seat == 0 else [str(rival), str(adapter)]
                        engine, _ = evaluator.get_engine(args.engine_dir, loader)
                        original = engine.interpreter
                        tracker = {"last": {}, "animal_escapes": [], "care_bonus_by_step": [], "animal_count_by_step": []}
                        def instrumented(state, env, _original=original, _tracker=tracker):
                            result = _original(state, env)
                            step_value = int(state[0].observation.get("step", -1)) if state else -1
                            observe_animals(state, seat, _tracker, step_value)
                            return result
                        engine.interpreter = instrumented
                        game = evaluator.play(engine, specs, args.engine_dir, loader, seed, seat, 20260912, 1.25, 10.0, 900.0)
                        trackers[label] = tracker
                        if label == "candidate":
                            metric_path = payload / "animal-cadence-eval-metrics.json"
                            if metric_path.is_file():
                                candidate_metrics = json.loads(metric_path.read_text(encoding="utf-8"))
                    canonical = canonical_game(game)
                    games[label] = canonical
                    write_json(args.output / f"{cell_id}-{label}.json", canonical)
                    print(json.dumps({"cell_id": cell_id, "arm": label, "status": canonical.get("status"), "steps": canonical.get("steps"), "scores": canonical.get("scores")}), flush=True)

                bm, cm = margin(games["baseline"], seat), margin(games["candidate"], seat)
                bs, cs = own_score(games["baseline"], seat), own_score(games["candidate"], seat)
                base_care = dict(trackers["baseline"]["care_bonus_by_step"])
                cand_care = dict(trackers["candidate"]["care_bonus_by_step"])
                common = sorted(set(base_care) & set(cand_care))
                care_divergence = sum(base_care[s] != cand_care[s] for s in common)
                cell = {
                    "cell_id": cell_id, "opponent": opponent, "seed": seed, "seat": seat,
                    "baseline": games["baseline"], "candidate": games["candidate"],
                    "baseline_margin": bm, "candidate_margin": cm,
                    "margin_delta": (cm - bm) if bm is not None and cm is not None else None,
                    "baseline_own_score": bs, "candidate_own_score": cs,
                    "own_score_delta": (cs - bs) if bs is not None and cs is not None else None,
                    "baseline_outcome": outcome(bm), "candidate_outcome": outcome(cm),
                    "complete_pair": bm is not None and cm is not None,
                    "candidate_metrics": candidate_metrics or {},
                    "baseline_animal_escapes": trackers["baseline"]["animal_escapes"],
                    "candidate_animal_escapes": trackers["candidate"]["animal_escapes"],
                    "animal_escape_delta": len(trackers["candidate"]["animal_escapes"]) - len(trackers["baseline"]["animal_escapes"]),
                    "care_bonus_divergence_steps": care_divergence,
                }
                cells.append(cell)
                report = {"schema": SCHEMA, "run": run, "cells": cells, "summary": summarize(cells)}
                write_json(args.output / "report.partial.json", report)
                print("PAIR " + json.dumps({k: v for k, v in cell.items() if k not in ("baseline", "candidate")}, sort_keys=True), flush=True)

    report = {"schema": SCHEMA, "run": run, "cells": cells, "summary": summarize(cells)}
    validate_report(report)
    write_json(args.output / "RESULTS.json", report)
    receipt = {
        "schema": "titan-v5/animal-cadence/matched-eval-receipt/v1",
        "result_sha256": digest(args.output / "RESULTS.json"),
        "run_sha256": digest(args.output / "run.json"),
        "summary": report["summary"],
    }
    write_json(args.output / "RECEIPT.json", receipt)
    print("RECEIPT " + json.dumps(receipt, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
