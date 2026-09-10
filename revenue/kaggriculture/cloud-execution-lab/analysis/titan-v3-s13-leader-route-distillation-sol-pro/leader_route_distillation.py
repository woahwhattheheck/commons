#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compile public Kaggriculture replay actions into deterministic route arms."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping
import zlib

SCHEMA = "titan-v3-s13-leader-route-bank/v1"
MODES = ("post24_full", "post24_market", "post24_units")


class CompileError(RuntimeError):
    pass


def strict_json(data: bytes, label: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise CompileError(f"{label}: duplicate JSON key {key!r}")
            out[key] = value
        return out

    def reject(value: str) -> Any:
        raise CompileError(f"{label}: non-finite JSON constant {value}")

    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CompileError(f"{label}: invalid UTF-8 JSON: {exc}") from exc


def _observation(value: Any, label: str) -> Mapping[str, Any]:
    if isinstance(value, str):
        value = strict_json(value.encode("utf-8"), label)
    if not isinstance(value, Mapping):
        raise CompileError(f"{label}: observation is not an object")
    return value


def _team_names(replay: Mapping[str, Any], seats: int) -> list[str]:
    info = replay.get("info")
    raw = info.get("TeamNames") if isinstance(info, Mapping) else None
    if isinstance(raw, Mapping):
        names = [str(raw.get(str(i), raw.get(i, f"seat-{i}"))) for i in range(seats)]
    elif isinstance(raw, list) and len(raw) >= seats:
        names = [str(raw[i]) for i in range(seats)]
    else:
        names = [f"seat-{i}" for i in range(seats)]
    return names


def _reward(replay: Mapping[str, Any], steps: list[Any], seat: int) -> float:
    for frame in reversed(steps):
        if not isinstance(frame, list) or seat >= len(frame) or not isinstance(frame[seat], Mapping):
            continue
        value = frame[seat].get("reward")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    rewards = replay.get("rewards")
    if isinstance(rewards, list) and seat < len(rewards) and isinstance(rewards[seat], (int, float)):
        return float(rewards[seat])
    raise CompileError(f"seat {seat}: no final numeric reward")


def _signature(obs: Mapping[str, Any], seat: int) -> dict[str, int]:
    player = obs.get("player", seat)
    farms = obs.get("farms")
    if type(player) is not int or not isinstance(farms, list) or player >= len(farms):
        raise CompileError("observation lacks player farm")
    farm = farms[player]
    if not isinstance(farm, Mapping):
        raise CompileError("player farm is not an object")
    hands = farm.get("hands", [])
    quadrants = farm.get("unlocked_quadrants", [])
    if not isinstance(hands, list) or not isinstance(quadrants, list):
        raise CompileError("farm hands/quadrants are not arrays")
    return {"hands": len(hands), "quadrants": len(quadrants)}


def _canonical_action(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CompileError(f"{label}: action is not an object")
    if set(value) != {"farmer", "hands", "market"}:
        raise CompileError(f"{label}: action keys drift: {sorted(value)}")
    farmer, hands, market = value["farmer"], value["hands"], value["market"]
    if not isinstance(farmer, list) or not farmer or not isinstance(farmer[0], str):
        raise CompileError(f"{label}: malformed farmer action")
    if not isinstance(hands, list) or not isinstance(market, list):
        raise CompileError(f"{label}: hands/market are not arrays")
    for row in hands:
        if not isinstance(row, list) or not row or not isinstance(row[0], str):
            raise CompileError(f"{label}: malformed hand action")
    for row in market:
        if row != [] and (not isinstance(row, list) or not row or not isinstance(row[0], str)):
            raise CompileError(f"{label}: malformed market action")
    return strict_json(json.dumps(value, separators=(",", ":"), allow_nan=False).encode(), label)


def extract_seat(replay: Mapping[str, Any], *, episode: str, seat: int, source_sha256: str) -> dict[str, Any]:
    raw_steps = replay.get("steps")
    if not isinstance(raw_steps, list) or len(raw_steps) < 2:
        raise CompileError(f"episode {episode}: missing replay steps")
    seats = len(raw_steps[0]) if isinstance(raw_steps[0], list) else 0
    if seats < 2 or seat >= seats:
        raise CompileError(f"episode {episode}: invalid seat {seat}")
    names = _team_names(replay, seats)

    # Kaggle replay frames retain the action that produced the current frame.
    # Pair frame i+1's action with frame i's pre-action observation.
    tape: dict[str, Any] = {}
    for i in range(len(raw_steps) - 1):
        before_frame, after_frame = raw_steps[i], raw_steps[i + 1]
        if not isinstance(before_frame, list) or not isinstance(after_frame, list):
            raise CompileError(f"episode {episode}: non-array frame {i}")
        if seat >= len(before_frame) or seat >= len(after_frame):
            raise CompileError(f"episode {episode}: seat missing at frame {i}")
        before, after = before_frame[seat], after_frame[seat]
        if not isinstance(before, Mapping) or not isinstance(after, Mapping):
            raise CompileError(f"episode {episode}: malformed seat frame {i}")
        action = after.get("action")
        if action is None:
            continue
        obs = _observation(before.get("observation"), f"episode {episode} frame {i} observation")
        step = obs.get("step", i)
        if type(step) is not int or step < 0:
            raise CompileError(f"episode {episode}: invalid observation step at frame {i}")
        key = str(step)
        if key in tape:
            raise CompileError(f"episode {episode}: duplicate action step {step}")
        tape[key] = {
            "action": _canonical_action(action, f"episode {episode} seat {seat} step {step}"),
            "signature": _signature(obs, seat),
        }
    if len(tape) < 700:
        raise CompileError(f"episode {episode} seat {seat}: only {len(tape)} usable actions")
    return {
        "episode": str(episode),
        "seat": seat,
        "team": names[seat],
        "reward": _reward(replay, raw_steps, seat),
        "source_sha256": source_sha256,
        "actions": len(tape),
        "tape": tape,
    }


def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value or "team"


def compile_bank(paths: Iterable[Path], max_candidates: int) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for path in sorted(paths, key=lambda p: p.name):
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        replay = strict_json(data, path.name)
        if not isinstance(replay, Mapping):
            raise CompileError(f"{path.name}: replay root is not an object")
        episode = "".join(ch for ch in path.stem if ch.isdigit()) or path.stem
        steps = replay.get("steps")
        if not isinstance(steps, list) or not steps or not isinstance(steps[0], list):
            raise CompileError(f"{path.name}: cannot determine seat count")
        seat_count = len(steps[0])
        sources.append({"episode": episode, "path": path.name, "bytes": len(data), "sha256": digest})
        for seat in range(seat_count):
            candidates.append(extract_seat(replay, episode=episode, seat=seat, source_sha256=digest))

    by_team: dict[str, dict[str, Any]] = {}
    for row in candidates:
        key = row["team"].casefold()
        incumbent = by_team.get(key)
        if incumbent is None or (row["reward"], row["episode"], -row["seat"]) > (
            incumbent["reward"], incumbent["episode"], -incumbent["seat"]
        ):
            by_team[key] = row
    chosen = sorted(by_team.values(), key=lambda r: (-r["reward"], r["team"], r["episode"], r["seat"]))[:max_candidates]
    for row in chosen:
        row["candidate_id"] = f"{_slug(row['team'])}-e{row['episode']}-s{row['seat']}"
    return {
        "schema": SCHEMA,
        "selection": "highest final reward per exact TeamNames label",
        "max_candidates": max_candidates,
        "sources": sources,
        "candidates": chosen,
    }


def _py_literal(value: str) -> str:
    return repr(value)


def emit_candidates(bank: Mapping[str, Any], runtime: Path, baseline: Path, output: Path) -> dict[str, Any]:
    if bank.get("schema") != SCHEMA or not isinstance(bank.get("candidates"), list):
        raise CompileError("bank schema drift")
    runtime = runtime.resolve(strict=True)
    baseline = baseline.resolve(strict=True)
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for source in bank["candidates"]:
        if not isinstance(source, Mapping):
            raise CompileError("candidate bank row is not an object")
        tape = source.get("tape")
        if not isinstance(tape, Mapping):
            raise CompileError("candidate bank row has no tape")
        tape_bytes = json.dumps(tape, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        tape_sha = hashlib.sha256(tape_bytes).hexdigest()
        packed = base64.b85encode(zlib.compress(tape_bytes, 9)).decode("ascii")
        for mode in MODES:
            arm_id = f"{source['candidate_id']}--{mode}"
            path = output / f"{arm_id}.py"
            code = f'''# SPDX-License-Identifier: Apache-2.0\n# Generated deterministically by leader_route_distillation.py.\nfrom __future__ import annotations\nimport base64, hashlib, importlib.util, json, zlib\n\nARM_ID = {_py_literal(arm_id)}\nSOURCE_EPISODE = {_py_literal(str(source['episode']))}\nSOURCE_TEAM = {_py_literal(str(source['team']))}\nSOURCE_SEAT = {int(source['seat'])}\nSOURCE_REWARD = {float(source['reward'])!r}\nSOURCE_SHA256 = {_py_literal(str(source['source_sha256']))}\nTAPE_SHA256 = {_py_literal(tape_sha)}\n_PACKED = {_py_literal(packed)}\n\ndef _load(name, path):\n    spec = importlib.util.spec_from_file_location(name, path)\n    if spec is None or spec.loader is None:\n        raise RuntimeError(f"cannot load {{path}}")\n    module = importlib.util.module_from_spec(spec)\n    spec.loader.exec_module(module)\n    return module\n\n_runtime = _load("s13_runtime_" + hashlib.sha256(ARM_ID.encode()).hexdigest()[:12], {_py_literal(str(runtime))})\n_baseline = _load("s13_baseline_" + hashlib.sha256(ARM_ID.encode()).hexdigest()[:12], {_py_literal(str(baseline))})\n_raw = zlib.decompress(base64.b85decode(_PACKED.encode("ascii")))\nif hashlib.sha256(_raw).hexdigest() != TAPE_SHA256:\n    raise RuntimeError("embedded route tape digest mismatch")\n_tape = json.loads(_raw.decode("utf-8"))\n_policy = _runtime.LeaderRoutePolicy(_baseline.agent, _tape, mode={_py_literal(mode)}, start_step=24)\n\ndef agent(obs, configuration=None):\n    return _policy.agent(obs, configuration)\n\ndef diagnostics():\n    return _policy.diagnostics()\n'''
            path.write_text(code, encoding="utf-8", newline="\n")
            rows.append({
                "arm_id": arm_id,
                "path": path.name,
                "mode": mode,
                "source_episode": str(source["episode"]),
                "source_team": str(source["team"]),
                "source_seat": int(source["seat"]),
                "source_reward": float(source["reward"]),
                "source_sha256": str(source["source_sha256"]),
                "tape_sha256": tape_sha,
                "python_sha256": hashlib.sha256(code.encode()).hexdigest(),
            })
    manifest = {
        "schema": "titan-v3-s13-generated-arms/v1",
        "runtime": str(runtime),
        "baseline": str(baseline),
        "arms": rows,
    }
    (output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="command", required=True)
    compile_p = subs.add_parser("compile")
    compile_p.add_argument("--input-dir", type=Path, required=True)
    compile_p.add_argument("--output", type=Path, required=True)
    compile_p.add_argument("--max-candidates", type=int, default=5)
    emit_p = subs.add_parser("emit")
    emit_p.add_argument("--bank", type=Path, required=True)
    emit_p.add_argument("--runtime", type=Path, required=True)
    emit_p.add_argument("--baseline-entry", type=Path, required=True)
    emit_p.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "compile":
        paths = list(args.input_dir.glob("episode_*.json"))
        if not paths:
            raise CompileError("input directory has no episode_*.json files")
        bank = compile_bank(paths, args.max_candidates)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(bank, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"output": str(args.output), "sources": len(bank["sources"]), "candidates": len(bank["candidates"])}, sort_keys=True))
    else:
        bank = strict_json(args.bank.read_bytes(), str(args.bank))
        manifest = emit_candidates(bank, args.runtime, args.baseline_entry, args.output_dir)
        print(json.dumps({"output": str(args.output_dir), "arms": len(manifest["arms"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CompileError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
