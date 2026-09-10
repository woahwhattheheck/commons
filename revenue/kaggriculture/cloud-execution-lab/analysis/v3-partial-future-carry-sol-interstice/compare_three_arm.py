# SPDX-License-Identifier: Apache-2.0
"""Validate and classify V2 control, strict rejection, and carry repair panels."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping

import bind_execution as binding
import materialize as lane

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
KAG = LAB.parent
ENGINE_DIR = LAB / "reference" / "engine"
LOADER = KAG / "20260907-offline-agent" / "evaluate.py"
ARLENE = (
    LAB
    / "runtime"
    / "variants"
    / "v1"
    / "reference"
    / "next-panel"
    / "vendor"
    / "arlene.py"
)
V1_ENTRY = LAB / "runtime" / "variants" / "v1" / "candidate.py"

OPERATION = lane.OPERATION
EXPECTED_ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
EXPECTED_ENGINE_SHA256 = {
    "kaggriculture.py": "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e",
    "kaggriculture.json": "a82c89c1a2315b93f39775d8e025471a01b738647c9772658368ee6b1b6f4867",
    "utils.py": "537b627b11784d424147ef57ebb0369b039bf83c9f891e81f10486b1f552334b",
}
EXPECTED_LOADER_SHA256 = "cd113a94ae99b03492502e425bdcf09c3db17a2aa2a8fd866f0d78caec9e311e"
EXPECTED_ARLENE_SHA256 = "1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4"
EXPECTED_V1_ENTRY_SHA256 = lane.EXPECTED_CANDIDATE_ENTRY_SHA256
EXPECTED_SEEDS = (539131249, 1834999074, 2609097301, 2611092207)
EXPECTED_RNG_SEED = 20260909
EXPECTED_EPISODE_STEPS = 720
EXPECTED_ACTIONS = 719
EXPECTED_GAMES = 16
EXPECTED_LIMITS = {
    "action_rpc_seconds": 1.0,
    "startup_seconds": 15.0,
    "game_seconds_between_steps": 180.0,
    "remaining_overage_time": 0.0,
}
EXPECTED_EVALUATOR_SOURCE_BLOB = "077feb2208b6e0c1727835eb4f8089709bf67f3b"
EXPECTED_EVALUATOR_SOURCE_SHA256 = (
    "e9a093ab6bccaa58289ba84ee62d4abec0aa85eae2a8dfc828964c4b6773c797"
)
EXPECTED_EVALUATOR_REPAIR = "sol-keel-candidate-action-digest-v1"
EXPECTED_EVALUATOR_SHA256 = (
    "53a2eb184d7bff6ca19ac2dbe45334d4d0587d26738e57f9a4cff31087e239dd"
)
EXPECTED_EVALUATOR_BLOB = "1736a5a59605c62904ddc37163c4ce7646d35dff"
EXPECTED_EVALUATOR_PATCHES = (
    {
        "label": "candidate digest initialization",
        "old_sha256": "98dd4b2c5a9d46e0ed1bc1ebc6d8d03bb282e4197f529bfeec63a9cce65c185f",
        "new_sha256": "ab70da21b70a3762a28f8a92b968ab460bab27024af71d5bb5ca3563d4993498",
        "old_occurrences_before": 1,
        "old_occurrences_after": 0,
        "new_occurrences_after": 1,
    },
    {
        "label": "pre-interpreter candidate action capture",
        "old_sha256": "60c9aae2f7cfc11042dbfdc6ac80786e9bb031ed9d9477ed450c55f6fed9cf8e",
        "new_sha256": "d165a435c6ca3de362bb4ff6a4ee1696ae11824a4bcbe081605244f4ff5d0653",
        "old_occurrences_before": 1,
        "old_occurrences_after": 0,
        "new_occurrences_after": 1,
    },
    {
        "label": "candidate digest publication",
        "old_sha256": "4f79373792a25b3d169e16fcd020cc9019f6973176d90ea81ef2f664b2921074",
        "new_sha256": "2e92fc7cafc0a669ca7251186bf63e8160c6bc1d8000248b227dfd7be428fc52",
        "old_occurrences_before": 1,
        "old_occurrences_after": 0,
        "new_occurrences_after": 1,
    },
)
COMMON_RUNTIME_FIELDS = ("python", "platform", "method")


class ClassificationError(ValueError):
    """The panel evidence is incomplete, mismatched, or non-finite."""


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ClassificationError(f"{label} is not an object")
    return value


def digest(value: Any, label: str, length: int = 64) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ClassificationError(f"{label} is not a lowercase hex digest")
    return value


def finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ClassificationError(f"{label} is not numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ClassificationError(f"{label} is not finite")
    return result


def exact_number(value: Any, expected: float, label: str) -> None:
    parsed = finite_number(value, label)
    if parsed != expected:
        raise ClassificationError(
            f"{label} mismatch: expected {expected}, got {value!r}"
        )


def finite_pair(value: Any, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 2:
        raise ClassificationError(f"{label} is not a two-value list")
    return [finite_number(item, f"{label}[{index}]") for index, item in enumerate(value)]


def expected_opponents() -> dict[str, dict[str, str]]:
    return {
        "arlene": {
            "entry": "arlene.py",
            "callable": "agent",
            "sha256": EXPECTED_ARLENE_SHA256,
        },
        "v1": {
            "entry": "candidate.py",
            "callable": "agent",
            "sha256": EXPECTED_V1_ENTRY_SHA256,
        },
    }


def validate_live_source_bank() -> None:
    expected_files = {
        "kaggriculture.py": ENGINE_DIR / "kaggriculture.py",
        "kaggriculture.json": ENGINE_DIR / "kaggriculture.json",
        "utils.py": ENGINE_DIR / "utils.py",
    }
    for name, path in expected_files.items():
        if digest_file(path) != EXPECTED_ENGINE_SHA256[name]:
            raise ClassificationError(f"live engine file drifted: {name}")
    if digest_file(LOADER) != EXPECTED_LOADER_SHA256:
        raise ClassificationError("live evaluator loader drifted")
    if digest_file(ARLENE) != EXPECTED_ARLENE_SHA256:
        raise ClassificationError("live Arlene opponent drifted")
    if digest_file(V1_ENTRY) != EXPECTED_V1_ENTRY_SHA256:
        raise ClassificationError("live V1 opponent drifted")


def validate_evaluator_receipt(receipt: Mapping[str, Any], evaluator: Path) -> None:
    if receipt.get("schema_version") != 1:
        raise ClassificationError("evaluator receipt schema mismatch")
    if receipt.get("operation") != binding.STRICT_OPERATION:
        raise ClassificationError("evaluator receipt operation mismatch")
    if receipt.get("repair") != EXPECTED_EVALUATOR_REPAIR:
        raise ClassificationError("evaluator receipt repair identity mismatch")

    source = mapping(receipt.get("source"), "evaluator source")
    expected_source = {
        "path_name": "evaluate.py",
        "git_blob_sha1": EXPECTED_EVALUATOR_SOURCE_BLOB,
        "sha256": EXPECTED_EVALUATOR_SOURCE_SHA256,
        "bytes": 36057,
    }
    if dict(source) != expected_source:
        raise ClassificationError("evaluator source identity mismatch")

    patched = mapping(receipt.get("patched"), "patched evaluator")
    if patched.get("path_name") != evaluator.name:
        raise ClassificationError("patched evaluator path identity mismatch")
    if patched.get("sha256") != EXPECTED_EVALUATOR_SHA256:
        raise ClassificationError("patched evaluator SHA-256 mismatch")
    if patched.get("git_blob_sha1") != EXPECTED_EVALUATOR_BLOB:
        raise ClassificationError("patched evaluator blob mismatch")
    if patched.get("bytes") != 36321:
        raise ClassificationError("patched evaluator byte count mismatch")
    if patched.get("candidate_action_field") != "candidate_action_sha256":
        raise ClassificationError("candidate action field mismatch")
    if patched.get("candidate_action_count_field") != "candidate_action_count":
        raise ClassificationError("candidate action count field mismatch")
    if patched.get("capture_phase") != "after both returned actions, before interpreter":
        raise ClassificationError("candidate action capture phase mismatch")
    patches = patched.get("patches")
    if not isinstance(patches, list) or patches != list(EXPECTED_EVALUATOR_PATCHES):
        raise ClassificationError("evaluator patch ledger mismatch")

    data = evaluator.resolve(strict=True).read_bytes()
    if lane.sha256(data) != EXPECTED_EVALUATOR_SHA256:
        raise ClassificationError("patched evaluator file does not match receipt")
    if lane.git_blob_sha1(data) != EXPECTED_EVALUATOR_BLOB:
        raise ClassificationError("patched evaluator file blob mismatch")


def validate_binding(
    receipt: Mapping[str, Any],
    arms_root: Path,
    strict_receipt_path: Path,
    repair_receipt_path: Path,
) -> dict[str, Mapping[str, Any]]:
    if receipt.get("schema_version") != 1 or receipt.get("operation") != OPERATION:
        raise ClassificationError("binding receipt identity mismatch")
    if receipt.get("strict_operation") != binding.STRICT_OPERATION:
        raise ClassificationError("binding strict operation mismatch")
    if receipt.get("strict_receipt_sha256") != digest_file(strict_receipt_path):
        raise ClassificationError("binding strict receipt digest mismatch")
    if receipt.get("repair_receipt_sha256") != digest_file(repair_receipt_path):
        raise ClassificationError("binding repair receipt digest mismatch")
    arms = receipt.get("arms")
    if not isinstance(arms, Mapping) or set(arms) != {"control", "strict", "repair"}:
        raise ClassificationError("binding arm set mismatch")

    expected_identity = {
        "control": (
            binding.EXPECTED_SOURCE_CLOSURE,
            lane.EXPECTED_V2_SCHEDULER_SHA256,
        ),
        "strict": (
            binding.EXPECTED_STRICT_CLOSURE,
            binding.EXPECTED_STRICT_SCHEDULER_SHA256,
        ),
        "repair": (
            binding.EXPECTED_REPAIR_CLOSURE,
            lane.EXPECTED_PATCHED_SCHEDULER_SHA256,
        ),
    }
    normalized: dict[str, Mapping[str, Any]] = {}
    for arm, expected in arms.items():
        expected = mapping(expected, f"binding arm {arm}")
        closure, scheduler_sha256 = expected_identity[arm]
        if expected.get("payload_closure_sha256") != closure:
            raise ClassificationError(f"{arm} binding payload closure mismatch")
        if expected.get("scheduler_sha256") != scheduler_sha256:
            raise ClassificationError(f"{arm} binding scheduler mismatch")
        if expected.get("payload_entry_sha256") != lane.EXPECTED_CANDIDATE_ENTRY_SHA256:
            raise ClassificationError(f"{arm} binding entry mismatch")
        if expected.get("wrapper") != f"{arm}/bound_entry.py::agent":
            raise ClassificationError(f"{arm} binding wrapper path mismatch")
        wrapper_sha256 = digest(expected.get("wrapper_sha256"), f"{arm} wrapper")
        wrapper_blob = digest(
            expected.get("wrapper_git_blob_sha1"), f"{arm} wrapper blob", 40
        )

        arm_root = arms_root.resolve(strict=True) / arm
        wrapper = arm_root / "bound_entry.py"
        payload = arm_root / "payload"
        data = wrapper.read_bytes()
        if lane.sha256(data) != wrapper_sha256:
            raise ClassificationError(f"{arm} wrapper digest mismatch")
        if lane.git_blob_sha1(data) != wrapper_blob:
            raise ClassificationError(f"{arm} wrapper blob mismatch")
        inventory = lane.inventory(payload)
        if lane.closure_sha256(inventory) != closure:
            raise ClassificationError(f"{arm} bound payload closure mismatch")
        if inventory.get("scheduler.py", {}).get("sha256") != scheduler_sha256:
            raise ClassificationError(f"{arm} bound scheduler mismatch")
        if inventory.get("candidate.py", {}).get("sha256") != (
            lane.EXPECTED_CANDIDATE_ENTRY_SHA256
        ):
            raise ClassificationError(f"{arm} bound entry mismatch")
        normalized[arm] = expected

    if len({row["wrapper_sha256"] for row in normalized.values()}) != 3:
        raise ClassificationError("bound wrapper identities are not distinct")
    return normalized


def game_key(game: Mapping[str, Any]) -> tuple[str, int, int]:
    opponent = game.get("opponent")
    seed = game.get("seed")
    seat = game.get("candidate_seat")
    if not isinstance(opponent, str) or not opponent:
        raise ClassificationError("game opponent is invalid")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ClassificationError("game seed is invalid")
    if isinstance(seat, bool) or not isinstance(seat, int) or seat not in (0, 1):
        raise ClassificationError("game candidate_seat is invalid")
    return opponent, seed, seat


def validate_daily_bank(value: Any, arm: str, key: tuple[str, int, int]) -> list[dict]:
    if not isinstance(value, list) or not value:
        raise ClassificationError(f"{arm} game {key} daily bank missing")
    normalized = []
    previous = -1
    for index, raw in enumerate(value):
        row = mapping(raw, f"{arm} game {key} daily bank {index}")
        step = row.get("step")
        if isinstance(step, bool) or not isinstance(step, int) or step <= previous:
            raise ClassificationError(f"{arm} game {key} daily bank step invalid")
        normalized.append({"step": step, "bank": finite_pair(row.get("bank"), "daily bank")})
        previous = step
    return normalized


def validate_actor(
    raw: Any, *, arm: str, key: tuple[str, int, int], actor_index: int
) -> None:
    actor = mapping(raw, f"{arm} game {key} actor {actor_index}")
    calls = actor.get("calls")
    exit_code = actor.get("exit_code")
    if (
        isinstance(calls, bool)
        or not isinstance(calls, int)
        or calls != EXPECTED_ACTIONS
        or isinstance(exit_code, bool)
        or not isinstance(exit_code, int)
        or exit_code != 0
    ):
        raise ClassificationError(f"{arm} game {key} actor {actor_index} failed")
    if finite_number(
        actor.get("max_call_seconds"),
        f"{arm} game {key} actor {actor_index} max call",
    ) > EXPECTED_LIMITS["action_rpc_seconds"]:
        raise ClassificationError(f"{arm} game {key} actor {actor_index} timed out")


def validate_panel(
    panel: Mapping[str, Any],
    *,
    arm: str,
    binding_arm: Mapping[str, Any],
) -> tuple[dict[tuple[str, int, int], dict[str, Any]], str]:
    if panel.get("schema_version") != 1:
        raise ClassificationError(f"{arm} panel schema mismatch")
    invocation = digest(panel.get("invocation_id"), f"{arm} invocation", 32)
    if panel.get("engine_ref") != EXPECTED_ENGINE_REF:
        raise ClassificationError(f"{arm} panel engine ref mismatch")
    if panel.get("engine_sha256") != EXPECTED_ENGINE_SHA256:
        raise ClassificationError(f"{arm} panel engine source map mismatch")
    if panel.get("loader_sha256") != EXPECTED_LOADER_SHA256:
        raise ClassificationError(f"{arm} panel loader mismatch")
    if panel.get("evaluator_sha256") != EXPECTED_EVALUATOR_SHA256:
        raise ClassificationError(f"{arm} panel evaluator mismatch")

    candidate = mapping(panel.get("candidate"), f"{arm} panel candidate")
    if candidate.get("entry") != "bound_entry.py":
        raise ClassificationError(f"{arm} panel used the wrong entry file")
    if candidate.get("callable") != "agent":
        raise ClassificationError(f"{arm} panel callable mismatch")
    if candidate.get("sha256") != binding_arm.get("wrapper_sha256"):
        raise ClassificationError(f"{arm} panel did not execute the bound wrapper")

    if panel.get("opponents") != expected_opponents():
        raise ClassificationError(f"{arm} panel opponent identity mismatch")
    seeds = panel.get("seeds")
    if (
        not isinstance(seeds, list)
        or tuple(seeds) != EXPECTED_SEEDS
        or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds)
    ):
        raise ClassificationError(f"{arm} exact seed grid mismatch")
    if panel.get("agent_rng_seed") != EXPECTED_RNG_SEED:
        raise ClassificationError(f"{arm} agent RNG seed mismatch")

    python = panel.get("python")
    platform = panel.get("platform")
    method = panel.get("method")
    if not isinstance(python, str) or not python:
        raise ClassificationError(f"{arm} Python identity missing")
    if not isinstance(platform, str) or not platform:
        raise ClassificationError(f"{arm} platform identity missing")
    if not isinstance(method, str) or "Official interpreter" not in method:
        raise ClassificationError(f"{arm} evaluator method identity missing")

    limits = mapping(panel.get("limits"), f"{arm} limits")
    if set(limits) != set(EXPECTED_LIMITS):
        raise ClassificationError(f"{arm} limit keys mismatch")
    for name, expected in EXPECTED_LIMITS.items():
        exact_number(limits.get(name), expected, f"{arm} limit {name}")

    progress = mapping(panel.get("progress"), f"{arm} progress")
    if (
        progress.get("state") != "complete"
        or progress.get("phase") != "finalize"
        or progress.get("planned_games") != EXPECTED_GAMES
        or progress.get("recorded_games") != EXPECTED_GAMES
        or progress.get("active_game") is not None
    ):
        raise ClassificationError(f"{arm} panel did not finalize exactly")

    games = panel.get("games")
    if not isinstance(games, list) or len(games) != EXPECTED_GAMES:
        raise ClassificationError(
            f"{arm} expected {EXPECTED_GAMES} games, found "
            f"{len(games) if isinstance(games, list) else 'non-list'}"
        )

    cells: dict[tuple[str, int, int], dict[str, Any]] = {}
    for index, raw in enumerate(games):
        game = mapping(raw, f"{arm} game {index}")
        key = game_key(game)
        if key in cells:
            raise ClassificationError(f"{arm} duplicate game cell {key}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise ClassificationError(f"{arm} game {key} failed")
        steps = game.get("steps")
        episode_steps = game.get("episode_steps")
        if (
            isinstance(steps, bool)
            or not isinstance(steps, int)
            or steps != EXPECTED_ACTIONS
            or isinstance(episode_steps, bool)
            or not isinstance(episode_steps, int)
            or episode_steps != EXPECTED_EPISODE_STEPS
        ):
            raise ClassificationError(f"{arm} game {key} step contract mismatch")

        scores = finite_pair(game.get("scores"), f"{arm} game {key} scores")
        seat = key[2]
        bank = finite_pair(game.get("bank_snapshot"), f"{arm} game {key} bank")
        if bank != scores:
            raise ClassificationError(f"{arm} game {key} bank snapshot mismatch")

        action_sha256 = digest(
            game.get("candidate_action_sha256"),
            f"{arm} game {key} candidate action",
        )
        count = game.get("candidate_action_count")
        if (
            isinstance(count, bool)
            or not isinstance(count, int)
            or count != EXPECTED_ACTIONS
        ):
            raise ClassificationError(f"{arm} game {key} action count mismatch")
        trace_sha256 = digest(game.get("trace_sha256"), f"{arm} game {key} trace")

        daily = validate_daily_bank(game.get("daily_bank"), arm, key)
        if daily[-1]["step"] != 718 or daily[-1]["bank"] != scores:
            raise ClassificationError(f"{arm} game {key} final daily bank mismatch")

        actors = game.get("actors")
        if not isinstance(actors, list) or len(actors) != 2:
            raise ClassificationError(f"{arm} game {key} actor evidence missing")
        for actor_index, actor in enumerate(actors):
            validate_actor(actor, arm=arm, key=key, actor_index=actor_index)

        cells[key] = {
            "own": scores[seat],
            "rival": scores[1 - seat],
            "margin": scores[seat] - scores[1 - seat],
            "action_sha256": action_sha256,
            "trace_sha256": trace_sha256,
            "daily_bank": daily,
        }

    expected_keys = {
        (opponent, seed, seat)
        for opponent in expected_opponents()
        for seed in EXPECTED_SEEDS
        for seat in (0, 1)
    }
    if set(cells) != expected_keys:
        raise ClassificationError(f"{arm} panel cell set mismatch")
    return cells, invocation


def first_bank_divergence(left: list, right: list) -> int | None:
    if len(left) != len(right):
        raise ClassificationError("daily bank lengths differ")
    for a, b in zip(left, right):
        if a["step"] != b["step"]:
            raise ClassificationError("daily bank step identities differ")
        if a["bank"] != b["bank"]:
            return int(a["step"])
    return None


def summarize_comparison(
    base: Mapping[tuple[str, int, int], Mapping[str, Any]],
    candidate: Mapping[tuple[str, int, int], Mapping[str, Any]],
) -> dict[str, Any]:
    if set(base) != set(candidate):
        raise ClassificationError("paired comparison cell sets differ")
    rows = []
    for key in sorted(base):
        opponent, seed, seat = key
        before = base[key]
        after = candidate[key]
        own_delta = after["own"] - before["own"]
        rival_delta = after["rival"] - before["rival"]
        rows.append(
            {
                "opponent": opponent,
                "seed": seed,
                "candidate_seat": seat,
                "own_delta": own_delta,
                "rival_delta": rival_delta,
                "margin_delta": own_delta - rival_delta,
                "action_changed": before["action_sha256"] != after["action_sha256"],
                "trace_changed": before["trace_sha256"] != after["trace_sha256"],
                "first_daily_bank_divergence": first_bank_divergence(
                    before["daily_bank"], after["daily_bank"]
                ),
            }
        )
    own = [row["own_delta"] for row in rows]
    rival = [row["rival_delta"] for row in rows]
    margin = [row["margin_delta"] for row in rows]
    subgroups: dict[str, list[float]] = {}
    for row in rows:
        name = f"{row['opponent']}/seat-{row['candidate_seat']}"
        subgroups.setdefault(name, []).append(row["own_delta"])
    return {
        "cells": len(rows),
        "changed_action_cells": sum(row["action_changed"] for row in rows),
        "changed_trace_cells": sum(row["trace_changed"] for row in rows),
        "mean_own_delta": statistics.fmean(own),
        "median_own_delta": statistics.median(own),
        "min_own_delta": min(own),
        "max_own_delta": max(own),
        "positive_own_cells": sum(value > 0 for value in own),
        "zero_own_cells": sum(value == 0 for value in own),
        "negative_own_cells": sum(value < 0 for value in own),
        "mean_rival_delta": statistics.fmean(rival),
        "mean_margin_delta": statistics.fmean(margin),
        "subgroup_mean_own_delta": {
            name: statistics.fmean(values) for name, values in sorted(subgroups.items())
        },
        "first_divergence_steps": sorted(
            {
                row["first_daily_bank_divergence"]
                for row in rows
                if row["first_daily_bank_divergence"] is not None
            }
        ),
        "rows": rows,
    }


def classify(
    control: Mapping[str, Any],
    strict: Mapping[str, Any],
    repair: Mapping[str, Any],
    binding_arms: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    control_cells, control_invocation = validate_panel(
        control, arm="control", binding_arm=binding_arms["control"]
    )
    strict_cells, strict_invocation = validate_panel(
        strict, arm="strict", binding_arm=binding_arms["strict"]
    )
    repair_cells, repair_invocation = validate_panel(
        repair, arm="repair", binding_arm=binding_arms["repair"]
    )
    if len({control_invocation, strict_invocation, repair_invocation}) != 3:
        raise ClassificationError("the three arm invocations are not distinct")
    for field in COMMON_RUNTIME_FIELDS:
        if strict.get(field) != control.get(field) or repair.get(field) != control.get(field):
            raise ClassificationError(f"panel common runtime mismatch at {field}")

    strict_vs_control = summarize_comparison(control_cells, strict_cells)
    repair_vs_control = summarize_comparison(control_cells, repair_cells)
    repair_vs_strict = summarize_comparison(strict_cells, repair_cells)

    rc = repair_vs_control
    rs = repair_vs_strict
    if rc["changed_action_cells"] == 0:
        verdict = "NO_REPAIR_ACTION_CHANGE"
    elif rc["mean_own_delta"] <= 0:
        verdict = "REPAIR_NO_MEAN_UPSIDE"
    elif rc["negative_own_cells"]:
        verdict = "REPAIR_MIXED_UPSIDE"
    elif rs["mean_own_delta"] > 0 and rs["negative_own_cells"] == 0:
        verdict = "REPAIR_DOMINATES_CONTROL_AND_STRICT"
    else:
        verdict = "REPAIR_BEATS_CONTROL"
    passes = verdict in {
        "REPAIR_DOMINATES_CONTROL_AND_STRICT",
        "REPAIR_BEATS_CONTROL",
    }

    preferred = "control"
    if (
        strict_vs_control["mean_own_delta"] > 0
        and strict_vs_control["negative_own_cells"] == 0
    ):
        preferred = "strict"
    if (
        passes
        and repair_vs_strict["mean_own_delta"] >= 0
        and repair_vs_strict["negative_own_cells"] == 0
    ):
        preferred = "repair"
    return {
        "verdict": verdict,
        "passes_no_negative_control_screen": passes,
        "preferred_arm_under_no_negative_guard": preferred,
        "invocations": {
            "control": control_invocation,
            "strict": strict_invocation,
            "repair": repair_invocation,
        },
        "strict_vs_control": strict_vs_control,
        "repair_vs_control": repair_vs_control,
        "repair_vs_strict": repair_vs_strict,
    }


def markdown(report: Mapping[str, Any]) -> str:
    comparisons = report["comparisons"]
    lines = [
        "# Titan V3 partial-future carry screen",
        "",
        f"**Verdict:** `{comparisons['verdict']}`",
        "**Preferred arm under no-negative guard:** "
        f"`{comparisons['preferred_arm_under_no_negative_guard']}`",
        "",
        "This is a closure-bound causal panel, not Kaggle leaderboard or release authority.",
        "",
        "| comparison | mean own | median | min | max | + / 0 / - | changed actions |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label in ("strict_vs_control", "repair_vs_control", "repair_vs_strict"):
        row = comparisons[label]
        lines.append(
            f"| {label} | {row['mean_own_delta']:.3f} | "
            f"{row['median_own_delta']:.3f} | {row['min_own_delta']:.3f} | "
            f"{row['max_own_delta']:.3f} | {row['positive_own_cells']} / "
            f"{row['zero_own_cells']} / {row['negative_own_cells']} | "
            f"{row['changed_action_cells']} |"
        )
    lines.extend(
        [
            "",
            "## Repair activation",
            "",
            "First differing daily-bank checkpoints: "
            f"`{comparisons['repair_vs_control']['first_divergence_steps']}`",
            "",
            "The source theorem for the pinned public seed is 24 units liquidated "
            "by V2 versus a 14-unit minimum-capacity sale with 10 units retained "
            "as carry.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--strict", type=Path, required=True)
    parser.add_argument("--repair", type=Path, required=True)
    parser.add_argument("--binding-receipt", type=Path, required=True)
    parser.add_argument("--strict-receipt", type=Path, required=True)
    parser.add_argument("--repair-receipt", type=Path, required=True)
    parser.add_argument("--evaluator-receipt", type=Path, required=True)
    parser.add_argument("--arms-root", type=Path, required=True)
    parser.add_argument("--patched-evaluator", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    validate_live_source_bank()
    strict_receipt = binding.strict_object(args.strict_receipt)
    repair_receipt = binding.strict_object(args.repair_receipt)
    binding.validate_strict_receipt(strict_receipt)
    binding.validate_repair_receipt(repair_receipt)
    evaluator_receipt = binding.strict_object(args.evaluator_receipt)
    validate_evaluator_receipt(evaluator_receipt, args.patched_evaluator)
    binding_receipt = binding.strict_object(args.binding_receipt)
    binding_arms = validate_binding(
        binding_receipt,
        args.arms_root,
        args.strict_receipt,
        args.repair_receipt,
    )
    control = binding.strict_object(args.control)
    strict = binding.strict_object(args.strict)
    repair = binding.strict_object(args.repair)
    comparisons = classify(control, strict, repair, binding_arms)
    report = {
        "schema_version": 1,
        "operation": OPERATION,
        "head": args.head,
        "identities": {
            "control_sha256": digest_file(args.control),
            "strict_sha256": digest_file(args.strict),
            "repair_sha256": digest_file(args.repair),
            "binding_sha256": digest_file(args.binding_receipt),
            "strict_materialization_sha256": digest_file(args.strict_receipt),
            "repair_materialization_sha256": digest_file(args.repair_receipt),
            "evaluator_materialization_sha256": digest_file(args.evaluator_receipt),
            "patched_evaluator_sha256": digest_file(args.patched_evaluator),
        },
        "comparisons": comparisons,
    }
    lane.atomic_write(
        args.output,
        (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(
            "utf-8"
        ),
    )
    lane.atomic_write(args.markdown, markdown(report).encode("utf-8"))
    print(
        json.dumps(
            {
                "verdict": comparisons["verdict"],
                "preferred": comparisons["preferred_arm_under_no_negative_guard"],
                "repair_mean_own_delta": comparisons["repair_vs_control"][
                    "mean_own_delta"
                ],
                "repair_negative_cells": comparisons["repair_vs_control"][
                    "negative_own_cells"
                ],
            },
            sort_keys=True,
        )
    )
    return 0 if comparisons["passes_no_negative_control_screen"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
