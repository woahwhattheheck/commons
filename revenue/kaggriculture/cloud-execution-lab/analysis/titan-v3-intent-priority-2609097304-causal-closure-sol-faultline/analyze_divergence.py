#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Recompute the exact intent-priority activation and first-divergence verdict."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
from itertools import zip_longest
from typing import Any, Iterable

ARCHIVE_SHA256 = "5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1"
SOURCE_SHA256 = "3249398b6aa56d1b3464db8d0cce5aa35e8edee397fc4341bd710d1f74dad469"
FROZEN_SELECTED_GIT_BLOB = "fc7baf5c179818a55037f6a61d92984d81d1a21c"
EVALUATOR_GIT_BLOB = "077feb2208b6e0c1727835eb4f8089709bf67f3b"
OPERATION = "titan-v3-intent-priority-2609097304-causal-closure-20260910-01"
EVALUATOR_OPERATION = "titan-v3-intent-priority-first-divergence-evaluator-20260910-01"
OPPONENT = "arlene"
SEEDS = (
    2609097304,
    539131249,
    1834999074,
    2609097301,
    2609097302,
    2609097303,
    2611092201,
    2611092207,
)
EXPECTED_STEPS = 719
ENGINE_FILES = ("kaggriculture.py", "kaggriculture.json", "utils.py")


class EvidenceError(ValueError):
    """The reports are incomplete, malformed, or not bound to the declared run."""


