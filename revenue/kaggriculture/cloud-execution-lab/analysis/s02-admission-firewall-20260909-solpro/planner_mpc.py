# SPDX-License-Identifier: Apache-2.0
"""Fail-closed S02 planner admission firewall.

This module is a drop-in replacement for the original V3 S02 experiment.  It
keeps the useful idea -- exact-engine counterfactual evaluation -- while
removing the unsafe parts that made the H=6 candidate collapse:

* no worker-action mutations;
* no order invention, deletion, quantity change, or payload change;
* no fake multi-step rollout in which our farm passes after turn zero;
* no mutable rival shadow shared across candidates;
* no absolute-cash comparison across unmatched simulations;
* no execution from a partial scenario set; and
* shadow-only operation by default.

A candidate can execute only when it is a pure permutation of the canonical
market tape and every required paired scenario reaches the same complete
post-step state (apart from our cash) with a strict cash improvement.  This is
a dominance certificate, not a speculative value estimate.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterable, Mapping, Sequence

ENGINE_DIR = os.environ.get("TITAN_MPC_ENGINE", "/tmp/v25/engine")
_ENGINE = None
_FALSE = frozenset(("", "0", "false", "no", "off"))
_KNOWN_MARKET_OPS = frozenset(
    ("SELL", "HIRE", "BUY_LAND", "BUY_SEED", "BUY_ANIMAL", "BUY_PRODUCT", "PASS")
)
_STATS: dict[str, Any] = {
    "turns": 0,
    "off": 0,
    "shadow_turns": 0,
    "execute_turns": 0,
    "recommendations": 0,
    "executed": 0,
    "timeouts": 0,
    "errors": 0,
    "rejected_structure": 0,
    "rejected_evidence": 0,
    "plan_s": [],
}


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() not in _FALSE


def _mode_from_env() -> str:
    if not _truthy(os.environ.get("TITAN_MPC", "1")):
        return "off"
    mode = os.environ.get("TITAN_MPC_MODE", "shadow").strip().lower()
    if _truthy(os.environ.get("TITAN_MPC_EXECUTE", "0")):
        mode = "execute"
    return mode if mode in {"off", "shadow", "execute"} else "shadow"


def _engine():
    global _ENGINE
    if _ENGINE is None:
        import importlib.util
        import sys

        path = os.path.join(ENGINE_DIR, "kaggriculture.py")
        spec = importlib.util.spec_from_file_location("_s02_guard_kaggriculture", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"unable to load Kaggriculture engine at {path}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_s02_guard_kaggriculture"] = mod
        spec.loader.exec_module(mod)
        _ENGINE = mod
    return _ENGINE


def _as_dict(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return {str(k): _as_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_as_dict(v) for v in obj]
    if hasattr(obj, "toDict"):
        return _as_dict(obj.toDict())
    return obj


def _obs_dict(observation: Any) -> dict[str, Any]:
    if isinstance(observation, Mapping):
        return _as_dict(observation)
    if hasattr(observation, "toDict"):
        return _as_dict(observation.toDict())
    return _as_dict(dict(observation))


class _Obs(dict):
    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


class _Cfg(dict):
    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


def _wrap_obs(values: Mapping[str, Any]) -> _Obs:
    out = _Obs()
    out.update(values)
    return out


def legal_pass(obs: Mapping[str, Any], player: int | None = None) -> dict[str, Any]:
    idx = int(obs["player"] if player is None else player)
    farm = obs["farms"][idx]
    n_hands = len(farm.get("hands") or [])
    return {
        "farmer": ["PASS"],
        "hands": [["PASS"] for _ in range(n_hands)],
        "market": [],
    }


def _norm_action(action: Any, obs: Mapping[str, Any], player: int | None = None) -> dict[str, Any]:
    idx = int(obs["player"] if player is None else player)
    farm = obs["farms"][idx]
    n_hands = len(farm.get("hands") or [])
    if not isinstance(action, Mapping):
        return legal_pass(obs, idx)
    farmer = action.get("farmer") or ["PASS"]
    farmer = list(farmer) if isinstance(farmer, (list, tuple)) else ["PASS"]
    hands = list(action.get("hands") or [])
    while len(hands) < n_hands:
        hands.append(["PASS"])
    normalized_hands = [
        list(row) if isinstance(row, (list, tuple)) else ["PASS"] for row in hands[:n_hands]
    ]
    return {
        "farmer": farmer,
        "hands": normalized_hands,
        "market": copy.deepcopy(list(action.get("market") or [])),
    }


def _typed_scalar(value: Any) -> list[Any]:
    """Encode a scalar without collapsing Python key/value types."""
    if value is None:
        return ["none", None]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, int):
        return ["int", str(value)]
    if isinstance(value, float):
        if math.isnan(value):
            return ["float", "nan"]
        if math.isinf(value):
            return ["float", "+inf" if value > 0 else "-inf"]
        return ["float", value.hex()]
    if isinstance(value, str):
        return ["str", value]
    raise TypeError(f"unsupported canonical scalar: {type(value).__name__}")


def _typed_tree(value: Any) -> Any:
    """Collision-free canonical tree for game/action identity checks.

    Mapping keys are represented as typed values rather than coerced strings,
    so ``{1: 'x', '1': 'y'}`` cannot alias ``{'1': 'y'}``. Unsupported
    objects fail closed instead of falling back to repr-based identity.
    """
    if isinstance(value, Mapping):
        rows = [(_typed_tree(key), _typed_tree(item)) for key, item in value.items()]
        rows.sort(key=lambda pair: json.dumps(pair[0], separators=(",", ":"), ensure_ascii=True))
        return ["map", rows]
    if isinstance(value, list):
        return ["list", [_typed_tree(item) for item in value]]
    if isinstance(value, tuple):
        return ["tuple", [_typed_tree(item) for item in value]]
    if hasattr(value, "toDict"):
        return _typed_tree(value.toDict())
    return _typed_scalar(value)


def _json_key(value: Any) -> str:
    return json.dumps(_typed_tree(value), separators=(",", ":"), ensure_ascii=True)


def action_digest(action: Mapping[str, Any]) -> str:
    return hashlib.sha256(_json_key(action).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class StructureCheck:
    ok: bool
    reason: str


def structural_contract(canonical: Mapping[str, Any], candidate: Mapping[str, Any]) -> StructureCheck:
    """Admit only an exact permutation of the canonical market tape.

    Worker actions and every market-row payload are immutable.  The market tape
    length and multiplicity are also immutable, including empty slots.
    """
    if not isinstance(canonical, Mapping) or not isinstance(candidate, Mapping):
        return StructureCheck(False, "non_mapping_action")
    try:
        if _json_key(candidate.get("farmer") or ["PASS"]) != _json_key(
            canonical.get("farmer") or ["PASS"]
        ):
            return StructureCheck(False, "farmer_changed")
        if _json_key(candidate.get("hands") or []) != _json_key(canonical.get("hands") or []):
            return StructureCheck(False, "hands_changed")
        base_other = {key: value for key, value in canonical.items() if key != "market"}
        cand_other = {key: value for key, value in candidate.items() if key != "market"}
        if _json_key(base_other) != _json_key(cand_other):
            return StructureCheck(False, "non_market_payload_changed")
        base_market = list(canonical.get("market") or [])
        cand_market = list(candidate.get("market") or [])
        if len(base_market) != len(cand_market):
            return StructureCheck(False, "market_length_changed")
        if Counter(map(_json_key, base_market)) != Counter(map(_json_key, cand_market)):
            return StructureCheck(False, "market_payload_changed")
        for order in cand_market:
            if order and (
                not isinstance(order, (list, tuple)) or str(order[0]) not in _KNOWN_MARKET_OPS
            ):
                return StructureCheck(False, "unknown_market_operation")
        if _json_key(candidate) == _json_key(canonical):
            return StructureCheck(False, "canonical_identity")
    except (TypeError, ValueError):
        return StructureCheck(False, "unserializable_action")
    return StructureCheck(True, "exact_market_permutation")


def _stable_market_variant(action: Mapping[str, Any], rank: Callable[[Any], int]) -> dict[str, Any]:
    out = copy.deepcopy(dict(action))
    market = list(out.get("market") or [])
    out["market"] = [row for _, row in sorted(enumerate(market), key=lambda pair: (rank(pair[1]), pair[0]))]
    return out


def generate_candidates(
    canonical: Mapping[str, Any],
    obs: Mapping[str, Any] | None = None,
    cfg: Mapping[str, Any] | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Generate bounded queue-order variants while preserving all payloads.

    The current canonical action is always first.  Variants are intentionally
    narrow: stable SELL-first, stable funding/service/capital grouping, then
    adjacent swaps of non-empty rows.  No worker action or row payload changes.
    """
    del obs, cfg
    base = copy.deepcopy(dict(canonical))
    candidates: list[dict[str, Any]] = [base]
    seen = {action_digest(base)}
    market = list(base.get("market") or [])
    if len(market) < 2 or limit <= 1:
        return candidates

    def sell_first(row: Any) -> int:
        return 0 if row and row[0] == "SELL" else 1

    def economic_order(row: Any) -> int:
        if not row:
            return 5
        op = row[0]
        return {
            "SELL": 0,
            "HIRE": 1,
            "BUY_SEED": 1,
            "BUY_PRODUCT": 2,
            "BUY_LAND": 3,
            "BUY_ANIMAL": 3,
            "PASS": 5,
        }.get(op, 4)

    variants: list[dict[str, Any]] = [
        _stable_market_variant(base, sell_first),
        _stable_market_variant(base, economic_order),
    ]
    for index in range(len(market) - 1):
        if not market[index] or not market[index + 1]:
            continue
        variant = copy.deepcopy(base)
        rows = list(variant.get("market") or [])
        rows[index], rows[index + 1] = rows[index + 1], rows[index]
        variant["market"] = rows
        variants.append(variant)

    for variant in variants:
        digest = action_digest(variant)
        if digest in seen:
            continue
        check = structural_contract(base, variant)
        if not check.ok:
            continue
        seen.add(digest)
        candidates.append(variant)
        if len(candidates) >= max(1, int(limit)):
            break
    return candidates


