#!/usr/bin/env python3
"""Run exact current TITAN against frozen T09 intact and responsive opponents.

The result is checkpointed after every game.  A repeated invocation needs
``--resume`` and verifies all retained source and trace identities before it
skips a completed cell.  This makes an outer command interruption resumable
without silently rerunning or discarding completed games.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import time
from typing import Any

OPPONENTS = (
    ("arlene", "arlene", ""),
    ("apex", "apex", ""),
    ("arlene_sale_cadence", "arlene", "sale_cadence"),
    ("apex_crop_demand", "apex", "crop_demand"),
    ("arlene_labor_cadence", "arlene", "labor_cadence"),
)
EXPECTED_ARCHIVE = "87d7b8bf7c4e9467f4b6b46887abe2eb03735c42453cdbf4f2cac12c5962acc7"
EXPECTED_VARIANT_BLOB = "374a23ffb3cf6cc1c67571df74fde9f84467e832"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    return value


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def common_identity(args: argparse.Namespace, evaluator, candidate: str,
                    base_specs: dict[str, str], engine_hashes: dict[str, str]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "method": (
            "Repository cloud-eval Actor/play with the pinned official interpreter and exact "
            "T09 observation-only variant actor; fresh actor processes and complete ordered "
            "joint-action capture. Local cloud development evidence, not hosted rating."
        ),
        "seed": args.seed,
        "archive": {
            "path": args.archive.name,
            "bytes": args.archive.stat().st_size,
            "sha256": sha256(args.archive),
        },
        "candidate": evaluator.fingerprint(candidate),
        "opponent_sources": {
            "arlene": evaluator.fingerprint(base_specs["arlene"]),
            "apex": {
                **evaluator.fingerprint(base_specs["apex"]),
                "agent_so_sha256": sha256(args.apex.with_name("agent.so")),
                "policy_cpp_sha256": sha256(args.apex.parent / "source" / "policy.cpp"),
                "tape_inc_sha256": sha256(args.apex.parent / "source" / "tape.inc"),
                "bridge_sha256": sha256(args.apex.parent / "submission_bridge.cpp"),
            },
        },
        "variants": {
            "path": args.variants.name,
            "sha256": sha256(args.variants),
            "git_blob": git_blob_sha1(args.variants),
            "names": ["sale_cadence", "crop_demand", "labor_cadence"],
        },
        "engine_ref": evaluator.ENGINE_REF,
        "engine_sha256": engine_hashes,
        "evaluator_sha256": sha256(args.evaluator),
        "loader_sha256": sha256(args.loader),
        "runner_sha256": sha256(Path(__file__)),
        "python": sys.version,
        "platform": platform.platform(),
        "limits": {
            "action_rpc_seconds": args.action_timeout,
            "startup_seconds": args.startup_timeout,
            "game_seconds_total": args.game_timeout,
            "remaining_overage_time": 0,
        },
    }


def validate_retained(document: dict[str, Any], identity: dict[str, Any], output: Path) -> None:
    for key in (
        "schema_version", "seed", "archive", "candidate", "opponent_sources", "variants",
        "engine_ref", "engine_sha256", "evaluator_sha256", "loader_sha256", "runner_sha256",
        "python", "platform", "limits",
    ):
        if document.get(key) != identity.get(key):
            raise ValueError(f"resume identity changed: {key}")
    seen: set[tuple[str, int]] = set()
    for game in document.get("games", []):
        key = (str(game.get("opponent")), int(game.get("candidate_seat")))
        if key in seen:
            raise ValueError(f"duplicate retained game: {key}")
        seen.add(key)
        trace = output / game["action_trace"]["path"]
        if not trace.is_file() or sha256(trace) != game["action_trace"]["sha256"]:
            raise ValueError(f"retained trace changed: {trace}")


def summarize(games: list[dict[str, Any]]) -> dict[str, Any]:
    complete = [game for game in games if game.get("status") == "complete"]
    by_opponent: dict[str, Any] = {}
    for name, base_name, variant in OPPONENTS:
        rows = [game for game in complete if game["opponent"] == name]
        by_opponent[name] = {
            "base_opponent": base_name,
            "variant": variant or "intact",
            "games": len(rows),
            "wins": sum(game["verdict"] == "W" for game in rows),
            "ties": sum(game["verdict"] == "T" for game in rows),
            "losses": sum(game["verdict"] == "L" for game in rows),
            "mean_candidate_cash": statistics.mean(game["candidate_cash"] for game in rows) if rows else None,
            "mean_rival_cash": statistics.mean(game["rival_cash"] for game in rows) if rows else None,
            "mean_margin": statistics.mean(game["margin"] for game in rows) if rows else None,
            "changed_turns": sorted({game["opponent_changed_turns"] for game in rows}),
        }
    paired: dict[str, Any] = {}
    for variant_name, intact_name in (
        ("arlene_sale_cadence", "arlene"),
        ("apex_crop_demand", "apex"),
        ("arlene_labor_cadence", "arlene"),
    ):
        effects = []
        for seat in (0, 1):
            variant_game = next((g for g in complete if g["opponent"] == variant_name and g["candidate_seat"] == seat), None)
            intact_game = next((g for g in complete if g["opponent"] == intact_name and g["candidate_seat"] == seat), None)
            if variant_game is None or intact_game is None:
                continue
            effects.append({
                "candidate_seat": seat,
                "candidate_cash_delta": variant_game["candidate_cash"] - intact_game["candidate_cash"],
                "rival_cash_delta": variant_game["rival_cash"] - intact_game["rival_cash"],
                "margin_delta": variant_game["margin"] - intact_game["margin"],
                "outcome": intact_game["verdict"] + "->" + variant_game["verdict"],
                "changed_turns": variant_game["opponent_changed_turns"],
            })
        paired[variant_name] = effects
    return {
        "independent_seeds": 1,
        "mirrored_seat_records": len(games),
        "scheduled": len(OPPONENTS) * 2,
        "completed": len(complete),
        "failed": len(games) - len(complete),
        "wins": sum(game.get("verdict") == "W" for game in complete),
        "ties": sum(game.get("verdict") == "T" for game in complete),
        "losses": sum(game.get("verdict") == "L" for game in complete),
        "by_opponent": by_opponent,
        "paired_variant_effects": paired,
        "max_candidate_call_seconds": max(
            (game["actors"][game["candidate_seat"]]["max_call_seconds"] for game in complete),
            default=None,
        ),
        "max_candidate_rpc_seconds": max(
            (game["actors"][game["candidate_seat"]]["max_rpc_seconds"] for game in complete),
            default=None,
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluator", type=Path, required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--arlene", type=Path, required=True)
    parser.add_argument("--apex", type=Path, required=True)
    parser.add_argument("--variants", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--action-timeout", type=float, default=1.0)
    parser.add_argument("--startup-timeout", type=float, default=10.0)
    parser.add_argument("--game-timeout", type=float, default=120.0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    for path in (args.evaluator, args.loader, args.candidate, args.arlene, args.apex,
                 args.variants, args.archive):
        path.resolve(strict=True)
    args.engine_dir.resolve(strict=True)
    if sha256(args.archive) != EXPECTED_ARCHIVE:
        raise SystemExit("canonical archive digest mismatch")
    if git_blob_sha1(args.variants) != EXPECTED_VARIANT_BLOB:
        raise SystemExit("T09 variant source Git blob mismatch")

    partial_path = args.output_dir / "PARTIAL.json"
    final_path = args.output_dir / "RESULTS.json"
    if final_path.exists():
        raise FileExistsError(f"completed result already exists: {final_path}")
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.resume:
        raise FileExistsError("output directory is not empty; use --resume only for its matching PARTIAL.json")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "traces").mkdir(exist_ok=True)

    evaluator = load_module(args.evaluator.resolve(), "astra_responsive_eval")
    variants = load_module(args.variants.resolve(), "astra_responsive_variants")
    engine, engine_hashes = evaluator.get_engine(args.engine_dir.resolve(), args.loader.resolve())
    evaluator.Actor = variants.actor_class(evaluator.Actor, engine.SHOPS)
    candidate = evaluator.resolve_spec(str(args.candidate.resolve()))
    base_specs = {
        "arlene": evaluator.resolve_spec(str(args.arlene.resolve())),
        "apex": evaluator.resolve_spec(str(args.apex.resolve())),
    }
    identity = common_identity(args, evaluator, candidate, base_specs, engine_hashes)
    if args.resume:
        if not partial_path.is_file():
            raise FileNotFoundError("--resume requires PARTIAL.json")
        document = json.loads(partial_path.read_text())
        validate_retained(document, identity, args.output_dir)
    else:
        document = {**identity, "complete": False, "games": []}
        atomic_json(partial_path, document)

    completed = {(game["opponent"], int(game["candidate_seat"])) for game in document["games"]}
    for opponent_name, base_name, variant in OPPONENTS:
        rival_spec = base_specs[base_name] + ("|league=" + variant if variant else "")
        for candidate_seat in (0, 1):
            key = (opponent_name, candidate_seat)
            if key in completed:
                print(json.dumps({"opponent": opponent_name, "candidate_seat": candidate_seat, "status": "retained"}), flush=True)
                continue
            events: list[dict[str, Any]] = []
            original_interpreter = engine.interpreter

            def capture_interpreter(state, env):
                has_actions = any(bool(getattr(item, "action", None)) for item in state)
                if has_actions:
                    step = int(state[0].observation.get("step", len(events)))
                    before = [float(state[0].observation.farms[index]["money"]) for index in range(2)]
                    actions = [plain(copy.deepcopy(item.action)) for item in state]
                result = original_interpreter(state, env)
                if has_actions:
                    after = [float(state[0].observation.farms[index]["money"]) for index in range(2)]
                    events.append({
                        "step": step,
                        "actions": actions,
                        "bank_before": before,
                        "bank_after": after,
                        "status_after": [str(item.status) for item in state],
                        "reward_after": [plain(item.reward) for item in state],
                    })
                return result

            engine.interpreter = capture_interpreter
            specs = [candidate, rival_spec] if candidate_seat == 0 else [rival_spec, candidate]
            started = time.perf_counter()
            try:
                game = evaluator.play(
                    engine, specs, args.engine_dir.resolve(), args.loader.resolve(), args.seed,
                    candidate_seat, rng_seed=20260907,
                    action_timeout=args.action_timeout,
                    startup_timeout=args.startup_timeout,
                    game_timeout=args.game_timeout,
                )
            finally:
                engine.interpreter = original_interpreter
            game["opponent"] = opponent_name
            game["base_opponent"] = base_name
            game["variant"] = variant or "intact"
            game["capture_wall_seconds"] = time.perf_counter() - started
            rival_actor = game.get("actors", [None, None])[1 - candidate_seat]
            game["opponent_changed_turns"] = (
                rival_actor.get("league_changed_turns") if isinstance(rival_actor, dict) else None
            )
            trace_name = f"actions-seed{args.seed}-{opponent_name}-seat{candidate_seat}.jsonl.gz"
            trace_path = args.output_dir / "traces" / trace_name
            with gzip.open(trace_path, "wt", encoding="utf-8", newline="\n", compresslevel=9) as handle:
                for event in events:
                    handle.write(json.dumps(event, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
            game["action_trace"] = {
                "path": "traces/" + trace_name,
                "events": len(events),
                "bytes": trace_path.stat().st_size,
                "sha256": sha256(trace_path),
            }
            if game.get("status") == "complete":
                own = float(game["scores"][candidate_seat])
                rival = float(game["scores"][1 - candidate_seat])
                game.update(
                    candidate_cash=own,
                    rival_cash=rival,
                    margin=own - rival,
                    verdict="W" if own > rival else "L" if own < rival else "T",
                )
            document["games"].append(game)
            document["summary"] = summarize(document["games"])
            atomic_json(partial_path, document)
            print(json.dumps({
                "opponent": opponent_name,
                "candidate_seat": candidate_seat,
                "status": game.get("status"),
                "scores": game.get("scores"),
                "verdict": game.get("verdict"),
                "margin": game.get("margin"),
                "changed_turns": game.get("opponent_changed_turns"),
                "failure": game.get("failure"),
            }, sort_keys=True), flush=True)

    document["summary"] = summarize(document["games"])
    document["complete"] = len(document["games"]) == 10
    atomic_json(final_path, document)
    partial_path.unlink()
    print("SUMMARY " + json.dumps(document["summary"], sort_keys=True), flush=True)
    return int(not document["complete"] or document["summary"]["failed"] != 0)


if __name__ == "__main__":
    raise SystemExit(main())
