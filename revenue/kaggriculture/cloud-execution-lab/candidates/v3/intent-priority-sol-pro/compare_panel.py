# SPDX-License-Identifier: Apache-2.0
"""Classify a closure-bound current-main intent-priority matched panel."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Iterable, Mapping

import bind
import materialize


EXPERIMENT = "titan-v3-current-intent-priority-integration-20260910-01"
EXPECTED_OPPONENTS = ("arlene", "v1")
EXPECTED_SEEDS = (
    539131249,
    1834999074,
    2609097301,
    2609097302,
    2609097303,
    2609097304,
    2611092201,
    2611092207,
)
KNOWN_ACTIVATING_SEEDS = {1834999074, 2609097301}
EXPECTED_EPISODE_STEPS = 720
EXPECTED_ACTIONS = EXPECTED_EPISODE_STEPS - 1
EXPECTED_EVALUATOR_SOURCE_BLOB = "077feb2208b6e0c1727835eb4f8089709bf67f3b"
EXPECTED_EVALUATOR_SOURCE_SHA256 = (
    "e9a093ab6bccaa58289ba84ee62d4abec0aa85eae2a8dfc828964c4b6773c797"
)
EXPECTED_EVALUATOR_PATCH_SHA256 = (
    "8ab156a7fb815161c9bdfb11e9e33203f16cc526b0877391563e4d032936beeb"
)


class CompareError(ValueError):
    """The paired evidence is incomplete, detached, or internally inconsistent."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _reject_constant(value: str) -> None:
    raise CompareError(f"non-finite JSON constant: {value}")


