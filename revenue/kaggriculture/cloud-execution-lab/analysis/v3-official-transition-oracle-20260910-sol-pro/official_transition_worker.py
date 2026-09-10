#!/usr/bin/env python3
"""Isolated exact-interpreter worker for TITAN's transition oracle.

This file has no project imports.  It loads one source-pinned interpreter under
``python -I -B``, constructs a two-player state from exact engine constructors,
instruments stage boundaries without replacing their semantics, and emits one
canonical JSON receipt.
"""
from __future__ import annotations

import argparse
import copy
import functools
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import stat
import sys
import types
from typing import Any, Iterable

SCHEMA = "titan.v3.official-transition-oracle.worker.v1"
FIXTURE_SCHEMA = "titan.v3.official-transition-fixture.v1"
MAX_INPUT_BYTES = 1_000_000
MAX_EVENTS_PER_STEP = 250_000
EXPECTED_ENGINE_SUFFIX = Path(
    "revenue/kaggriculture/cloud-execution-lab/reference/engine/kaggriculture.py"
)
Json = Any


class WorkerError(RuntimeError):
    pass


class AttrDict(dict):
    """Minimal Kaggle-compatible mapping with attribute access."""

    def __getattr__(self, name: str) -> Json:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Json) -> None:
        self[name] = value


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _unique_object(pairs: Iterable[tuple[str, Json]]) -> dict[str, Json]:
    out: dict[str, Json] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def strict_loads(data: bytes) -> Json:
    return json.loads(
        data.decode("utf-8", errors="strict"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )


def _assert_finite(value: Json, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path}: non-finite number")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path}: non-string key")
            _assert_finite(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_finite(child, f"{path}[{index}]")


def canonical_bytes(value: Json) -> bytes:
    _assert_finite(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def semantic_hash(value: Json) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def bound_file(path: Path, label: str) -> tuple[Path, bytes]:
    raw = path.lstat()
    if stat.S_ISLNK(raw.st_mode):
        raise WorkerError(f"{label} is a symlink")
    resolved = path.resolve(strict=True)
    st = resolved.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
        raise WorkerError(f"{label} must be a single-link regular file")
    return resolved, resolved.read_bytes()


def deep_merge(base: Json, patch: Json, path: str = "$override") -> Json:
    """Deep-copy a fixture patch onto an engine-produced state object."""
    if isinstance(base, dict) and isinstance(patch, dict):
        out = copy.deepcopy(base)
        for key, value in patch.items():
            if not isinstance(key, str):
                raise WorkerError(f"{path}: patch key is not a string")
            if key in out:
                out[key] = deep_merge(out[key], value, f"{path}.{key}")
            else:
                out[key] = copy.deepcopy(value)
        return out
    return copy.deepcopy(patch)


def install_kaggle_stub() -> None:
    """Provide only the import-time symbol used by the pinned interpreter."""
    if "kaggle_environments" in sys.modules:
        raise WorkerError("unexpected preloaded kaggle_environments module")
    package = types.ModuleType("kaggle_environments")
    package.__path__ = []  # type: ignore[attr-defined]
    utils = types.ModuleType("kaggle_environments.utils")

    def resolve_episode_seed(env: Json) -> int:
        info = getattr(env, "info", {})
        return int(info.get("seed", 0)) if isinstance(info, dict) else 0

    utils.resolve_episode_seed = resolve_episode_seed  # type: ignore[attr-defined]
    package.utils = utils  # type: ignore[attr-defined]
    sys.modules["kaggle_environments"] = package
    sys.modules["kaggle_environments.utils"] = utils


def load_engine(path: Path) -> types.ModuleType:
    install_kaggle_stub()
    name = "_titan_pinned_kaggriculture_interpreter"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise WorkerError("cannot create interpreter module specification")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    required = (
        "_new_farm",
        "_new_private",
        "_new_market",
        "_new_town",
        "_refresh_prices",
        "_apply_unit_action",
        "_process_market",
        "_commit_unit",
        "_do_hire",
        "_do_buy_land",
        "_town_consume",
        "_decay_plants",
        "_end_of_day",
        "interpreter",
    )
    missing = [name for name in required if not callable(getattr(module, name, None))]
    if missing:
        raise WorkerError(f"pinned interpreter missing callables: {missing}")
    return module


def default_configuration() -> dict[str, Json]:
    return {
        "boardSize": 10,
        "startingMoney": 3000,
        "turnsPerDay": 24,
        "shedCapacity": 100,
        "maxMarketOrdersPerTurn": 10,
        "farmHandCostMult": 1,
        "townShopSellInterval": 4,
        "townCenterSellInterval": 24,
        "townShopUnlockInterval": 3,
        "weedSpawnChance": 0.0,
        "episodeSteps": 720,
    }


def active_market_prefixes(state: list[Json], config: AttrDict) -> list[Json]:
    limit = max(1, int(config.get("maxMarketOrdersPerTurn", 10)))
    prefixes: list[Json] = []
    for cell in state:
        action = cell.action if isinstance(cell.action, dict) else {}
        market = action.get("market", []) if isinstance(action, dict) else []
        queue = list(market) if isinstance(market, list) else []
        prefixes.append(copy.deepcopy(queue[:limit]))
    return prefixes


def state_snapshot(state: list[Json]) -> dict[str, Json]:
    obs0 = state[0].observation
    return {
        "observed_step": int(obs0.get("step", 0)),
        "day": int(obs0.get("day", 0)),
        "hour": int(obs0.get("hour", 0)),
        "farms": copy.deepcopy(obs0.farms),
        "market": copy.deepcopy(obs0.market),
        "town": copy.deepcopy(obs0.town),
        "privates": [copy.deepcopy(cell.observation.private) for cell in state],
        "status": [str(cell.status) for cell in state],
        "reward": [copy.deepcopy(cell.reward) for cell in state],
    }


def compact_player(state: list[Json], player: int) -> dict[str, Json]:
    farm = state[0].observation.farms[player]
    private = state[player].observation.private
    return {
        "money": farm.get("money", 0),
        "hands": copy.deepcopy(farm.get("hands", [])),
        "hires_today": farm.get("hires_today", 0),
        "unlocked_quadrants": copy.deepcopy(farm.get("unlocked_quadrants", [])),
        "shed": copy.deepcopy(private.get("shed", {})),
        "seeds": copy.deepcopy(private.get("seeds", {})),
        "inventories": copy.deepcopy(private.get("inventories", [])),
    }


class Recorder:
    def __init__(self, module: types.ModuleType, state: list[Json], env: Json):
        self.module = module
        self.state = state
        self.env = env
        self.events: list[dict[str, Json]] = []
        self.sequence = 0
        self.originals: dict[str, Json] = {}
        self.farm_players = {
            id(farm): player
            for player, farm in enumerate(state[0].observation.farms)
        }

    def reset(self) -> None:
        self.events = []
        self.sequence = 0

    def emit(self, stage: str, **fields: Json) -> None:
        if len(self.events) >= MAX_EVENTS_PER_STEP:
            raise WorkerError("event count exceeds per-step bound")
        event: dict[str, Json] = {
            "sequence": self.sequence,
            "stage": stage,
        }
        event.update(fields)
        self.events.append(event)
        self.sequence += 1

    def digest(self) -> str:
        return semantic_hash(state_snapshot(self.state))

    def player_for_farm(self, farm: Json) -> int:
        player = self.farm_players.get(id(farm))
        if player is None:
            raise WorkerError("interpreter passed an unknown farm object")
        return player

    def install(self) -> None:
        for name in (
            "_apply_unit_action",
            "_process_market",
            "_commit_unit",
            "_do_hire",
            "_do_buy_land",
            "_town_consume",
            "_decay_plants",
            "_end_of_day",
        ):
            self.originals[name] = getattr(self.module, name)

        original_apply = self.originals["_apply_unit_action"]

        @functools.wraps(original_apply)
        def apply_wrapper(farm, private, idx, action, *args, **kwargs):
            player = self.player_for_farm(farm)
            before = self.digest()
            before_player = compact_player(self.state, player)
            result = original_apply(farm, private, idx, action, *args, **kwargs)
            after = self.digest()
            self.emit(
                "unit",
                player=player,
                worker_index=int(idx),
                action=copy.deepcopy(action),
                changed=before != after,
                before_state_sha256=before,
                after_state_sha256=after,
                before_player=before_player,
                after_player=compact_player(self.state, player),
            )
            return result

        self.module._apply_unit_action = apply_wrapper

        original_commit = self.originals["_commit_unit"]

        @functools.wraps(original_commit)
        def commit_wrapper(op, item, price, farm, private, market, *args, **kwargs):
            player = self.player_for_farm(farm)
            before = {
                "money": farm.get("money", 0),
                "shed_item": private.get("shed", {}).get(item, 0),
                "shed_total": sum(private.get("shed", {}).values()),
                "seed_item": private.get("seeds", {}).get(item, 0),
                "market_inventory": market.get("inventory", {}).get(item),
            }
            before_hash = self.digest()
            result = original_commit(
                op, item, price, farm, private, market, *args, **kwargs
            )
            after_hash = self.digest()
            after = {
                "money": farm.get("money", 0),
                "shed_item": private.get("shed", {}).get(item, 0),
                "shed_total": sum(private.get("shed", {}).values()),
                "seed_item": private.get("seeds", {}).get(item, 0),
                "market_inventory": market.get("inventory", {}).get(item),
            }
            self.emit(
                "market_commit",
                player=player,
                operation=str(op),
                item=copy.deepcopy(item),
                price=copy.deepcopy(price),
                success=bool(result),
                before=before,
                after=after,
                before_state_sha256=before_hash,
                after_state_sha256=after_hash,
            )
            return result

        self.module._commit_unit = commit_wrapper

        original_hire = self.originals["_do_hire"]

        @functools.wraps(original_hire)
        def hire_wrapper(farm, private, *args, **kwargs):
            player = self.player_for_farm(farm)
            before = compact_player(self.state, player)
            before_hash = self.digest()
            result = original_hire(farm, private, *args, **kwargs)
            after = compact_player(self.state, player)
            after_hash = self.digest()
            self.emit(
                "market_atomic",
                player=player,
                operation="HIRE",
                success=len(after["hands"]) > len(before["hands"]),
                before=before,
                after=after,
                before_state_sha256=before_hash,
                after_state_sha256=after_hash,
            )
            return result

        self.module._do_hire = hire_wrapper

        original_land = self.originals["_do_buy_land"]

        @functools.wraps(original_land)
        def land_wrapper(farm, *args, **kwargs):
            player = self.player_for_farm(farm)
            before = compact_player(self.state, player)
            before_hash = self.digest()
            result = original_land(farm, *args, **kwargs)
            after = compact_player(self.state, player)
            after_hash = self.digest()
            self.emit(
                "market_atomic",
                player=player,
                operation="BUY_LAND",
                success=len(after["unlocked_quadrants"])
                > len(before["unlocked_quadrants"]),
                before=before,
                after=after,
                before_state_sha256=before_hash,
                after_state_sha256=after_hash,
            )
            return result

        self.module._do_buy_land = land_wrapper

        original_market = self.originals["_process_market"]

        @functools.wraps(original_market)
        def market_wrapper(state, env):
            before = self.digest()
            prefixes = active_market_prefixes(state, env.configuration)
            self.emit(
                "market_enter",
                active_prefixes=prefixes,
                before_state_sha256=before,
            )
            result = original_market(state, env)
            after = self.digest()
            self.emit(
                "market_exit",
                changed=before != after,
                before_state_sha256=before,
                after_state_sha256=after,
            )
            return result

        self.module._process_market = market_wrapper

        original_town = self.originals["_town_consume"]

        @functools.wraps(original_town)
        def town_wrapper(env, state, step):
            market = state[0].observation.market
            before_inventory = copy.deepcopy(market.get("inventory", {}))
            before = self.digest()
            result = original_town(env, state, step)
            after_inventory = copy.deepcopy(market.get("inventory", {}))
            keys = sorted(set(before_inventory) | set(after_inventory))
            delta = {
                key: after_inventory.get(key, 0) - before_inventory.get(key, 0)
                for key in keys
                if after_inventory.get(key, 0) != before_inventory.get(key, 0)
            }
            after = self.digest()
            self.emit(
                "town",
                step=int(step),
                inventory_delta=delta,
                changed=before != after,
                before_state_sha256=before,
                after_state_sha256=after,
            )
            return result

        self.module._town_consume = town_wrapper

        original_decay = self.originals["_decay_plants"]

        @functools.wraps(original_decay)
        def decay_wrapper(farm, step):
            player = self.player_for_farm(farm)
            before = self.digest()
            result = original_decay(farm, step)
            after = self.digest()
            self.emit(
                "decay",
                player=player,
                step=int(step),
                changed=before != after,
                before_state_sha256=before,
                after_state_sha256=after,
            )
            return result

        self.module._decay_plants = decay_wrapper

        original_eod = self.originals["_end_of_day"]

        @functools.wraps(original_eod)
        def eod_wrapper(state, env, day):
            before = self.digest()
            result = original_eod(state, env, day)
            after = self.digest()
            self.emit(
                "end_of_day",
                day=int(day),
                changed=before != after,
                before_state_sha256=before,
                after_state_sha256=after,
            )
            return result

        self.module._end_of_day = eod_wrapper


def validate_fixture(fixture: Json) -> None:
    if not isinstance(fixture, dict) or fixture.get("schema") != FIXTURE_SCHEMA:
        raise WorkerError("fixture schema mismatch")
    steps = fixture.get("steps")
    if not isinstance(steps, list) or not (1 <= len(steps) <= 64):
        raise WorkerError("fixture must contain 1..64 steps")
    start = fixture.get("start_step", 0)
    if isinstance(start, bool) or not isinstance(start, int) or start < 0:
        raise WorkerError("invalid start_step")
    for index, row in enumerate(steps):
        if not isinstance(row, dict):
            raise WorkerError(f"steps[{index}] is not an object")
        if row.get("step", start + index) != start + index:
            raise WorkerError("fixture steps are not contiguous")
        actions = row.get("actions")
        if not isinstance(actions, list) or len(actions) != 2:
            raise WorkerError("each step requires exactly two actions")
    _assert_finite(fixture)


def build_state(module: types.ModuleType, fixture: dict[str, Json]):
    config_data = default_configuration()
    config_data = deep_merge(config_data, fixture.get("configuration", {}), "$config")
    config = AttrDict(config_data)
    board_size = int(config.get("boardSize", 10))
    starting_money = int(config.get("startingMoney", 3000))
    if board_size < 2 or board_size > 100:
        raise WorkerError("boardSize outside [2,100]")
    if int(config.get("turnsPerDay", 24)) <= 0:
        raise WorkerError("turnsPerDay must be positive")
    if int(config.get("shedCapacity", 100)) < 0:
        raise WorkerError("shedCapacity must be nonnegative")

    farms = [module._new_farm(board_size, starting_money) for _ in range(2)]
    privates = [module._new_private() for _ in range(2)]
    market = module._new_market()
    town = module._new_town()
    overrides = fixture.get("overrides", {})
    if not isinstance(overrides, dict):
        raise WorkerError("overrides must be an object")
    farm_patches = overrides.get("farms", [{}, {}])
    private_patches = overrides.get("privates", [{}, {}])
    if not isinstance(farm_patches, list) or len(farm_patches) != 2:
        raise WorkerError("farms override must contain two patches")
    if not isinstance(private_patches, list) or len(private_patches) != 2:
        raise WorkerError("privates override must contain two patches")
    farms = [deep_merge(farms[i], farm_patches[i], f"$farms[{i}]") for i in range(2)]
    privates = [
        deep_merge(privates[i], private_patches[i], f"$privates[{i}]")
        for i in range(2)
    ]
    market = deep_merge(market, overrides.get("market", {}), "$market")
    town = deep_merge(town, overrides.get("town", {}), "$town")
    module._refresh_prices(market)

    start = int(fixture.get("start_step", 0))
    turns = max(1, int(config.get("turnsPerDay", 24)))
    cells: list[Json] = []
    for player in range(2):
        observation = AttrDict(
            player=player,
            step=start,
            day=start // turns,
            hour=start % turns,
            farms=farms,
            market=market,
            town=town,
            private=privates[player],
        )
        cells.append(
            types.SimpleNamespace(
                observation=observation,
                action={},
                status="ACTIVE",
                reward=0.0,
            )
        )
    env = types.SimpleNamespace(
        configuration=config,
        info={"seed": int(fixture.get("seed", 0))},
        done=False,
    )
    return cells, env


def run_fixture(
    module: types.ModuleType,
    fixture: dict[str, Json],
    *,
    source: dict[str, Json],
) -> dict[str, Json]:
    state, env = build_state(module, fixture)
    recorder = Recorder(module, state, env)
    recorder.install()
    retain_states = fixture.get("retain_states", True) is not False
    start = int(fixture.get("start_step", 0))
    rows: list[dict[str, Json]] = []
    initial = state_snapshot(state)

    for offset, step_spec in enumerate(fixture["steps"]):
        step = start + offset
        for cell in state:
            cell.observation.step = step
        actions = copy.deepcopy(step_spec["actions"])
        for player in range(2):
            state[player].action = actions[player]
        pre = state_snapshot(state)
        prefixes = active_market_prefixes(state, env.configuration)
        recorder.reset()
        returned = module.interpreter(state, env)
        if returned is not state:
            raise WorkerError("interpreter replaced the state container")
        post = state_snapshot(state)
        row: dict[str, Json] = {
            "step": step,
            "actions_sha256": semantic_hash(actions),
            "active_market_prefixes": prefixes,
            "active_market_prefixes_sha256": semantic_hash(prefixes),
            "pre_state_sha256": semantic_hash(pre),
            "post_state_sha256": semantic_hash(post),
            "events": copy.deepcopy(recorder.events),
            "event_trace_sha256": semantic_hash(recorder.events),
        }
        if retain_states:
            row["pre_state"] = pre
            row["post_state"] = post
        rows.append(row)

    terminal = state_snapshot(state)
    receipt: dict[str, Json] = {
        "schema": SCHEMA,
        "fixture_name": fixture["name"],
        "fixture_sha256": semantic_hash(fixture),
        "source": source,
        "configuration": copy.deepcopy(dict(env.configuration)),
        "seed": int(fixture.get("seed", 0)),
        "initial_state": initial,
        "initial_state_sha256": semantic_hash(initial),
        "steps": rows,
        "terminal_state": terminal,
        "terminal_state_sha256": semantic_hash(terminal),
        "engine_unchanged": True,
        "semantic_boundary": [
            "atomic_unit_validation",
            "player_order_atomic_market",
            "per_unit_two_player_precommit_quotes",
            "town_consumption",
            "plant_decay",
            "end_of_day",
        ],
    }
    receipt["transition_sha256"] = semantic_hash(
        {
            "initial": receipt["initial_state_sha256"],
            "steps": [
                {
                    "step": row["step"],
                    "actions": row["actions_sha256"],
                    "prefixes": row["active_market_prefixes_sha256"],
                    "pre": row["pre_state_sha256"],
                    "events": row["event_trace_sha256"],
                    "post": row["post_state_sha256"],
                }
                for row in rows
            ],
            "terminal": receipt["terminal_state_sha256"],
        }
    )
    receipt["receipt_sha256"] = semantic_hash(receipt)
    return receipt


def emit_error(exc: BaseException) -> int:
    payload = {
        "schema": "titan.v3.official-transition-oracle.error.v1",
        "error_type": type(exc).__name__,
        "message": str(exc),
    }
    sys.stdout.buffer.write(canonical_bytes(payload) + b"\n")
    return 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--expected-engine-blob", required=True)
    parser.add_argument("--expected-worker-sha256", required=True)
    args = parser.parse_args()
    try:
        worker_path, worker_bytes = bound_file(Path(__file__), "worker")
        worker_sha = sha256_bytes(worker_bytes)
        if worker_sha != args.expected_worker_sha256:
            raise WorkerError("worker SHA-256 mismatch")
        engine_path, engine_bytes = bound_file(args.engine, "engine")
        suffix_parts = EXPECTED_ENGINE_SUFFIX.parts
        if tuple(engine_path.parts[-len(suffix_parts):]) != suffix_parts:
            raise WorkerError(
                f"engine path must end with {EXPECTED_ENGINE_SUFFIX.as_posix()}"
            )
        engine_blob = git_blob_sha(engine_bytes)
        if engine_blob != args.expected_engine_blob:
            raise WorkerError("engine Git blob mismatch")
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise WorkerError("fixture input exceeds byte bound")
        fixture = strict_loads(raw)
        validate_fixture(fixture)
        fixture_canonical = canonical_bytes(fixture)
        module = load_engine(engine_path)
        source = {
            "engine_git_blob": engine_blob,
            "engine_sha256": sha256_bytes(engine_bytes),
            "engine_bytes": len(engine_bytes),
            "worker_sha256": worker_sha,
            "worker_bytes": len(worker_bytes),
            "isolated": True,
            "bytecode_disabled": True,
        }
        receipt = run_fixture(module, fixture, source=source)
        if engine_path.read_bytes() != engine_bytes:
            raise WorkerError("engine bytes changed during execution")
        if worker_path.read_bytes() != worker_bytes:
            raise WorkerError("worker bytes changed during execution")
        sys.stdout.buffer.write(canonical_bytes(receipt) + b"\n")
        return 0
    except BaseException as exc:
        return emit_error(exc)


if __name__ == "__main__":
    raise SystemExit(main())
