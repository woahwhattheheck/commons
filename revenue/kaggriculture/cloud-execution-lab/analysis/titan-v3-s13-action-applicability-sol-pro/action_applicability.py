#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Audit S13 replay-route applicability against exact pinned prestates.

The unit certificate binds every input read by the pinned unit executor. The
market certificate binds the tested player's own/public prestate, but cannot
bind the rival's simultaneous hidden market queue.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import types
from typing import Any, Mapping, Sequence

SCHEMA = "titan-v3-s13-action-applicability-audit/v1"
CERT_SCHEMA = "titan-v3-s13-action-prestate-certificate/v1"
PIN_SCHEMA = "titan-v3-s13-replay-pins/v1"
SHA256_RE = re.compile(r"[0-9a-f]{64}")
PASS = ["PASS"]


class AuditError(RuntimeError):
    pass


def strict_json(data: bytes, label: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise AuditError(f"{label}: duplicate JSON key {key!r}")
            out[key] = value
        return out

    def reject(value: str) -> Any:
        raise AuditError(f"{label}: non-finite JSON constant {value}")

    try:
        return json.loads(data.decode(), object_pairs_hook=pairs, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label}: invalid UTF-8 JSON: {exc}") from exc


strict_json_bytes = strict_json


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise AuditError(f"value is not canonical JSON: {exc}") from exc


def sha(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def obj(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AuditError(f"{label}: expected object")
    return value


def arr(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AuditError(f"{label}: expected array")
    return value


def exact_int(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise AuditError(f"{label}: expected integer >= {minimum}")
    return value


def finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise AuditError(f"{label}: expected finite number")
    return float(value)


def structural_signature(observation: Mapping[str, Any], seat: int) -> dict[str, int]:
    farms = arr(observation.get("farms"), "observation.farms")
    if not 0 <= seat < len(farms):
        raise AuditError("seat is outside observation.farms")
    farm = obj(farms[seat], f"observation.farms[{seat}]")
    return {"hands": len(arr(farm.get("hands"), "farm.hands")),
            "quadrants": len(arr(farm.get("unlocked_quadrants"), "farm.unlocked_quadrants"))}


def config_projection(configuration: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    defaults = {"boardSize": 10, "turnsPerDay": 24, "shedCapacity": 100,
                "maxMarketOrdersPerTurn": 10, "farmHandCostMult": 1}
    for key, default in defaults.items():
        out[key] = exact_int(configuration.get(key, default), f"configuration.{key}",
                             0 if key == "farmHandCostMult" else 1)
    params = configuration.get("marketParams")
    if params is not None and not isinstance(params, Mapping):
        raise AuditError("configuration.marketParams: expected object or null")
    out["marketParams"] = params
    return out


def exact_action(value: Any) -> dict[str, Any]:
    action = obj(value, "action")
    if set(action) != {"farmer", "hands", "market"}:
        raise AuditError(f"action keys drift: {sorted(action)}")
    farmer, hands, market = action["farmer"], action["hands"], action["market"]
    if not isinstance(farmer, list) or not farmer or not isinstance(farmer[0], str):
        raise AuditError("action.farmer is malformed")
    if not isinstance(hands, list) or any(not isinstance(row, list) or not row or
                                          not isinstance(row[0], str) for row in hands):
        raise AuditError("action.hands is malformed")
    if not isinstance(market, list) or any(row != [] and
                                           (not isinstance(row, list) or not row or
                                            not isinstance(row[0], str)) for row in market):
        raise AuditError("action.market is malformed")
    return strict_json(canonical(action), "action")


def prestate_certificate(observation: Mapping[str, Any], configuration: Mapping[str, Any],
                         action: Mapping[str, Any], *, seat: int, mode: str) -> dict[str, Any]:
    if mode not in {"units", "market", "full"}:
        raise AuditError(f"unsupported mode {mode!r}")
    farms = arr(observation.get("farms"), "observation.farms")
    if not 0 <= seat < len(farms):
        raise AuditError("seat is outside observation.farms")
    if type(observation.get("player", seat)) is not int or observation.get("player", seat) != seat:
        raise AuditError(f"observation.player {observation.get('player')!r} does not bind seat {seat}")
    farm = obj(farms[seat], "player farm")
    private = obj(observation.get("private"), "observation.private")
    cfg = config_projection(obj(configuration, "configuration"))
    action = exact_action(action)
    domains: dict[str, str] = {}
    if mode in {"units", "full"}:
        domains["units"] = sha({
            "day": exact_int(observation.get("day"), "observation.day"),
            "farm": farm,
            "private": private,
            "configuration": {key: cfg[key] for key in
                              ("boardSize", "turnsPerDay", "shedCapacity")},
            "action": {"farmer": action["farmer"], "hands": action["hands"]},
        })
    if mode in {"market", "full"}:
        domains["market"] = sha({
            "farm": {key: farm.get(key) for key in
                     ("money", "hands", "hires_today", "unlocked_quadrants", "tiles", "farmer")},
            "private": private,
            "market": obj(observation.get("market"), "observation.market"),
            "configuration": {key: cfg[key] for key in
                              ("boardSize", "shedCapacity", "maxMarketOrdersPerTurn",
                               "farmHandCostMult", "marketParams")},
            "action": action["market"],
        })
    return {"schema": CERT_SCHEMA, "mode": mode, "seat": seat,
            "action_sha256": sha(action), "domains": domains}


def certificate_matches(expected: Mapping[str, Any], observation: Mapping[str, Any],
                        configuration: Mapping[str, Any], action: Mapping[str, Any], *, seat: int) -> bool:
    mode = obj(expected, "expected certificate").get("mode")
    if not isinstance(mode, str):
        raise AuditError("expected certificate has no mode")
    return canonical(expected) == canonical(prestate_certificate(
        observation, configuration, action, seat=seat, mode=mode))


@dataclass(frozen=True)
class RouteRow:
    episode: str
    seat: int
    team: str
    frame: int
    step: int
    signature: tuple[int, int]
    action: Mapping[str, Any]
    observation: Mapping[str, Any]
    configuration: Mapping[str, Any]

    @property
    def route_id(self) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", self.team.lower()).strip("-") or "team"
        return f"{slug}-e{self.episode}-s{self.seat}"


def load_pins(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    value = obj(strict_json(data, str(path)), str(path))
    if value.get("schema") != PIN_SCHEMA:
        raise AuditError(f"{path}: source-pin schema drift")
    sources: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(arr(value.get("sources"), f"{path}.sources")):
        row = obj(raw, f"source[{index}]")
        episode = str(row.get("episode"))
        digest = row.get("json_sha256")
        if not episode.isdigit() or not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise AuditError(f"source[{index}]: invalid identity")
        if episode in sources:
            raise AuditError(f"{path}: duplicate episode {episode}")
        sources[episode] = dict(row)
    candidates = arr(value.get("expected_candidates"), f"{path}.expected_candidates")
    if any(not isinstance(candidate, str) for candidate in candidates):
        raise AuditError(f"{path}: invalid expected candidate")
    return {"sha256": hashlib.sha256(data).hexdigest(), "sources": sources,
            "expected_candidates": candidates}


def candidate_parts(candidate: str) -> tuple[str, int]:
    match = re.fullmatch(r".+-e([0-9]+)-s([0-9]+)", candidate)
    if not match:
        raise AuditError(f"invalid candidate id {candidate!r}")
    return match.group(1), int(match.group(2))


def load_route_rows(replay_dir: Path, pins: Mapping[str, Any], start_step: int = 24) -> list[RouteRow]:
    rows: list[RouteRow] = []
    sources = obj(pins.get("sources"), "pins.sources")
    for candidate in arr(pins.get("expected_candidates"), "pins.expected_candidates"):
        episode, seat = candidate_parts(candidate)
        source = obj(sources.get(episode), f"pin episode {episode}")
        path = replay_dir / f"episode_{episode}.json"
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != source.get("json_sha256") or len(data) != source.get("json_bytes"):
            raise AuditError(f"episode {episode}: source identity mismatch")
        replay = obj(strict_json(data, str(path)), str(path))
        steps = arr(replay.get("steps"), f"episode {episode}.steps")
        if len(steps) != source.get("frames"):
            raise AuditError(f"episode {episode}: frame-count mismatch")
        info = obj(replay.get("info"), f"episode {episode}.info")
        teams = arr(info.get("TeamNames"), "TeamNames")
        if teams != source.get("teams"):
            raise AuditError(f"episode {episode}: TeamNames mismatch")
        rewards = [finite(value, f"episode {episode}.reward") for value in
                   arr(replay.get("rewards"), f"episode {episode}.rewards")]
        expected_rewards = [finite(value, f"pin {episode}.reward") for value in
                            arr(source.get("rewards"), f"pin {episode}.rewards")]
        if rewards != expected_rewards or not 0 <= seat < len(teams):
            raise AuditError(f"episode {episode}: reward/seat mismatch")
        configuration = obj(replay.get("configuration"), f"episode {episode}.configuration")
        for frame in range(len(steps) - 1):
            before = arr(steps[frame], "before frame")[seat]
            after = arr(steps[frame + 1], "after frame")[seat]
            action = obj(after, "after row").get("action")
            if action is None:
                continue
            observation = obj(obj(before, "before row").get("observation"), "observation")
            step = exact_int(observation.get("step", frame), "observation.step")
            if step < start_step:
                continue
            signature = structural_signature(observation, seat)
            rows.append(RouteRow(episode, seat, teams[seat], frame, step,
                                 (signature["hands"], signature["quadrants"]),
                                 exact_action(action), observation, configuration))
    return rows


def load_pinned_engine(path: Path, expected_sha256: str) -> Any:
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected_sha256:
        raise AuditError(f"engine SHA-256 mismatch: expected {expected_sha256}, got {actual}")
    package, utils = types.ModuleType("kaggle_environments"), types.ModuleType("kaggle_environments.utils")
    utils.resolve_episode_seed = lambda *args, **kwargs: 0
    package.utils = utils
    old = (sys.modules.get("kaggle_environments"), sys.modules.get("kaggle_environments.utils"))
    sys.modules.update({"kaggle_environments": package, "kaggle_environments.utils": utils})
    try:
        spec = importlib.util.spec_from_file_location(f"s13_engine_{actual[:16]}", path)
        if spec is None or spec.loader is None:
            raise AuditError("cannot load pinned engine")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for name, prior in zip(("kaggle_environments", "kaggle_environments.utils"), old):
            if prior is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = prior


def unit_actions(action: Mapping[str, Any]) -> list[list[Any]]:
    return [list(action["farmer"]), *[list(row) for row in action["hands"]]]


def unit_active(engine: Any, row: RouteRow, actor: int, action: Sequence[Any]) -> bool:
    farm = copy.deepcopy(arr(row.observation.get("farms"), "farms")[row.seat])
    private = copy.deepcopy(obj(row.observation.get("private"), "private"))
    before = canonical({"farm": farm, "private": private})
    cfg = config_projection(row.configuration)
    engine._apply_unit_action(farm, private, actor, list(action), cfg["boardSize"],
                              row.observation["day"], cfg["turnsPerDay"], cfg["shedCapacity"])
    return before != canonical({"farm": farm, "private": private})


def row_ref(row: RouteRow) -> dict[str, Any]:
    return {"candidate": row.route_id, "episode": row.episode, "seat": row.seat,
            "team": row.team, "frame": row.frame, "step": row.step,
            "signature": {"hands": row.signature[0], "quadrants": row.signature[1]},
            "action_sha256": sha(row.action)}


def audit_rows(rows: Sequence[RouteRow], engine: Any) -> dict[str, Any]:
    groups: dict[tuple[int, tuple[int, int]], list[RouteRow]] = {}
    for row in rows:
        groups.setdefault((row.step, row.signature), []).append(row)
    collision_groups = disagreements = comparisons = 0
    witnesses: list[dict[str, Any]] = []
    certificate_failures = 0
    for group in groups.values():
        collision_groups += len({sha(row.action) for row in group}) > 1
        for source in group:
            for target in group:
                if source is target or canonical(source.action) == canonical(target.action):
                    continue
                disagreements += 1
                source_units, target_units = unit_actions(source.action), unit_actions(target.action)
                if len(source_units) != len(target_units):
                    raise AuditError("same signature produced different actor counts")
                for actor, (source_action, target_action) in enumerate(zip(source_units, target_units)):
                    if source_action == PASS or source_action == target_action:
                        continue
                    comparisons += 1
                    if (unit_active(engine, source, actor, source_action) and
                            not unit_active(engine, target, actor, source_action) and
                            unit_active(engine, target, actor, target_action)):
                        source_cert = prestate_certificate(source.observation, source.configuration,
                                                           source.action, seat=source.seat, mode="units")
                        target_cert = prestate_certificate(target.observation, target.configuration,
                                                           source.action, seat=target.seat, mode="units")
                        witness = {"source": row_ref(source), "target": row_ref(target),
                                   "actor_index": actor, "source_component": source_action,
                                   "target_component": target_action,
                                   "source_certificate_sha256": sha(source_cert),
                                   "target_certificate_sha256": sha(target_cert)}
                        witnesses.append(witness)
                        certificate_failures += canonical(source_cert) == canonical(target_cert)
    witnesses.sort(key=lambda row: (row["source"]["step"], row["source"]["candidate"],
                                    row["target"]["candidate"], row["actor_index"],
                                    canonical(row["source_component"])))
    by_op: dict[str, int] = {}
    by_pair: dict[str, int] = {}
    steps: set[int] = set()
    for witness in witnesses:
        op = witness["source_component"][0]
        pair = f"{witness['source']['candidate']} -> {witness['target']['candidate']}"
        by_op[op] = by_op.get(op, 0) + 1
        by_pair[pair] = by_pair.get(pair, 0) + 1
        steps.add(witness["source"]["step"])
    ranked_pairs = [{"pair": pair, "witnesses": count} for pair, count in
                    sorted(by_pair.items(), key=lambda item: (-item[1], item[0]))[:10]]
    return {
        "route_rows": len(rows), "signature_groups": len(groups),
        "multi_route_signature_groups": sum(len(group) > 1 for group in groups.values()),
        "bundle_collision_groups": collision_groups,
        "ordered_bundle_disagreements": disagreements,
        "unit_component_comparisons": comparisons,
        "unit_false_applicability_witnesses": len(witnesses),
        "unit_false_applicability_steps": len(steps),
        "unit_false_applicability_by_source_op": dict(sorted(by_op.items())),
        "largest_route_pair_counts": ranked_pairs,
        "certificate_failures": certificate_failures,
        "first_witness": witnesses[0] if witnesses else None,
        "sample_witnesses": witnesses[:8],
        "witnesses_sha256": sha(witnesses),
    }


def build_receipt(replay_dir: Path, pins_path: Path, engine_path: Path,
                  engine_sha256: str) -> dict[str, Any]:
    pins = load_pins(pins_path)
    audit = audit_rows(load_route_rows(replay_dir, pins),
                       load_pinned_engine(engine_path, engine_sha256))
    if audit["unit_false_applicability_witnesses"] <= 0 or audit["certificate_failures"]:
        raise AuditError("corpus/certificate predecessor did not close")
    return {"schema": SCHEMA, "source_pins_sha256": pins["sha256"],
            "engine": {"path": engine_path.name, "sha256": engine_sha256,
                       "oracle": "_apply_unit_action"},
            "selected_candidates": pins["expected_candidates"], "audit": audit,
            "disposition": {
                "current_structural_signature": "REJECT_AS_ACTION_APPLICABILITY_CERTIFICATE",
                "unit_prestate_certificate": "PASS_ON_PINNED_SOURCE_COLLISION_CENSUS",
                "market_limitation": "HIDDEN_RIVAL_SIMULTANEOUS_QUEUE_NOT_BOUND"}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay-dir", type=Path, required=True)
    parser.add_argument("--source-pins", type=Path, required=True)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--engine-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not SHA256_RE.fullmatch(args.engine_sha256):
        raise AuditError("--engine-sha256 must be lowercase SHA-256")
    receipt = build_receipt(args.replay_dir, args.source_pins, args.engine, args.engine_sha256)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output),
                      "receipt_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
                      **receipt["audit"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AuditError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