def strict_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"),
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CompareError(f"cannot read strict JSON {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise CompareError(f"JSON root is not an object: {path}")
    return value


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + ".tmp")
    if temporary.exists():
        temporary.unlink()
    with temporary.open("xb") as stream:
        stream.write(data)
        stream.flush()
    temporary.replace(path)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CompareError(f"{label} is not an object")
    return value


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CompareError(f"{label} is not numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise CompareError(f"{label} is not finite")
    return parsed


def _hex(value: Any, label: str, length: int = 64) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise CompareError(f"{label} is not lowercase {length}-hex")
    return value


def _regular_bytes(path: Path, label: str) -> bytes:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise CompareError(f"{label} is not one regular file: {path}")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise CompareError(f"cannot read {label}: {exc}") from exc


def expected_grid(
    opponents: Iterable[str] = EXPECTED_OPPONENTS,
    seeds: Iterable[int] = EXPECTED_SEEDS,
) -> set[tuple[str, int, int]]:
    return {
        (opponent, int(seed), seat)
        for opponent in opponents
        for seed in seeds
        for seat in (0, 1)
    }


def validate_materialization(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    head: str,
    control_root: Path,
    candidate_root: Path,
) -> dict[str, Any]:
    for label, receipt in (("control", control), ("candidate", candidate)):
        if receipt.get("schema_version") != 1:
            raise CompareError(f"{label} materialization schema mismatch")
        if receipt.get("experiment") != EXPERIMENT:
            raise CompareError(f"{label} materialization experiment mismatch")
        if receipt.get("integration_head") != head:
            raise CompareError(f"{label} materialization head mismatch")
        if receipt.get("canonical_base_head") != materialize.CANONICAL_BASE_HEAD:
            raise CompareError(f"{label} canonical base mismatch")

    source = _mapping(control.get("source"), "control source")
    candidate_source = _mapping(candidate.get("source"), "candidate source")
    if dict(source) != dict(candidate_source):
        raise CompareError("control/candidate canonical source receipts differ")
    if source.get("archive_sha256") != materialize.EXPECTED_ARCHIVE_SHA256:
        raise CompareError("canonical archive SHA-256 mismatch")
    if source.get("archive_bytes") != materialize.EXPECTED_ARCHIVE_BYTES:
        raise CompareError("canonical archive size mismatch")
    if (
        source.get("source_manifest_sha256")
        != materialize.EXPECTED_SOURCE_MANIFEST_SHA256
    ):
        raise CompareError("canonical SOURCE.json mismatch")
    if (
        source.get("scheduler_git_blob_sha1")
        != materialize.EXPECTED_SCHEDULER_BLOB
    ):
        raise CompareError("canonical scheduler blob mismatch")

    control_feature = _mapping(control.get("feature"), "control feature")
    candidate_feature = _mapping(candidate.get("feature"), "candidate feature")
    if control_feature.get("enabled") is not False:
        raise CompareError("control is not default-off")
    if candidate_feature.get("enabled") is not True:
        raise CompareError("candidate is not enabled")
    if control_feature.get("default") is not False:
        raise CompareError("control default is not false")
    if candidate_feature.get("default") is not False:
        raise CompareError("candidate default is not false")
    for field in (
        "name",
        "target_domain",
        "target_quantity",
        "control_priority",
        "enabled_priority",
        "selection_effect",
    ):
        if control_feature.get(field) != candidate_feature.get(field):
            raise CompareError(f"factor receipt differs at {field}")

    control_result = _mapping(control.get("candidate"), "control result")
    candidate_result = _mapping(candidate.get("candidate"), "candidate result")
    if control_result.get("changed_files") != []:
        raise CompareError("default-off materialization changed canonical files")
    if candidate_result.get("changed_files") != ["scheduler.py"]:
        raise CompareError("enabled materialization is not scheduler-only")
    if control_result.get("closure_sha256") != source.get("closure_sha256"):
        raise CompareError("default-off closure is not canonical-exact")
    if (
        control_result.get("scheduler_git_blob_sha1")
        != source.get("scheduler_git_blob_sha1")
    ):
        raise CompareError("default-off scheduler is not canonical-exact")
    if candidate_result.get("scheduler_git_blob_sha1") == source.get(
        "scheduler_git_blob_sha1"
    ):
        raise CompareError("enabled scheduler equals control")
    if (
        control_result.get("old_occurrences_after") != 1
        or control_result.get("new_occurrences_after") != 0
    ):
        raise CompareError("default-off expression cardinality is invalid")
    if (
        candidate_result.get("old_occurrences_before") != 1
        or candidate_result.get("old_occurrences_after") != 0
        or candidate_result.get("new_occurrences_before") != 0
        or candidate_result.get("new_occurrences_after") != 1
    ):
        raise CompareError("enabled expression cardinality is invalid")

    control_inventory = bind.inventory(control_root)
    candidate_inventory = bind.inventory(candidate_root)
    control_closure = bind.closure_sha256(control_inventory)
    candidate_closure = bind.closure_sha256(candidate_inventory)
    if control_closure != control_result.get("closure_sha256"):
        raise CompareError("control tree is detached from materialization receipt")
    if candidate_closure != candidate_result.get("closure_sha256"):
        raise CompareError("candidate tree is detached from materialization receipt")
    changed = [
        name
        for name in sorted(control_inventory)
        if control_inventory.get(name) != candidate_inventory.get(name)
    ]
    if set(control_inventory) != set(candidate_inventory):
        raise CompareError("control/candidate file inventories differ")
    if changed != ["scheduler.py"]:
        raise CompareError(f"on-disk candidate delta is not scheduler-only: {changed}")

    return {
        "source_archive_sha256": source["archive_sha256"],
        "source_closure_sha256": source["closure_sha256"],
        "control_closure_sha256": control_closure,
        "candidate_closure_sha256": candidate_closure,
        "control_scheduler_git_blob_sha1": control_result[
            "scheduler_git_blob_sha1"
        ],
        "candidate_scheduler_git_blob_sha1": candidate_result[
            "scheduler_git_blob_sha1"
        ],
        "changed_files": changed,
    }


def validate_binding(
    binding_receipt: Mapping[str, Any],
    *,
    head: str,
    control_root: Path,
    candidate_root: Path,
    control_wrapper: Path,
    candidate_wrapper: Path,
    control_closure: str,
    candidate_closure: str,
) -> dict[str, Any]:
    if binding_receipt.get("schema_version") != 1:
        raise CompareError("binding schema mismatch")
    if binding_receipt.get("experiment") != EXPERIMENT:
        raise CompareError("binding experiment mismatch")
    if binding_receipt.get("integration_head") != head:
        raise CompareError("binding head mismatch")
    results: dict[str, Any] = {}
    for label, root, wrapper, closure in (
        ("control", control_root, control_wrapper, control_closure),
        ("candidate", candidate_root, candidate_wrapper, candidate_closure),
    ):
        row = _mapping(binding_receipt.get(label), f"{label} binding")
        wrapper_bytes = _regular_bytes(wrapper, f"{label} wrapper")
        if Path(str(row.get("root"))).resolve() != Path(root).resolve():
            raise CompareError(f"{label} binding root mismatch")
        if Path(str(row.get("entry"))).resolve() != Path(wrapper).resolve():
            raise CompareError(f"{label} binding entry mismatch")
        if row.get("callable") != "agent":
            raise CompareError(f"{label} binding callable mismatch")
        if row.get("closure_sha256") != closure:
            raise CompareError(f"{label} binding closure mismatch")
        if row.get("entry_sha256") != sha256(wrapper_bytes):
            raise CompareError(f"{label} wrapper SHA-256 mismatch")
        results[label] = {
            "closure_sha256": closure,
            "entry_sha256": sha256(wrapper_bytes),
        }
    return results


def validate_evaluator(
    receipt: Mapping[str, Any],
    *,
    source_path: Path,
    patched_path: Path,
) -> dict[str, str]:
    if receipt.get("schema_version") != 1:
        raise CompareError("evaluator receipt schema mismatch")
    if receipt.get("repair") != "sol-candidate-action-evidence-v1":
        raise CompareError("evaluator repair identifier mismatch")
    source = _mapping(receipt.get("source"), "evaluator source")
    patched = _mapping(receipt.get("patched"), "patched evaluator")
    source_bytes = _regular_bytes(source_path, "source evaluator")
    patched_bytes = _regular_bytes(patched_path, "patched evaluator")
    if git_blob_sha1(source_bytes) != EXPECTED_EVALUATOR_SOURCE_BLOB:
        raise CompareError("source evaluator Git blob drifted")
    if sha256(source_bytes) != EXPECTED_EVALUATOR_SOURCE_SHA256:
        raise CompareError("source evaluator SHA-256 drifted")
    if source.get("git_blob_sha1") != EXPECTED_EVALUATOR_SOURCE_BLOB:
        raise CompareError("evaluator source receipt blob mismatch")
    if source.get("sha256") != EXPECTED_EVALUATOR_SOURCE_SHA256:
        raise CompareError("evaluator source receipt SHA-256 mismatch")
    if source.get("bytes") != len(source_bytes):
        raise CompareError("evaluator source receipt size mismatch")
    if sha256(patched_bytes) != EXPECTED_EVALUATOR_PATCH_SHA256:
        raise CompareError("patched evaluator SHA-256 drifted")
    if patched.get("sha256") != EXPECTED_EVALUATOR_PATCH_SHA256:
        raise CompareError("patched evaluator receipt SHA-256 mismatch")
    if patched.get("git_blob_sha1") != git_blob_sha1(patched_bytes):
        raise CompareError("patched evaluator receipt blob mismatch")
    if patched.get("bytes") != len(patched_bytes):
        raise CompareError("patched evaluator receipt size mismatch")
    if patched.get("candidate_action_field") != "candidate_action_sha256":
        raise CompareError("patched evaluator action field mismatch")
    if patched.get("candidate_action_count_field") != "candidate_action_count":
        raise CompareError("patched evaluator action count field mismatch")
    if patched.get("capture_phase") != (
        "after both returned actions, before interpreter"
    ):
        raise CompareError("patched evaluator capture phase mismatch")
    patches = patched.get("patches")
    if not isinstance(patches, list) or len(patches) != 3:
        raise CompareError("patched evaluator cardinality receipt is incomplete")
    for index, patch in enumerate(patches):
        row = _mapping(patch, f"evaluator patch {index}")
        if (
            row.get("old_occurrences_before") != 1
            or row.get("old_occurrences_after") != 0
            or row.get("new_occurrences_after") != 1
        ):
            raise CompareError(f"evaluator patch {index} cardinality is invalid")
    return {
        "source_git_blob_sha1": EXPECTED_EVALUATOR_SOURCE_BLOB,
        "source_sha256": EXPECTED_EVALUATOR_SOURCE_SHA256,
        "patched_git_blob_sha1": git_blob_sha1(patched_bytes),
        "patched_sha256": EXPECTED_EVALUATOR_PATCH_SHA256,
    }


def _daily_divergence(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    label: str,
) -> int | None:
    left = control.get("daily_bank")
    right = candidate.get("daily_bank")
    if not isinstance(left, list) or not isinstance(right, list):
        raise CompareError(f"{label} daily bank is missing")
    if len(left) != len(right):
        raise CompareError(f"{label} daily bank lengths differ")
    first: int | None = None
    for index, (a, b) in enumerate(zip(left, right)):
        a = _mapping(a, f"{label} control daily bank {index}")
        b = _mapping(b, f"{label} candidate daily bank {index}")
        if type(a.get("step")) is not int or a.get("step") != b.get("step"):
            raise CompareError(f"{label} daily bank step mismatch")
        a_bank = a.get("bank")
        b_bank = b.get("bank")
        if (
            not isinstance(a_bank, list)
            or not isinstance(b_bank, list)
            or len(a_bank) != 2
            or len(b_bank) != 2
        ):
            raise CompareError(f"{label} daily bank vector is invalid")
        for seat in (0, 1):
            _number(a_bank[seat], f"{label} control daily bank")
            _number(b_bank[seat], f"{label} candidate daily bank")
        if first is None and a_bank != b_bank:
            first = int(a["step"])
    return first


def _validate_report(
    report: Mapping[str, Any],
    *,
    label: str,
    entry_sha256: str,
    evaluator_sha256: str,
) -> tuple[dict[tuple[str, int, int], Mapping[str, Any]], dict[str, Any]]:
    if report.get("schema_version") != 1:
        raise CompareError(f"{label} evaluator schema mismatch")
    candidate = _mapping(report.get("candidate"), f"{label} candidate provenance")
    if candidate.get("callable") != "agent":
        raise CompareError(f"{label} candidate callable mismatch")
    if candidate.get("sha256") != entry_sha256:
        raise CompareError(f"{label} candidate entry hash mismatch")
    if report.get("evaluator_sha256") != evaluator_sha256:
        raise CompareError(f"{label} evaluator hash mismatch")
    if report.get("seeds") != list(EXPECTED_SEEDS):
        raise CompareError(f"{label} seed vector mismatch")
    opponents = _mapping(report.get("opponents"), f"{label} opponents")
    if set(opponents) != set(EXPECTED_OPPONENTS):
        raise CompareError(f"{label} opponent set mismatch")
    for opponent in EXPECTED_OPPONENTS:
        row = _mapping(opponents[opponent], f"{label} opponent {opponent}")
        if row.get("callable") != "agent":
            raise CompareError(f"{label} opponent callable mismatch: {opponent}")
        _hex(row.get("sha256"), f"{label} opponent hash {opponent}")
    progress = _mapping(report.get("progress"), f"{label} progress")
    expected = len(expected_grid())
    if (
        progress.get("state") != "complete"
        or progress.get("planned_games") != expected
        or progress.get("recorded_games") != expected
    ):
        raise CompareError(f"{label} evaluator did not complete exact grid")
    games = report.get("games")
    if not isinstance(games, list) or len(games) != expected:
        raise CompareError(f"{label} game cardinality mismatch")

    normalized: dict[tuple[str, int, int], Mapping[str, Any]] = {}
    for index, raw in enumerate(games):
        game = _mapping(raw, f"{label} game {index}")
        opponent = game.get("opponent")
        seed = game.get("seed")
        seat = game.get("candidate_seat")
        if (
            type(opponent) is not str
            or type(seed) is not int
            or type(seat) is not int
            or seat not in (0, 1)
        ):
            raise CompareError(f"{label} game {index} key is invalid")
        key = (opponent, seed, seat)
        if key in normalized:
            raise CompareError(f"{label} duplicate game key: {key!r}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise CompareError(f"{label} game did not complete: {key!r}")
        if (
            game.get("episode_steps") != EXPECTED_EPISODE_STEPS
            or game.get("steps") != EXPECTED_ACTIONS
            or game.get("candidate_action_count") != EXPECTED_ACTIONS
        ):
            raise CompareError(f"{label} game action count mismatch: {key!r}")
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2:
            raise CompareError(f"{label} game scores are invalid: {key!r}")
        _number(scores[0], f"{label} game score 0")
        _number(scores[1], f"{label} game score 1")
        _hex(game.get("candidate_action_sha256"), f"{label} action hash")
        _hex(game.get("trace_sha256"), f"{label} trace hash")
        normalized[key] = game
    if set(normalized) != expected_grid():
        missing = sorted(expected_grid() - set(normalized))
        extra = sorted(set(normalized) - expected_grid())
        raise CompareError(
            f"{label} evaluator grid mismatch; missing={missing}, extra={extra}"
        )
    metadata = {
        "engine_ref": report.get("engine_ref"),
        "engine_sha256": report.get("engine_sha256"),
        "loader_sha256": report.get("loader_sha256"),
        "evaluator_sha256": report.get("evaluator_sha256"),
        "agent_rng_seed": report.get("agent_rng_seed"),
        "limits": report.get("limits"),
        "method": report.get("method"),
        "python": report.get("python"),
        "platform": report.get("platform"),
        "opponents": report.get("opponents"),
        "seeds": report.get("seeds"),
    }
    return normalized, metadata


def _outcome(own: float, rival: float) -> str:
    if own > rival:
        return "win"
    if own < rival:
        return "loss"
    return "tie"


def compare_reports(
    control_report: Mapping[str, Any],
    candidate_report: Mapping[str, Any],
    *,
    control_entry_sha256: str,
    candidate_entry_sha256: str,
    evaluator_sha256: str,
) -> dict[str, Any]:
    control, control_meta = _validate_report(
        control_report,
        label="control",
        entry_sha256=control_entry_sha256,
        evaluator_sha256=evaluator_sha256,
    )
    candidate, candidate_meta = _validate_report(
        candidate_report,
        label="candidate",
        entry_sha256=candidate_entry_sha256,
        evaluator_sha256=evaluator_sha256,
    )
    for field in (
        "engine_ref",
        "engine_sha256",
        "loader_sha256",
        "evaluator_sha256",
        "agent_rng_seed",
        "limits",
        "opponents",
        "seeds",
    ):
        if control_meta[field] != candidate_meta[field]:
            raise CompareError(f"control/candidate execution differs at {field}")

    rows: list[dict[str, Any]] = []
    transitions: Counter[str] = Counter()
    for key in sorted(expected_grid()):
        opponent, seed, seat = key
        before = control[key]
        after = candidate[key]
        control_scores = before["scores"]
        candidate_scores = after["scores"]
        rival_seat = 1 - seat
        control_own = _number(control_scores[seat], "control own score")
        control_rival = _number(control_scores[rival_seat], "control rival score")
        candidate_own = _number(candidate_scores[seat], "candidate own score")
        candidate_rival = _number(
            candidate_scores[rival_seat], "candidate rival score"
        )
        action_changed = (
            before["candidate_action_sha256"]
            != after["candidate_action_sha256"]
        )
        whole_changed = before["trace_sha256"] != after["trace_sha256"]
        if action_changed != whole_changed:
            raise CompareError(
                f"candidate-action and whole-trace activation disagree: {key!r}"
            )
        first_divergence = _daily_divergence(
            before, after, label=f"{opponent}/{seed}/seat-{seat}"
        )
        own_delta = candidate_own - control_own
        rival_delta = candidate_rival - control_rival
        margin_delta = (
            candidate_own - candidate_rival - (control_own - control_rival)
        )
        control_outcome = _outcome(control_own, control_rival)
        candidate_outcome = _outcome(candidate_own, candidate_rival)
        transitions[f"{control_outcome}->{candidate_outcome}"] += 1
        rows.append(
            {
                "opponent": opponent,
                "seed": seed,
                "seat": seat,
                "control_own": control_own,
                "control_rival": control_rival,
                "candidate_own": candidate_own,
                "candidate_rival": candidate_rival,
                "own_delta": own_delta,
                "rival_delta": rival_delta,
                "margin_delta": margin_delta,
                "control_outcome": control_outcome,
                "candidate_outcome": candidate_outcome,
                "candidate_action_changed": action_changed,
                "whole_trace_changed": whole_changed,
                "first_daily_bank_divergence_step": first_divergence,
            }
        )

    own_deltas = [row["own_delta"] for row in rows]
    rival_deltas = [row["rival_delta"] for row in rows]
    margin_deltas = [row["margin_delta"] for row in rows]
    changed_rows = [row for row in rows if row["candidate_action_changed"]]
    new_losses = [
        row
        for row in rows
        if row["control_outcome"] != "loss"
        and row["candidate_outcome"] == "loss"
    ]
    lost_wins = [
        row
        for row in rows
        if row["control_outcome"] == "win"
        and row["candidate_outcome"] != "win"
    ]
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["opponent"], row["seat"])].append(row)
    strata: dict[str, dict[str, Any]] = {}
    for (opponent, seat), group in sorted(grouped.items()):
        own = [row["own_delta"] for row in group]
        margin = [row["margin_delta"] for row in group]
        strata[f"{opponent}:seat-{seat}"] = {
            "opponent": opponent,
            "seat": seat,
            "cells": len(group),
            "candidate_action_changed_cells": sum(
                row["candidate_action_changed"] for row in group
            ),
            "positive_cells": sum(value > 0 for value in own),
            "zero_cells": sum(value == 0 for value in own),
            "negative_cells": sum(value < 0 for value in own),
            "mean_own_delta": statistics.mean(own),
            "median_own_delta": statistics.median(own),
            "minimum_own_delta": min(own),
            "maximum_own_delta": max(own),
            "mean_margin_delta": statistics.mean(margin),
            "new_losses": sum(row in new_losses for row in group),
            "lost_wins": sum(row in lost_wins for row in group),
        }

    overall = {
        "cells": len(rows),
        "candidate_action_changed_cells": len(changed_rows),
        "known_seed_action_changed_cells": sum(
            row["candidate_action_changed"]
            and row["seed"] in KNOWN_ACTIVATING_SEEDS
            for row in rows
        ),
        "positive_cells": sum(value > 0 for value in own_deltas),
        "zero_cells": sum(value == 0 for value in own_deltas),
        "negative_cells": sum(value < 0 for value in own_deltas),
        "mean_own_delta": statistics.mean(own_deltas),
        "median_own_delta": statistics.median(own_deltas),
        "minimum_own_delta": min(own_deltas),
        "maximum_own_delta": max(own_deltas),
        "mean_rival_delta": statistics.mean(rival_deltas),
        "mean_margin_delta": statistics.mean(margin_deltas),
        "new_losses": len(new_losses),
        "lost_wins": len(lost_wins),
    }
    gates = {
        "complete_exact_grid": overall["cells"] == len(expected_grid()),
        "candidate_action_activation": (
            overall["candidate_action_changed_cells"] > 0
        ),
        "known_seed_activation_survives_rebase": (
            overall["known_seed_action_changed_cells"] > 0
        ),
        "positive_mean_own_cash": overall["mean_own_delta"] > 0,
        "nonnegative_median_own_cash": overall["median_own_delta"] >= 0,
        "no_negative_own_cash_cells": overall["negative_cells"] == 0,
        "positive_mean_margin": overall["mean_margin_delta"] > 0,
        "zero_new_losses": overall["new_losses"] == 0,
        "zero_lost_wins": overall["lost_wins"] == 0,
        "all_opponent_seat_strata_nonnegative": all(
            row["mean_own_delta"] >= 0
            and row["median_own_delta"] >= 0
            and row["minimum_own_delta"] >= 0
            and row["mean_margin_delta"] >= 0
            and row["new_losses"] == 0
            and row["lost_wins"] == 0
            for row in strata.values()
        ),
    }
    failed = [name for name, passed in gates.items() if not passed]
    verdict = "ADMIT" if not failed else "REJECT"
    return {
        "schema_version": 1,
        "operation": EXPERIMENT,
        "experiment": EXPERIMENT,
        "verdict": verdict,
        "reason": (
            "all current-main win-oriented admission gates passed"
            if not failed
            else "failed gates: " + ", ".join(failed)
        ),
        "exit_code": 0 if verdict == "ADMIT" else 1,
        "gates": gates,
        "overall": overall,
        "by_opponent_seat": strata,
        "outcome_transitions": dict(sorted(transitions.items())),
        "changed_rows": changed_rows,
        "new_loss_rows": new_losses,
        "lost_win_rows": lost_wins,
        "rows": rows,
        "execution": control_meta,
    }