@dataclass(frozen=True)
class VisibilityCertificate:
    exact: bool
    reasons: tuple[str, ...]
    step: int


def live_visibility_certificate(obs: Mapping[str, Any], cfg: Mapping[str, Any]) -> VisibilityCertificate:
    """Describe whether one exact reacting transition is observable live.

    Ad-hoc injected keys are deliberately ignored.  Kaggriculture exposes both
    public farms but only the active player's private packet.  A transition at
    the day boundary also consumes hidden RNG state.
    """
    step = int(
        obs.get("step")
        if obs.get("step") is not None
        else int(obs.get("day", 0)) * int(cfg.get("turnsPerDay", 24))
        + int(obs.get("hour", 0))
    )
    reasons: list[str] = []
    farms = obs.get("farms") or []
    player = int(obs.get("player", 0))
    if not isinstance(obs.get("private"), Mapping):
        reasons.append("missing_own_private")
    if len(farms) > 1:
        reasons.append("missing_rival_private_for_exact_reacting_transition")
    if not (0 <= player < len(farms)):
        reasons.append("missing_public_farm")
    turns = max(1, int(cfg.get("turnsPerDay", 24)))
    if (step + 1) % turns == 0:
        reasons.append("hidden_end_of_day_rng_seed")
    return VisibilityCertificate(not reasons, tuple(reasons), step)