def strict_load(path: Path, label: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise EvidenceError(f"{label} has duplicate key {key!r}")
            out[key] = value
        return out

    def reject(value: str) -> Any:
        raise EvidenceError(f"{label} has non-finite JSON constant {value}")

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=pairs,
            parse_constant=reject,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot load {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} root must be an object")
    return value


def encoded(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise EvidenceError(f"value is not canonical JSON: {exc}") from exc


def sha256_value(value: Any) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def sha256_file(path: Path, label: str) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise EvidenceError(f"cannot read {label}: {exc}") from exc


def runtime_binding(opponent_source: Path, loader: Path, engine_dir: Path) -> dict[str, Any]:
    opponent_source = opponent_source.resolve(strict=True)
    loader = loader.resolve(strict=True)
    engine_dir = engine_dir.resolve(strict=True)
    engines = {name: sha256_file(engine_dir / name, f"engine {name}") for name in ENGINE_FILES}
    return {
        "opponent_sha256": sha256_file(opponent_source, "Arlene source"),
        "opponent_entry": opponent_source.name,
        "loader_sha256": sha256_file(loader, "loader"),
        "engine_sha256": engines,
    }


def digest(value: Any, label: str, length: int = 64) -> str:
    if not isinstance(value, str) or len(value) != length or value.lower() != value:
        raise EvidenceError(f"{label} must be lowercase {length}-hex")
    try:
        int(value, 16)
    except ValueError as exc:
        raise EvidenceError(f"{label} must be lowercase {length}-hex") from exc
    return value


def true_int(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise EvidenceError(f"{label} must be an integer >= {minimum}")
    return value


def finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise EvidenceError(f"{label} must be finite")
    return result


def exact_keys() -> set[tuple[str, int, int]]:
    return {(OPPONENT, seed, seat) for seed in SEEDS for seat in (0, 1)}


def validate_receipts(
    pair: dict[str, Any],
    evaluator: dict[str, Any],
    head: str | None,
    runtime: dict[str, Any],
) -> dict[str, Any]:
    if pair.get("schema_version") != 1 or pair.get("operation") != OPERATION:
        raise EvidenceError("pair receipt operation/schema mismatch")
    if head is not None and pair.get("git_head") != head:
        raise EvidenceError("pair receipt does not bind the requested Git head")
    archive = pair.get("archive")
    source = pair.get("source_manifest")
    factor = pair.get("factor")
    arms = pair.get("arms")
    if not all(isinstance(value, dict) for value in (archive, source, factor, arms)):
        raise EvidenceError("pair receipt lacks bound objects")
    if archive.get("sha256") != ARCHIVE_SHA256 or archive.get("bytes") != 428158:
        raise EvidenceError("pair archive identity mismatch")
    if source.get("sha256") != SOURCE_SHA256 or source.get("runtime_files") != 109:
        raise EvidenceError("pair source-manifest identity mismatch")
    if factor.get("source_git_blob_sha1") != FROZEN_SELECTED_GIT_BLOB:
        raise EvidenceError("pair frozen_selected source mismatch")
    if pair.get("only_runtime_delta") != ["frozen_selected.py"]:
        raise EvidenceError("pair declares an unexpected runtime delta")
    if set(arms) != {"control", "candidate"}:
        raise EvidenceError("pair arms mismatch")
    for mode in ("control", "candidate"):
        arm = arms[mode]
        if not isinstance(arm, dict):
            raise EvidenceError(f"{mode} arm is malformed")
        digest(arm.get("frozen_selected_sha256"), f"{mode} frozen SHA-256")
        digest(arm.get("frozen_selected_git_blob_sha1"), f"{mode} frozen Git blob", 40)
        digest(arm.get("entry_sha256"), f"{mode} entry SHA-256")
    if arms["control"]["frozen_selected_git_blob_sha1"] != FROZEN_SELECTED_GIT_BLOB:
        raise EvidenceError("control arm does not preserve frozen_selected")
    if arms["candidate"]["frozen_selected_git_blob_sha1"] == FROZEN_SELECTED_GIT_BLOB:
        raise EvidenceError("candidate arm failed to patch frozen_selected")

    if evaluator.get("schema_version") != 1 or evaluator.get("operation") != EVALUATOR_OPERATION:
        raise EvidenceError("evaluator receipt operation/schema mismatch")
    source_eval = evaluator.get("source")
    patched_eval = evaluator.get("patched")
    if not isinstance(source_eval, dict) or not isinstance(patched_eval, dict):
        raise EvidenceError("evaluator receipt lacks source/patched objects")
    if source_eval.get("git_blob_sha1") != EVALUATOR_GIT_BLOB:
        raise EvidenceError("evaluator source Git blob mismatch")
    if patched_eval.get("capture_phase") != "after both returned actions, before official interpreter":
        raise EvidenceError("evaluator capture phase mismatch")
    for key in ("opponent_sha256", "loader_sha256"):
        digest(runtime.get(key), f"runtime {key}")
    if runtime.get("opponent_entry") != "arlene.py":
        raise EvidenceError("runtime opponent entry must be arlene.py")
    engine_sha = runtime.get("engine_sha256")
    if not isinstance(engine_sha, dict) or set(engine_sha) != set(ENGINE_FILES):
        raise EvidenceError("runtime engine file set mismatch")
    for name in ENGINE_FILES:
        digest(engine_sha.get(name), f"runtime engine {name} SHA-256")
    return {
        "patched_evaluator_sha256": digest(
            patched_eval.get("sha256"), "patched evaluator SHA-256"
        ),
        "control_entry_sha256": arms["control"]["entry_sha256"],
        "candidate_entry_sha256": arms["candidate"]["entry_sha256"],
        **runtime,
    }


def index_report(
    report: dict[str, Any], mode: str, binding: dict[str, str]
) -> dict[tuple[str, int, int], dict[str, Any]]:
    if report.get("schema_version") != 1:
        raise EvidenceError(f"{mode} report schema mismatch")
    if report.get("evaluator_sha256") != binding["patched_evaluator_sha256"]:
        raise EvidenceError(f"{mode} report evaluator mismatch")
    if report.get("loader_sha256") != binding["loader_sha256"]:
        raise EvidenceError(f"{mode} report loader mismatch")
    if report.get("engine_sha256") != binding["engine_sha256"]:
        raise EvidenceError(f"{mode} report engine-source mismatch")
    candidate_fingerprint = report.get("candidate")
    expected_entry = f"{mode}_entry.py"
    if (
        not isinstance(candidate_fingerprint, dict)
        or candidate_fingerprint.get("entry") != expected_entry
        or candidate_fingerprint.get("callable") != "agent"
        or candidate_fingerprint.get("sha256") != binding[f"{mode}_entry_sha256"]
    ):
        raise EvidenceError(f"{mode} report candidate-entry mismatch")
    if tuple(report.get("seeds", ())) != SEEDS:
        raise EvidenceError(f"{mode} report seed order/set mismatch")
    opponents = report.get("opponents")
    if not isinstance(opponents, dict) or set(opponents) != {OPPONENT}:
        raise EvidenceError(f"{mode} report opponent grid mismatch")
    rival_fingerprint = opponents[OPPONENT]
    if (
        not isinstance(rival_fingerprint, dict)
        or rival_fingerprint.get("entry") != binding["opponent_entry"]
        or rival_fingerprint.get("callable") != "agent"
        or rival_fingerprint.get("sha256") != binding["opponent_sha256"]
    ):
        raise EvidenceError(f"{mode} report opponent-source mismatch")
    progress = report.get("progress")
    games = report.get("games")
    if not isinstance(progress, dict) or progress.get("state") != "complete":
        raise EvidenceError(f"{mode} report is not complete")
    if not isinstance(games, list):
        raise EvidenceError(f"{mode} games must be a list")
    planned = true_int(progress.get("planned_games"), f"{mode} planned games", 1)
    recorded = true_int(progress.get("recorded_games"), f"{mode} recorded games", 1)
    if planned != recorded or recorded != len(games) or recorded != len(exact_keys()):
        raise EvidenceError(f"{mode} report game cardinality mismatch")
    reproduction = report.get("reproducibility")
    if not isinstance(reproduction, dict) or reproduction.get("checked") is not True:
        raise EvidenceError(f"{mode} report lacks deterministic recheck")
    if reproduction.get("same_trace_and_scores") is not True:
        raise EvidenceError(f"{mode} deterministic recheck failed")

    result: dict[tuple[str, int, int], dict[str, Any]] = {}
    for offset, game in enumerate(games):
        if not isinstance(game, dict):
            raise EvidenceError(f"{mode} game {offset} is not an object")
        key = (
            str(game.get("opponent")),
            true_int(game.get("seed"), f"{mode} game seed"),
            true_int(game.get("candidate_seat"), f"{mode} candidate seat"),
        )
        if key in result:
            raise EvidenceError(f"{mode} duplicate game cell {key}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise EvidenceError(f"{mode} game {key} is not complete")
        if true_int(game.get("episode_steps"), f"{mode} episode steps") != 720:
            raise EvidenceError(f"{mode} game {key} episode length drift")
        if true_int(game.get("steps"), f"{mode} steps") != EXPECTED_STEPS:
            raise EvidenceError(f"{mode} game {key} callback count drift")
        scores = game.get("scores")
        bank = game.get("bank_snapshot")
        if not isinstance(scores, list) or len(scores) != 2:
            raise EvidenceError(f"{mode} game {key} scores malformed")
        if not isinstance(bank, list) or len(bank) != 2:
            raise EvidenceError(f"{mode} game {key} bank snapshot malformed")
        score_values = [finite(value, f"{mode} score {key}") for value in scores]
        bank_values = [finite(value, f"{mode} bank {key}") for value in bank]
        if score_values != bank_values:
            raise EvidenceError(f"{mode} game {key} scores differ from terminal bank")
        digest(game.get("trace_sha256"), f"{mode} trace SHA-256 {key}")
        timeline = game.get("candidate_timeline")
        if not isinstance(timeline, list) or len(timeline) != EXPECTED_STEPS:
            raise EvidenceError(f"{mode} game {key} timeline cardinality mismatch")
        for step, row in enumerate(timeline):
            if not isinstance(row, dict) or row.get("step") != step:
                raise EvidenceError(f"{mode} game {key} timeline step {step} malformed")
            digest(row.get("pre_world_sha256"), f"{mode} pre-world {key}/{step}")
            digest(row.get("post_world_sha256"), f"{mode} post-world {key}/{step}")
            action = row.get("tested_action")
            rival = row.get("rival_action")
            if not isinstance(action, dict) or not isinstance(rival, dict):
                raise EvidenceError(f"{mode} game {key} action {step} malformed")
            if digest(row.get("tested_action_sha256"), f"{mode} tested action {key}/{step}") != sha256_value(action):
                raise EvidenceError(f"{mode} game {key} tested action digest mismatch at {step}")
            if digest(row.get("rival_action_sha256"), f"{mode} rival action {key}/{step}") != sha256_value(rival):
                raise EvidenceError(f"{mode} game {key} rival action digest mismatch at {step}")
            debug = row.get("debug")
            if not isinstance(debug, dict) or debug.get("schema_version") != 1:
                raise EvidenceError(f"{mode} game {key} debug {step} malformed")
            if debug.get("mode") != mode or debug.get("step") != step or debug.get("player") != key[2]:
                raise EvidenceError(f"{mode} game {key} debug identity mismatch at {step}")
            timeline_bank = row.get("bank")
            if not isinstance(timeline_bank, list) or len(timeline_bank) != 2:
                raise EvidenceError(f"{mode} game {key} bank timeline malformed at {step}")
            [finite(value, f"{mode} bank {key}/{step}") for value in timeline_bank]
            if step and timeline[step - 1]["post_world_sha256"] != row["pre_world_sha256"]:
                raise EvidenceError(f"{mode} game {key} world-chain break at step {step}")
        if [float(value) for value in timeline[-1]["bank"]] != bank_values:
            raise EvidenceError(f"{mode} game {key} final timeline bank mismatch")
        result[key] = game
    if set(result) != exact_keys():
        raise EvidenceError(f"{mode} report paired grid mismatch")
    return result


def first_difference(control: list[dict[str, Any]], candidate: list[dict[str, Any]], key: tuple[str, int, int]) -> int | None:
    missing = object()
    for step, pair in enumerate(zip_longest(control, candidate, fillvalue=missing)):
        left, right = pair
        if left is missing or right is missing:
            raise EvidenceError(f"cell {key} timeline lengths differ at step {step}")
        if left["tested_action"] != right["tested_action"]:
            return step
        for field in ("pre_world_sha256", "rival_action", "post_world_sha256", "bank"):
            if left[field] != right[field]:
                raise EvidenceError(
                    f"cell {key} diverges in {field} at step {step} without a tested-action treatment"
                )
    return None


def executable_market(action: dict[str, Any], limit: int) -> list[Any]:
    market = action.get("market", [])
    if not isinstance(market, list):
        raise EvidenceError("action market is not a list")
    return market[: max(1, limit)]


def sell_signature(market: Iterable[Any]) -> list[tuple[str, int]]:
    result: list[tuple[str, int]] = []
    for row in market:
        if (
            isinstance(row, list)
            and len(row) > 2
            and row[0] == "SELL"
            and isinstance(row[1], str)
            and type(row[2]) is int
            and row[2] > 0
        ):
            result.append((row[1], row[2]))
    return result


def action_without_market(action: dict[str, Any]) -> dict[str, Any]:
    result = dict(action)
    result.pop("market", None)
    return result


def precondition(debug: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "step",
        "player",
        "max_market_orders",
        "money",
        "shed",
        "pending_before",
        "planned_before",
        "baseline_order",
        "control_order",
        "intent_order",
        "base_market",
    )
    return {field: debug.get(field) for field in fields}


def cell_result(
    key: tuple[str, int, int], control: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    seat = key[2]
    control_timeline = control["candidate_timeline"]
    candidate_timeline = candidate["candidate_timeline"]
    difference = first_difference(control_timeline, candidate_timeline, key)
    own_control = float(control["scores"][seat])
    rival_control = float(control["scores"][1 - seat])
    own_candidate = float(candidate["scores"][seat])
    rival_candidate = float(candidate["scores"][1 - seat])
    row: dict[str, Any] = {
        "opponent": key[0],
        "seed": key[1],
        "candidate_seat": seat,
        "action_changed": difference is not None,
        "trace_changed": control["trace_sha256"] != candidate["trace_sha256"],
        "first_divergence_step": difference,
        "control_own_cash": own_control,
        "candidate_own_cash": own_candidate,
        "own_cash_delta": own_candidate - own_control,
        "control_rival_cash": rival_control,
        "candidate_rival_cash": rival_candidate,
        "rival_cash_delta": rival_candidate - rival_control,
        "margin_delta": (own_candidate - rival_candidate) - (own_control - rival_control),
    }
    if difference is None:
        if row["trace_changed"] or any(
            row[field] != 0.0 for field in ("own_cash_delta", "rival_cash_delta", "margin_delta")
        ):
            raise EvidenceError(f"dormant cell {key} has trace or score drift")
        row["classification"] = "dormant"
        return row

    before_control = control_timeline[difference]
    before_candidate = candidate_timeline[difference]
    if before_control["pre_world_sha256"] != before_candidate["pre_world_sha256"]:
        raise EvidenceError(f"active cell {key} lacks common pre-world at first divergence")
    if before_control["rival_action"] != before_candidate["rival_action"]:
        raise EvidenceError(f"active cell {key} changed rival action at first divergence")
    if action_without_market(before_control["tested_action"]) != action_without_market(before_candidate["tested_action"]):
        raise EvidenceError(f"active cell {key} changes a non-market action field")
    control_debug = before_control["debug"]
    candidate_debug = before_candidate["debug"]
    if precondition(control_debug) != precondition(candidate_debug):
        raise EvidenceError(f"active cell {key} lacks identical policy precondition")
    if control_debug.get("returned_market") != before_control["tested_action"].get("market", []):
        raise EvidenceError(f"active cell {key} control debug/action market mismatch")
    if candidate_debug.get("returned_market") != before_candidate["tested_action"].get("market", []):
        raise EvidenceError(f"active cell {key} candidate debug/action market mismatch")
    if control_debug.get("control_order") == control_debug.get("intent_order"):
        raise EvidenceError(f"active cell {key} has no intent-order exposure")
    limit = true_int(control_debug.get("max_market_orders"), "max market orders", 0)
    control_market = executable_market(before_control["tested_action"], limit)
    candidate_market = executable_market(before_candidate["tested_action"], limit)
    if control_market == candidate_market:
        raise EvidenceError(f"active cell {key} differs only outside the executable market prefix")
    if before_control["post_world_sha256"] == before_candidate["post_world_sha256"]:
        raise EvidenceError(f"active cell {key} returned different executable actions but no world effect")

    control_sells = sell_signature(control_market)
    candidate_sells = sell_signature(candidate_market)
    same_multiset = sorted(control_sells) == sorted(candidate_sells)
    missing = object()
    first_row = next(
        index
        for index, values in enumerate(
            zip_longest(control_market, candidate_market, fillvalue=missing)
        )
        if values[0] != values[1]
    )
    own_immediate = float(before_candidate["bank"][seat]) - float(before_control["bank"][seat])
    rival_immediate = float(before_candidate["bank"][1 - seat]) - float(before_control["bank"][1 - seat])
    row.update({
        "classification": "executable_sell_order" if same_multiset else "plan_or_quantity_reselection",
        "pre_world_sha256": before_control["pre_world_sha256"],
        "control_post_world_sha256": before_control["post_world_sha256"],
        "candidate_post_world_sha256": before_candidate["post_world_sha256"],
        "first_changed_market_index": first_row,
        "control_executable_market": control_market,
        "candidate_executable_market": candidate_market,
        "control_sell_signature": control_sells,
        "candidate_sell_signature": candidate_sells,
        "sell_multiset_preserved": same_multiset,
        "immediate_own_cash_delta": own_immediate,
        "immediate_rival_cash_delta": rival_immediate,
        "pending_before": control_debug.get("pending_before"),
        "baseline_order": control_debug.get("baseline_order"),
        "control_order": control_debug.get("control_order"),
        "intent_order": control_debug.get("intent_order"),
        "shed": control_debug.get("shed"),
        "control_chosen": control_debug.get("chosen"),
        "candidate_chosen": candidate_debug.get("chosen"),
        "precondition_sha256": sha256_value(precondition(control_debug)),
    })
    return row


def analyze(
    control_report: dict[str, Any],
    candidate_report: dict[str, Any],
    pair_receipt: dict[str, Any],
    evaluator_receipt: dict[str, Any],
    expected_head: str | None,
    runtime: dict[str, Any],
) -> dict[str, Any]:
    binding = validate_receipts(pair_receipt, evaluator_receipt, expected_head, runtime)
    controls = index_report(control_report, "control", binding)
    candidates = index_report(candidate_report, "candidate", binding)
    rows = [cell_result(key, controls[key], candidates[key]) for key in sorted(exact_keys())]
    active = [row for row in rows if row["action_changed"]]
    dormant = [row for row in rows if not row["action_changed"]]

    expected_active = {(OPPONENT, 2609097304, 0), (OPPONENT, 2609097304, 1)}
    actual_active = {(row["opponent"], row["seed"], row["candidate_seat"]) for row in active}
    if actual_active != expected_active:
        raise EvidenceError(f"activation topology drift: expected {expected_active}, got {actual_active}")
    for row in active:
        if (
            row["own_cash_delta"] != -6.0
            or row["rival_cash_delta"] != 33.0
            or row["margin_delta"] != -39.0
        ):
            raise EvidenceError(f"reported negative-pair terminal delta did not reproduce: {row}")
    if len(dormant) != 14:
        raise EvidenceError("expected fourteen dormant mirrored cells")

    own_deltas = [row["own_cash_delta"] for row in rows]
    rival_deltas = [row["rival_cash_delta"] for row in rows]
    margin_deltas = [row["margin_delta"] for row in rows]
    common_precondition = (
        active[0]["precondition_sha256"] == active[1]["precondition_sha256"]
    )
    output = {
        "schema_version": 1,
        "experiment": "titan-v3-intent-priority-2609097304-causal-closure",
        "git_head": expected_head,
        "binding": {
            "archive_sha256": ARCHIVE_SHA256,
            "source_manifest_sha256": SOURCE_SHA256,
            "frozen_selected_git_blob_sha1": FROZEN_SELECTED_GIT_BLOB,
            "evaluator_source_git_blob_sha1": EVALUATOR_GIT_BLOB,
            **binding,
        },
        "grid": {
            "opponents": [OPPONENT],
            "seeds": list(SEEDS),
            "seats": [0, 1],
            "paired_cells": len(rows),
            "action_active_cells": len(active),
            "dormant_cells": len(dormant),
        },
        "aggregate": {
            "mean_own_cash_delta": statistics.mean(own_deltas),
            "median_own_cash_delta": statistics.median(own_deltas),
            "mean_rival_cash_delta": statistics.mean(rival_deltas),
            "mean_margin_delta": statistics.mean(margin_deltas),
            "minimum_own_cash_delta": min(own_deltas),
            "minimum_margin_delta": min(margin_deltas),
            "negative_own_cells": sum(value < 0 for value in own_deltas),
            "negative_margin_cells": sum(value < 0 for value in margin_deltas),
        },
        "causal_closure": {
            "all_pre_divergence_steps_identical": True,
            "common_pre_world_at_first_divergence": True,
            "rival_action_identical_at_first_divergence": True,
            "only_tested_market_field_changed": True,
            "executable_prefix_changed": True,
            "post_world_changed_immediately": True,
            "active_cells_share_exact_precondition": common_precondition,
            "classification_counts": {
                name: sum(row.get("classification") == name for row in active)
                for name in ("executable_sell_order", "plan_or_quantity_reselection")
            },
        },
        "cells": rows,
        "verdict": {
            "disposition": "RETIRE_FACTOR",
            "reason": (
                "The exact current entrypoint exposes the factor in only two mirrored "
                "cells, and both causally reduce own cash by 6 while increasing rival cash "
                "by 33. The other fourteen cells are action-dormant. No positive activation "
                "exists from which to justify a public-state enabling guard; a guard that "
                "blocks the two failures collapses to current control on this panel."
            ),
            "canonical_change_authorized": False,
            "guard_authorized": False,
            "v1_extension_required": False,
            "promotion_authorized": False,
            "strength_claim": False,
        },
    }
    if output["aggregate"] != {
        "mean_own_cash_delta": -0.75,
        "median_own_cash_delta": 0.0,
        "mean_rival_cash_delta": 4.125,
        "mean_margin_delta": -4.875,
        "minimum_own_cash_delta": -6.0,
        "minimum_margin_delta": -39.0,
        "negative_own_cells": 2,
        "negative_margin_cells": 2,
    }:
        raise EvidenceError(f"aggregate did not reproduce SOL-REACH result: {output['aggregate']}")
    return output


def markdown(report: dict[str, Any]) -> str:
    active = [row for row in report["cells"] if row["action_changed"]]
    lines = [
        "# TITAN V3 intent-priority causal closure",
        "",
        f"**Disposition: {report['verdict']['disposition']}**",
        "",
        report["verdict"]["reason"],
        "",
        "## Exact result",
        "",
        f"- Grid: {report['grid']['paired_cells']} paired Arlene cells; "
        f"{report['grid']['action_active_cells']} active / {report['grid']['dormant_cells']} dormant.",
        f"- Mean own delta: {report['aggregate']['mean_own_cash_delta']:+.3f}; "
        f"mean rival delta: {report['aggregate']['mean_rival_cash_delta']:+.3f}; "
        f"mean margin delta: {report['aggregate']['mean_margin_delta']:+.3f}.",
        "- Both active cells are mirrored seed `2609097304`: own `-6`, rival `+33`, margin `-39`.",
        "- Every pre-divergence step is identical; the first changed tested market action has an identical pre-world and rival action, then immediately changes the official post-world.",
        "",
        "## First divergences",
        "",
        "| Seat | Step | Class | Row | Immediate own | Immediate rival | Pending | Baseline | Control order | Intent order |",
        "|---:|---:|---|---:|---:|---:|---|---|---|---|",
    ]
    for row in active:
        lines.append(
            "| {seat} | {step} | `{kind}` | {index} | {own:+.0f} | {rival:+.0f} | `{pending}` | `{baseline}` | `{control}` | `{intent}` |".format(
                seat=row["candidate_seat"],
                step=row["first_divergence_step"],
                kind=row["classification"],
                index=row["first_changed_market_index"],
                own=row["immediate_own_cash_delta"],
                rival=row["immediate_rival_cash_delta"],
                pending=json.dumps(row["pending_before"], separators=(",", ":")),
                baseline=json.dumps(row["baseline_order"], separators=(",", ":")),
                control=json.dumps(row["control_order"], separators=(",", ":")),
                intent=json.dumps(row["intent_order"], separators=(",", ":")),
            )
        )
    lines.extend([
        "",
        "## Integration boundary",
        "",
        "Do not port or promote this factor on current V3. The scheduler-only version is unreachable behind `consumer=frozen`; the actual `FrozenSelected.transform` version is reachable only in the two measured cells and is harmful in both. Keep the canonical PRODUCTS traversal.",
        "",
    ])
    return "\n".join(lines)


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--pair-receipt", type=Path, required=True)
    parser.add_argument("--evaluator-receipt", type=Path, required=True)
    parser.add_argument("--opponent-source", type=Path, required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--expected-head")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    report = analyze(
        strict_load(args.control, "control report"),
        strict_load(args.candidate, "candidate report"),
        strict_load(args.pair_receipt, "pair receipt"),
        strict_load(args.evaluator_receipt, "evaluator receipt"),
        args.expected_head,
        runtime_binding(args.opponent_source, args.loader, args.engine_dir),
    )
    atomic_write(
        args.output.resolve(),
        (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(),
    )
    atomic_write(args.markdown.resolve(), markdown(report).encode("utf-8"))
    print(json.dumps(report["verdict"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
