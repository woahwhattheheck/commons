# SPDX-License-Identifier: Apache-2.0
"""Source-bound accounting for the Gemini/Antigravity WEEDBANK idea.

This is a research oracle, not a policy. It separates three effects that the
original "zero-cost coop carpet" proposal conflated:

* direct weed avoidance (a tile can need at most one DIG before it stops being
  empty, because a spawned weed occupies the tile);
* BUILD/DIG unit-action opportunity cost; and
* shared EOD RNG cursor movement, which may alter later public town-shop RNG.

The oracle deliberately emits no runtime admission bit and gives RNG steering
no positive value without a separately authenticated predictor/economic gate.
"""
from __future__ import annotations

import hashlib
import math

ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
STANDARD_WEED_CHANCE = 0.005
STANDARD_EODS = 30


class WeedbankContractError(ValueError):
    """Input or source evidence is outside the bounded theorem."""


def git_blob_sha1(data: bytes) -> str:
    if not isinstance(data, bytes):
        raise WeedbankContractError("engine data must be bytes")
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def verify_engine_bytes(data: bytes) -> bool:
    """Fail closed unless bytes are the exact pinned official engine."""
    if git_blob_sha1(data) != ENGINE_GIT_BLOB:
        raise WeedbankContractError("official engine Git blob drift")
    text = data.decode("utf-8")
    anchors = (
        'if op == "DIG":',
        "Removes plants, weeds, empty coop/pasture. Does NOT remove a placed animal.",
        'if op == "BUILD_COOP":',
        'farm["tiles"][fy][fx] = {"kind": "COOP"}',
        'if farm["tiles"][y][x] is None and rng.random() < weed_chance:',
    )
    missing = [anchor for anchor in anchors if anchor not in text]
    if missing:
        raise WeedbankContractError("pinned engine is missing WEEDBANK source anchors")
    return True


def _plain_nonnegative_int(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise WeedbankContractError(f"{name} must be a nonnegative plain int")
    return value


def _probability(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WeedbankContractError("weed_chance must be a finite number in [0,1]")
    value = float(value)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise WeedbankContractError("weed_chance must be a finite number in [0,1]")
    return value


def weed_spawn_probability(eods: int, weed_chance: float = STANDARD_WEED_CHANCE) -> float:
    """Probability an always-empty tile becomes a weed within ``eods`` rolls."""
    eods = _plain_nonnegative_int(eods, "eods")
    p = _probability(weed_chance)
    return 1.0 - (1.0 - p) ** eods


def expected_empty_tile_rng_draws(eods: int, weed_chance: float = STANDARD_WEED_CHANCE) -> float:
    """Expected RNG draws consumed before weed occupancy stops later draws.

    An empty tile consumes one RNG draw per EOD until it spawns a weed. A
    structure consumes zero weed RNG draws while it occupies that tile.
    """
    eods = _plain_nonnegative_int(eods, "eods")
    p = _probability(weed_chance)
    if eods == 0:
        return 0.0
    if p == 0.0:
        return float(eods)
    return weed_spawn_probability(eods, p) / p


def occupancy_lease_receipt(
    eods: int,
    weed_chance: float = STANDARD_WEED_CHANCE,
    *,
    restore_with_dig: bool = True,
) -> dict:
    """Return labor/RNG accounting for one empty-tile structure lease.

    ``direct_action_delta`` is expected baseline weed-cleanup actions minus
    lease actions. Positive would favor the lease on weed labor alone.
    It cannot be positive: baseline can need at most one weed DIG, while the
    lease costs one BUILD and, when restored, one DIG.

    The RNG fields are telemetry only. They do not imply that moving the
    shared RNG cursor is beneficial or predictable.
    """
    if not isinstance(restore_with_dig, bool):
        raise WeedbankContractError("restore_with_dig must be bool")
    eods = _plain_nonnegative_int(eods, "eods")
    p = _probability(weed_chance)
    weed_probability = weed_spawn_probability(eods, p)
    build_actions = 1
    restore_actions = 1 if restore_with_dig else 0
    lease_actions = build_actions + restore_actions
    direct_action_delta = weed_probability - lease_actions
    return {
        "schema": "titan-v4/weedbank-occupancy-lease/v1",
        "source_engine_git_blob": ENGINE_GIT_BLOB,
        "eods": eods,
        "weed_chance": p,
        "weed_spawn_probability": weed_probability,
        "expected_baseline_weed_cleanup_actions": weed_probability,
        "expected_rng_draws_suppressed": expected_empty_tile_rng_draws(eods, p),
        "build_actions": build_actions,
        "restore_actions": restore_actions,
        "lease_actions": lease_actions,
        "direct_action_delta": direct_action_delta,
        "direct_weed_labor_advantage": direct_action_delta > 0.0,
        "rng_decision_authority": False,
        "hidden_seed_targeting_authority": False,
        "runtime_policy_authority": False,
        "verdict": "NO_DIRECT_WEED_LABOR_EDGE",
    }