@dataclass(frozen=True)
class RivalScenario:
    name: str
    action: Mapping[str, Any]
    private: Mapping[str, Any] | None = None
    # True only for an offline evidence packet whose rival private state and
    # transition RNG are source-bound.  Live callers cannot create exactness by
    # injecting this bit; paired_one_step_evaluate also checks live visibility.
    certified_exact: bool = False


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    complete: bool
    exact: bool
    state_equivalent: bool
    baseline_cash: float | None
    candidate_cash: float | None
    delta: float | None
    reason: str


@dataclass(frozen=True)
class Evaluation:
    scenarios: tuple[ScenarioResult, ...]
    reason: str = "paired_one_step"

    @property
    def complete(self) -> bool:
        return bool(self.scenarios) and all(row.complete for row in self.scenarios)

    @property
    def exact(self) -> bool:
        return self.complete and all(row.exact for row in self.scenarios)

    @property
    def state_equivalent(self) -> bool:
        return self.complete and all(row.state_equivalent for row in self.scenarios)

    @property
    def scenario_count(self) -> int:
        return len(self.scenarios)

    @property
    def deltas(self) -> tuple[float, ...]:
        return tuple(float(row.delta) for row in self.scenarios if row.delta is not None)

    @property
    def worst_delta(self) -> float:
        return min(self.deltas) if len(self.deltas) == len(self.scenarios) and self.deltas else float("-inf")

    def admitted(self, *, min_scenarios: int, min_cash_gain: float) -> bool:
        return (
            self.complete
            and self.exact
            and self.state_equivalent
            and self.scenario_count >= int(min_scenarios)
            and self.worst_delta >= float(min_cash_gain)
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.update(
            complete=self.complete,
            exact=self.exact,
            state_equivalent=self.state_equivalent,
            scenario_count=self.scenario_count,
            worst_delta=self.worst_delta,
        )
        return data


def _make_env(cfg: Mapping[str, Any], seed: int = 0) -> SimpleNamespace:
    raw = copy.deepcopy(dict(cfg or {}))
    for key, value in (
        ("episodeSteps", 720),
        ("turnsPerDay", 24),
        ("boardSize", 10),
        ("shedCapacity", 100),
        ("weedSpawnChance", 0.005),
        ("townShopUnlockInterval", 3),
        ("maxMarketOrdersPerTurn", 10),
        ("startingMoney", 3000),
    ):
        raw.setdefault(key, value)
    return SimpleNamespace(configuration=_Cfg(raw), done=False, info={"seed": int(seed)})


def _new_private() -> Mapping[str, Any]:
    return copy.deepcopy(_engine()._new_private())


def instantiate_state(
    obs: Mapping[str, Any], cfg: Mapping[str, Any], rival_private: Mapping[str, Any] | None = None
) -> list[SimpleNamespace]:
    del cfg
    player = int(obs["player"])
    rival = 1 - player
    farms = copy.deepcopy(obs["farms"])
    market = copy.deepcopy(obs["market"])
    town = copy.deepcopy(obs.get("town") or {"unlocked_shops": []})
    step = int(
        obs.get("step")
        if obs.get("step") is not None
        else int(obs.get("day", 0)) * 24 + int(obs.get("hour", 0))
    )
    day = int(obs.get("day", step // 24))
    hour = int(obs.get("hour", step % 24))
    privates: list[Mapping[str, Any] | None] = [None, None]
    privates[player] = copy.deepcopy(obs.get("private") or _new_private())
    privates[rival] = copy.deepcopy(rival_private) if rival_private is not None else _new_private()
    states: list[SimpleNamespace] = []
    for idx in range(2):
        wrapped = _wrap_obs(
            {
                "player": idx,
                "step": step,
                "day": day,
                "hour": hour,
                "farms": farms,
                "market": market,
                "town": town,
                "private": privates[idx],
            }
        )
        states.append(SimpleNamespace(observation=wrapped, action={}, status="ACTIVE", reward=0))
    return states


def _obs_for_player(states: Sequence[SimpleNamespace], player: int) -> dict[str, Any]:
    current = states[player].observation
    return {
        "player": player,
        "step": int(current.get("step", 0)),
        "day": int(current.get("day", 0)),
        "hour": int(current.get("hour", 0)),
        "farms": current["farms"],
        "market": current["market"],
        "town": current.get("town") or {"unlocked_shops": []},
        "private": current["private"],
    }


def _step_engine(
    states: Sequence[SimpleNamespace], env: SimpleNamespace, joint_actions: Sequence[Mapping[str, Any]]
) -> Sequence[SimpleNamespace]:
    for idx, state in enumerate(states):
        state.action = copy.deepcopy(joint_actions[idx])
    _engine().interpreter(states, env)
    # Kaggriculture's interpreter updates day/hour and farm state.  The agent
    # harness owns the externally visible step counter, so mirror that one-step
    # advance in the simulated observations exactly once.
    next_step = int(states[0].observation.get("step", 0)) + 1
    for state in states:
        state.observation["step"] = next_step
        state.observation.step = next_step
    return states


def _cash(states: Sequence[SimpleNamespace], player: int) -> float:
    return float(states[0].observation["farms"][player]["money"])


def _states_valid(states: Sequence[SimpleNamespace]) -> bool:
    if len(states) != 2:
        return False
    for state in states:
        status = str(getattr(state, "status", "")).upper()
        if status not in {"ACTIVE", "DONE"}:
            return False
        if not hasattr(state, "observation"):
            return False
    return True


def _state_payload(states: Sequence[SimpleNamespace], own_player: int) -> dict[str, Any]:
    public = states[0].observation
    farms = copy.deepcopy(public["farms"])
    farms[own_player]["money"] = "__OWN_CASH__"
    return {
        "farms": farms,
        "market": public["market"],
        "town": public.get("town"),
        "day": public.get("day"),
        "hour": public.get("hour"),
        "step": public.get("step"),
        "private": [states[0].observation["private"], states[1].observation["private"]],
        "status": [states[0].status, states[1].status],
        "reward": [states[0].reward, states[1].reward],
    }


def _state_digest(states: Sequence[SimpleNamespace], own_player: int) -> str:
    return hashlib.sha256(_json_key(_state_payload(states, own_player)).encode("utf-8")).hexdigest()


def _paired_seed(obs: Mapping[str, Any], cfg: Mapping[str, Any], scenario_name: str) -> int:
    base = f"{cfg.get('seed', 0)}|{obs.get('step', 0)}|{obs.get('player', 0)}|{scenario_name}"
    return int(hashlib.sha256(base.encode("utf-8")).hexdigest()[:15], 16)


def _simulate_one_step(
    obs: Mapping[str, Any],
    cfg: Mapping[str, Any],
    own_action: Mapping[str, Any],
    scenario: RivalScenario,
    *,
    pair_seed: int,
) -> Sequence[SimpleNamespace]:
    player = int(obs["player"])
    rival = 1 - player
    env = _make_env(cfg, seed=pair_seed)
    states = instantiate_state(obs, cfg, rival_private=scenario.private)
    own_obs = _obs_for_player(states, player)
    rival_obs = _obs_for_player(states, rival)
    joint: list[Mapping[str, Any] | None] = [None, None]
    joint[player] = _norm_action(own_action, own_obs, player)
    joint[rival] = _norm_action(scenario.action, rival_obs, rival)
    return _step_engine(states, env, joint)  # type: ignore[arg-type]


def default_scenarios(obs: Mapping[str, Any], cfg: Mapping[str, Any]) -> tuple[RivalScenario, ...]:
    del cfg
    rival = 1 - int(obs["player"])
    rival_obs = dict(obs)
    rival_obs["player"] = rival
    return (
        RivalScenario(
            "public_pass_empty_private",
            legal_pass(rival_obs, rival),
            None,
            certified_exact=False,
        ),
    )


def _bounded_scenarios(
    scenarios: Iterable[RivalScenario], deadline: float, *, limit: int = 16
) -> tuple[tuple[RivalScenario, ...], str | None]:
    """Pull a bounded, uniquely named scenario set.

    This bounds raw iterator pulls as well as retained rows. A provider must
    still make each individual ``next()`` cooperative; untrusted providers
    belong in a process-isolated harness.
    """
    iterator = iter(scenarios)
    rows: list[RivalScenario] = []
    names: set[str] = set()
    for _ in range(max(0, int(limit))):
        if time.perf_counter() >= deadline:
            raise TimeoutError("S02 scenario enumeration deadline")
        try:
            scenario = next(iterator)
        except StopIteration:
            return tuple(rows), None
        if not isinstance(scenario, RivalScenario):
            return tuple(rows), "invalid_scenario_type"
        if not isinstance(scenario.name, str) or not scenario.name.strip():
            return tuple(rows), "invalid_scenario_name"
        if scenario.name in names:
            return tuple(rows), "duplicate_scenario_name"
        if not isinstance(scenario.action, Mapping):
            return tuple(rows), "invalid_scenario_action"
        if scenario.private is not None and not isinstance(scenario.private, Mapping):
            return tuple(rows), "invalid_scenario_private"
        names.add(scenario.name)
        rows.append(scenario)
    if time.perf_counter() >= deadline:
        raise TimeoutError("S02 scenario enumeration deadline")
    try:
        next(iterator)
    except StopIteration:
        return tuple(rows), None
    return tuple(rows), "scenario_limit_exceeded"


def paired_one_step_evaluate(
    obs: Mapping[str, Any],
    cfg: Mapping[str, Any],
    canonical: Mapping[str, Any],
    candidate: Mapping[str, Any],
    deadline: float,
    scenario_provider: Callable[[Mapping[str, Any], Mapping[str, Any]], Iterable[RivalScenario]] = default_scenarios,
) -> Evaluation:
    """Evaluate matched one-step transitions from fresh states.

    The random module state is restored after each pair.  Baseline and candidate
    receive the same deterministic pair seed.  Any engine error, timeout,
    incomplete scenario, or non-cash state difference fails closed.
    """
    check = structural_contract(canonical, candidate)
    if not check.ok:
        return Evaluation(
            (ScenarioResult("structure", False, False, False, None, None, None, check.reason),),
            reason="structure_rejected",
        )
    visibility = live_visibility_certificate(obs, cfg)
    rows: list[ScenarioResult] = []
    scenarios, scenario_error = _bounded_scenarios(scenario_provider(obs, cfg), deadline)
    if scenario_error is not None:
        return Evaluation(
            (ScenarioResult("scenario_set", False, False, False, None, None, None, scenario_error),),
            reason="scenario_set_rejected",
        )
    if not scenarios:
        return Evaluation(
            (ScenarioResult("scenario_set", False, False, False, None, None, None, "empty_scenario_set"),),
            reason="scenario_set_rejected",
        )
    for scenario in scenarios:
        if time.perf_counter() >= deadline:
            raise TimeoutError("S02 paired evaluator deadline")
        pair_seed = _paired_seed(obs, cfg, scenario.name)
        saved_random = random.getstate()
        try:
            random.seed(pair_seed)
            baseline_states = _simulate_one_step(
                obs, cfg, canonical, scenario, pair_seed=pair_seed
            )
            random.seed(pair_seed)
            candidate_states = _simulate_one_step(
                obs, cfg, candidate, scenario, pair_seed=pair_seed
            )
        except Exception as exc:  # exact error is diagnostic, never admission
            rows.append(
                ScenarioResult(
                    scenario.name,
                    False,
                    False,
                    False,
                    None,
                    None,
                    None,
                    f"engine_error:{type(exc).__name__}",
                )
            )
            continue
        finally:
            random.setstate(saved_random)
        if not _states_valid(baseline_states) or not _states_valid(candidate_states):
            rows.append(
                ScenarioResult(
                    scenario.name,
                    False,
                    False,
                    False,
                    None,
                    None,
                    None,
                    "invalid_engine_status",
                )
            )
            continue
        baseline_cash = _cash(baseline_states, int(obs["player"]))
        candidate_cash = _cash(candidate_states, int(obs["player"]))
        equivalent = _state_digest(baseline_states, int(obs["player"])) == _state_digest(
            candidate_states, int(obs["player"])
        )
        delta = candidate_cash - baseline_cash
        if not visibility.exact or not scenario.certified_exact:
            reason = "sensitivity_only:" + ",".join(visibility.reasons or ("uncertified_scenario",))
        elif not equivalent:
            reason = "non_cash_state_changed"
        elif delta > 0:
            reason = "strict_cash_dominance"
        elif delta == 0:
            reason = "cash_tie"
        else:
            reason = "cash_regression"
        rows.append(
            ScenarioResult(
                scenario.name,
                True,
                bool(visibility.exact and scenario.certified_exact),
                equivalent,
                baseline_cash,
                candidate_cash,
                delta,
                reason,
            )
        )
    return Evaluation(tuple(rows))


def _write_jsonl(path: str, payload: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")


class Planner:
    """Canonical-first planner with shadow-default, strict evidence admission."""

    def __init__(
        self,
        canonical_fn: Callable[[Any, Any], Mapping[str, Any]],
        horizon: int = 12,
        budget_s: float = 0.6,
        *,
        mode: str | None = None,
        min_scenarios: int | None = None,
        min_cash_gain: float | None = None,
        candidate_fn: Callable[..., list[dict[str, Any]]] = generate_candidates,
        evaluator: Callable[..., Evaluation] = paired_one_step_evaluate,
        log_path: str | None = None,
    ) -> None:
        self.canonical_fn = canonical_fn
        self.requested_horizon = int(horizon)
        # Honest model boundary: this implementation evaluates exactly one
        # transition; it never fills an unmodelled suffix with PASS actions.
        self.evaluation_horizon = 1
        self.budget_s = max(0.0, float(budget_s))
        selected_mode = (mode or _mode_from_env()).strip().lower()
        self.mode = selected_mode if selected_mode in {"off", "shadow", "execute"} else "shadow"
        self.min_scenarios = int(
            min_scenarios
            if min_scenarios is not None
            else os.environ.get("TITAN_MPC_MIN_SCENARIOS", "3")
        )
        self.min_cash_gain = float(
            min_cash_gain
            if min_cash_gain is not None
            else os.environ.get("TITAN_MPC_MIN_CASH_GAIN", "1")
        )
        self.candidate_fn = candidate_fn
        self.evaluator = evaluator
        self.log_path = log_path or os.environ.get("TITAN_MPC_LOG", "/tmp/v25/s02_guard.jsonl")

    def _record(
        self,
        *,
        obs: Mapping[str, Any],
        canonical: Mapping[str, Any],
        recommended: Mapping[str, Any],
        executed: bool,
        evaluation: Evaluation | None,
        elapsed: float,
        rejections: Sequence[str],
    ) -> None:
        payload: dict[str, Any] = {
            "schema": "titan.s02.guard.v1",
            "step": int(obs.get("step", 0)),
            "player": int(obs.get("player", 0)),
            "mode": self.mode,
            "requested_horizon": self.requested_horizon,
            "evaluation_horizon": self.evaluation_horizon,
            "canonical_sha256": action_digest(canonical),
            "recommended_sha256": action_digest(recommended),
            "recommended": action_digest(recommended) != action_digest(canonical),
            "executed": bool(executed),
            "elapsed_s": round(float(elapsed), 9),
            "rejections": list(rejections),
        }
        if evaluation is not None:
            payload["evaluation"] = evaluation.to_dict()
        try:
            _write_jsonl(self.log_path, payload)
        except Exception:
            # Telemetry may never alter the canonical action path.
            pass

    def act(self, observation: Any, configuration: Any = None) -> Mapping[str, Any]:
        t0 = time.perf_counter()
        canonical = copy.deepcopy(dict(self.canonical_fn(observation, configuration)))
        _STATS["turns"] += 1
        if self.mode == "off":
            _STATS["off"] += 1
            return canonical

        obs = _obs_dict(observation)
        cfg = dict(configuration or {})
        if obs.get("step") is None:
            obs["step"] = int(obs.get("day", 0)) * int(cfg.get("turnsPerDay", 24)) + int(
                obs.get("hour", 0)
            )
        deadline = t0 + self.budget_s
        best = canonical
        best_eval: Evaluation | None = None
        best_worst = float("-inf")
        rejections: list[str] = []
        try:
            candidates = self.candidate_fn(canonical, obs, cfg, limit=8)
            for candidate in candidates[1:]:
                if time.perf_counter() >= deadline:
                    _STATS["timeouts"] += 1
                    rejections.append("deadline")
                    break
                check = structural_contract(canonical, candidate)
                if not check.ok:
                    _STATS["rejected_structure"] += 1
                    rejections.append(check.reason)
                    continue
                try:
                    evaluation = self.evaluator(obs, cfg, canonical, candidate, deadline)
                except TimeoutError:
                    _STATS["timeouts"] += 1
                    rejections.append("evaluator_timeout")
                    break
                except Exception as exc:
                    _STATS["errors"] += 1
                    rejections.append(f"evaluator_error:{type(exc).__name__}")
                    continue
                if not evaluation.admitted(
                    min_scenarios=self.min_scenarios, min_cash_gain=self.min_cash_gain
                ):
                    _STATS["rejected_evidence"] += 1
                    rejections.append(
                        "evidence:"
                        f"complete={int(evaluation.complete)},"
                        f"exact={int(evaluation.exact)},"
                        f"equivalent={int(evaluation.state_equivalent)},"
                        f"n={evaluation.scenario_count},"
                        f"worst={evaluation.worst_delta}"
                    )
                    continue
                if evaluation.worst_delta > best_worst:
                    best = copy.deepcopy(candidate)
                    best_eval = evaluation
                    best_worst = evaluation.worst_delta
        except Exception as exc:
            _STATS["errors"] += 1
            rejections.append(f"planner_error:{type(exc).__name__}")
            best = canonical
            best_eval = None

        recommended = action_digest(best) != action_digest(canonical)
        if recommended:
            _STATS["recommendations"] += 1
        executed = bool(recommended and self.mode == "execute")
        if executed:
            _STATS["executed"] += 1
            _STATS["execute_turns"] += 1
            output = best
        else:
            _STATS["shadow_turns"] += 1
            output = canonical
        elapsed = time.perf_counter() - t0
        _STATS["plan_s"].append(elapsed)
        self._record(
            obs=obs,
            canonical=canonical,
            recommended=best,
            executed=executed,
            evaluation=best_eval,
            elapsed=elapsed,
            rejections=rejections,
        )
        return output


def stats() -> dict[str, Any]:
    result = {key: copy.deepcopy(value) for key, value in _STATS.items() if key != "plan_s"}
    times = list(_STATS["plan_s"])
    if not times:
        result.update(n=0, max=None, p50=None)
        return result
    ordered = sorted(float(value) for value in times)
    result.update(n=len(ordered), max=ordered[-1], p50=ordered[len(ordered) // 2])
    return result