def assess(
    *,
    control_report: Mapping[str, Any],
    candidate_report: Mapping[str, Any],
    control_receipt: Mapping[str, Any],
    candidate_receipt: Mapping[str, Any],
    binding_receipt: Mapping[str, Any],
    evaluator_receipt: Mapping[str, Any],
    head: str,
    control_root: Path,
    candidate_root: Path,
    control_wrapper: Path,
    candidate_wrapper: Path,
    evaluator_source: Path,
    evaluator_patched: Path,
) -> dict[str, Any]:
    closure = validate_materialization(
        control_receipt,
        candidate_receipt,
        head=head,
        control_root=control_root,
        candidate_root=candidate_root,
    )
    binding_result = validate_binding(
        binding_receipt,
        head=head,
        control_root=control_root,
        candidate_root=candidate_root,
        control_wrapper=control_wrapper,
        candidate_wrapper=candidate_wrapper,
        control_closure=closure["control_closure_sha256"],
        candidate_closure=closure["candidate_closure_sha256"],
    )
    evaluator = validate_evaluator(
        evaluator_receipt,
        source_path=evaluator_source,
        patched_path=evaluator_patched,
    )
    result = compare_reports(
        control_report,
        candidate_report,
        control_entry_sha256=binding_result["control"]["entry_sha256"],
        candidate_entry_sha256=binding_result["candidate"]["entry_sha256"],
        evaluator_sha256=evaluator["patched_sha256"],
    )
    result["integration_head"] = head
    result["closure_binding"] = closure
    result["entry_binding"] = binding_result
    result["evaluator_binding"] = evaluator
    return result


def markdown(result: Mapping[str, Any]) -> str:
    lines = [
        "# TITAN V3 current-main intent-priority admission",
        "",
        f"**Verdict:** `{result.get('verdict')}` — {result.get('reason')}",
        "",
    ]
    overall = result.get("overall")
    if isinstance(overall, Mapping):
        lines.extend(
            [
                f"- Exact paired cells: {overall['cells']}",
                (
                    "- Candidate-action-changed cells: "
                    f"{overall['candidate_action_changed_cells']}"
                ),
                (
                    "- Known-seed changed cells: "
                    f"{overall['known_seed_action_changed_cells']}"
                ),
                (
                    "- Mean / median own-cash delta: "
                    f"{overall['mean_own_delta']:+.3f} / "
                    f"{overall['median_own_delta']:+.3f}"
                ),
                (
                    "- Mean rival / margin delta: "
                    f"{overall['mean_rival_delta']:+.3f} / "
                    f"{overall['mean_margin_delta']:+.3f}"
                ),
                (
                    "- Positive / zero / negative own cells: "
                    f"{overall['positive_cells']} / {overall['zero_cells']} / "
                    f"{overall['negative_cells']}"
                ),
                (
                    "- New losses / lost wins: "
                    f"{overall['new_losses']} / {overall['lost_wins']}"
                ),
                "",
                "## Gates",
                "",
            ]
        )
        for name, passed in result["gates"].items():
            lines.append(f"- {'PASS' if passed else 'FAIL'} — `{name}`")
        lines.extend(
            [
                "",
                "## Opponent × seat",
                "",
                (
                    "| Stratum | Cells | Changed | + / 0 / - | Mean own Δ | "
                    "Median own Δ | Mean margin Δ | New losses | Lost wins |"
                ),
                (
                    "|---|---:|---:|---:|---:|---:|---:|---:|---:|"
                ),
            ]
        )
        for name, row in result["by_opponent_seat"].items():
            lines.append(
                f"| {name} | {row['cells']} | "
                f"{row['candidate_action_changed_cells']} | "
                f"{row['positive_cells']} / {row['zero_cells']} / "
                f"{row['negative_cells']} | {row['mean_own_delta']:+.3f} | "
                f"{row['median_own_delta']:+.3f} | "
                f"{row['mean_margin_delta']:+.3f} | {row['new_losses']} | "
                f"{row['lost_wins']} |"
            )
        lines.extend(["", "## Changed cells", ""])
        for row in result.get("changed_rows", []):
            lines.append(
                "- "
                f"`{row['opponent']}/{row['seed']}/seat-{row['seat']}`: "
                f"own {row['own_delta']:+.0f}, rival {row['rival_delta']:+.0f}, "
                f"margin {row['margin_delta']:+.0f}, first bank divergence "
                f"{row['first_daily_bank_divergence_step']}"
            )
    lines.extend(
        [
            "",
            (
                "This is an exact offline causal panel against current canonical "
                "bytes. It is not hosted Kaggle scoring, a leaderboard estimate, "
                "release authority, or submission authorization."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--control-receipt", type=Path, required=True)
    parser.add_argument("--candidate-receipt", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--evaluator-receipt", type=Path, required=True)
    parser.add_argument("--control-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--control-wrapper", type=Path, required=True)
    parser.add_argument("--candidate-wrapper", type=Path, required=True)
    parser.add_argument("--evaluator-source", type=Path, required=True)
    parser.add_argument("--evaluator-patched", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    try:
        result = assess(
            control_report=strict_json(args.control),
            candidate_report=strict_json(args.candidate),
            control_receipt=strict_json(args.control_receipt),
            candidate_receipt=strict_json(args.candidate_receipt),
            binding_receipt=strict_json(args.binding),
            evaluator_receipt=strict_json(args.evaluator_receipt),
            head=args.head,
            control_root=args.control_root,
            candidate_root=args.candidate_root,
            control_wrapper=args.control_wrapper,
            candidate_wrapper=args.candidate_wrapper,
            evaluator_source=args.evaluator_source,
            evaluator_patched=args.evaluator_patched,
        )
    except (
        CompareError,
        bind.BindError,
        materialize.MaterializeError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        result = {
            "schema_version": 1,
            "operation": EXPERIMENT,
            "experiment": EXPERIMENT,
            "integration_head": args.head,
            "verdict": "INVALID",
            "reason": str(exc),
            "exit_code": 2,
        }

    atomic_write(
        args.output,
        (
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False)
            + "\n"
        ).encode("utf-8"),
    )
    atomic_write(args.markdown, markdown(result).encode("utf-8"))
    print(
        json.dumps(
            {
                "experiment": EXPERIMENT,
                "verdict": result["verdict"],
                "reason": result["reason"],
                "exit_code": result["exit_code"],
                "overall": result.get("overall"),
            },
            sort_keys=True,
        )
    )
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
