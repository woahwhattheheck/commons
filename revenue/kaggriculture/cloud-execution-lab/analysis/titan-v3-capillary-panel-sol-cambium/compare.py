# SPDX-License-Identifier: Apache-2.0
"""Classify the exact control-vs-Capillary full-game panel."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import tempfile
from typing import Any, Mapping

EXPECTED_SEEDS = (539131249, 1834999074, 2609097301, 2609097302)
EXPECTED_OPPONENTS = ("arlene", "v1")
EXPECTED_AGENT_RNG_SEED = 20260909
EXPECTED_ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
EXPECTED_GAMES_PER_ARM = len(EXPECTED_SEEDS) * len(EXPECTED_OPPONENTS) * 2
EXPECTED_STEPS = 719
EXPECTED_EPISODE_STEPS = 720
OPERATION = "titan-v3-capillary-action-bound-panel-20260910-sol-cambium-01"


class CompareError(ValueError):
    """The panel is incomplete, incomparable, or source-unbound."""


def strict_json(path: Path) -> dict[str, Any]:
    def pairs(rows):
        out = {}
        for key, value in rows:
            if key in out:
                raise CompareError(f"duplicate JSON key {key!r} in {path}")
            out[key] = value
        return out

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                CompareError(f"non-finite JSON token {token!r} in {path}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CompareError(f"cannot read {path}: {type(exc).__name__}: {exc}") from exc
    if not isinstance(value, dict):
        raise CompareError(f"{path} must contain one JSON object")
    return value


def finite(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise CompareError(f"{label} is not finite numeric")
    return float(value)


def digest(value: Any, label: str, length: int = 64) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise CompareError(f"{label} is not lowercase {length}-hex")
    return value


def exact_int(value: Any, expected: int, label: str) -> None:
    if type(value) is not int or value != expected:
        raise CompareError(f"{label}: expected {expected}, got {value!r}")


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def mean(values: list[float]) -> float:
    if not values:
        raise CompareError("cannot summarize an empty value set")
    return float(statistics.mean(values))


def validate_evaluator(receipt: Mapping[str, Any], audit: Mapping[str, Any]) -> str:
    if receipt.get("schema_version") != 1 or receipt.get("operation") != OPERATION:
        raise CompareError("evaluator receipt identity drift")
    source = receipt.get("source")
    patched = receipt.get("patched")
    expected = audit.get("evaluator_source")
    if not all(isinstance(row, Mapping) for row in (source, patched, expected)):
        raise CompareError("evaluator receipt or audit is incomplete")
    if any(
        source.get(key) != expected.get(key)
        for key in ("git_blob_sha1", "sha256", "bytes")
    ):
        raise CompareError("patched evaluator is not bound to audited source")
    patches = patched.get("patches")
    if not isinstance(patches, list) or len(patches) != 3:
        raise CompareError("candidate-action patch cardinality drift")
    for index, row in enumerate(patches):
        if (
            not isinstance(row, Mapping)
            or row.get("old_occurrences_before") != 1
            or row.get("old_occurrences_after") != 0
            or row.get("new_occurrences_after") != 1
        ):
            raise CompareError(f"candidate-action patch {index} cardinality drift")
    if (
        patched.get("capture_phase")
        != "after both returned actions, before interpreter"
        or patched.get("candidate_action_field") != "candidate_action_sha256"
        or patched.get("candidate_action_count_field") != "candidate_action_count"
    ):
        raise CompareError("candidate-action capture semantics drift")
    return digest(patched.get("sha256"), "patched evaluator sha256")


def expected_opponents(audit: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    rows = audit.get("opponents")
    if not isinstance(rows, Mapping) or set(rows) != set(EXPECTED_OPPONENTS):
        raise CompareError("source audit opponent bank drift")
    out = {}
    for name in EXPECTED_OPPONENTS:
        row = rows[name]
        if not isinstance(row, Mapping):
            raise CompareError(f"source audit opponent {name} invalid")
        out[name] = {
            "entry": "arlene.py" if name == "arlene" else "candidate.py",
            "callable": "agent",
            "sha256": digest(row.get("sha256"), f"opponent {name} sha256"),
        }
    return out


def validate_report(
    report: Mapping[str, Any],
    *,
    label: str,
    entry_sha256: str,
    evaluator_sha256: str,
    audit: Mapping[str, Any],
) -> dict[tuple[str, int, int], Mapping[str, Any]]:
    if report.get("schema_version") != 1:
        raise CompareError(f"{label} report schema drift")
    if report.get("engine_ref") != EXPECTED_ENGINE_REF:
        raise CompareError(f"{label} engine ref drift")
    if report.get("seeds") != list(EXPECTED_SEEDS):
        raise CompareError(f"{label} seed bank drift")
    exact_int(report.get("agent_rng_seed"), EXPECTED_AGENT_RNG_SEED, f"{label} RNG seed")
    if report.get("evaluator_sha256") != evaluator_sha256:
        raise CompareError(f"{label} evaluator identity drift")

    loader = audit.get("loader")
    if not isinstance(loader, Mapping) or report.get("loader_sha256") != loader.get("sha256"):
        raise CompareError(f"{label} loader identity drift")
    engine = audit.get("engine")
    actual_engine = report.get("engine_sha256")
    if not isinstance(engine, Mapping) or not isinstance(actual_engine, Mapping):
        raise CompareError(f"{label} engine receipt missing")
    expected_engine = {
        name: row.get("sha256") if isinstance(row, Mapping) else None
        for name, row in engine.items()
    }
    if actual_engine != expected_engine:
        raise CompareError(f"{label} engine source identity drift")

    entry = report.get("candidate")
    if (
        not isinstance(entry, Mapping)
        or entry.get("callable") != "agent"
        or entry.get("sha256") != entry_sha256
    ):
        raise CompareError(f"{label} candidate entry identity drift")
    if report.get("opponents") != expected_opponents(audit):
        raise CompareError(f"{label} opponent fingerprints drift")

    limits = report.get("limits")
    if not isinstance(limits, Mapping):
        raise CompareError(f"{label} timeout contract missing")
    if (
        finite(limits.get("action_rpc_seconds"), f"{label} action timeout") != 1.0
        or finite(limits.get("startup_seconds"), f"{label} startup timeout") != 15.0
        or finite(limits.get("game_seconds_between_steps"), f"{label} game timeout") != 180.0
        or limits.get("remaining_overage_time") != 0
    ):
        raise CompareError(f"{label} timeout contract drift")

    progress = report.get("progress")
    if (
        not isinstance(progress, Mapping)
        or progress.get("state") != "complete"
        or progress.get("phase") != "finalize"
        or progress.get("active_game") is not None
    ):
        raise CompareError(f"{label} report did not finish finalization")
    exact_int(progress.get("planned_games"), EXPECTED_GAMES_PER_ARM, f"{label} planned games")
    exact_int(progress.get("recorded_games"), EXPECTED_GAMES_PER_ARM, f"{label} recorded games")

    games = report.get("games")
    if not isinstance(games, list) or len(games) != EXPECTED_GAMES_PER_ARM:
        raise CompareError(f"{label} game cardinality drift")
    indexed = {}
    for index, game in enumerate(games):
        if not isinstance(game, Mapping):
            raise CompareError(f"{label} game {index} is not an object")
        opponent = game.get("opponent")
        seed = game.get("seed")
        seat = game.get("candidate_seat")
        if (
            opponent not in EXPECTED_OPPONENTS
            or type(seed) is not int
            or seed not in EXPECTED_SEEDS
            or type(seat) is not int
            or seat not in (0, 1)
        ):
            raise CompareError(f"{label} game {index} key drift")
        key = (opponent, seed, seat)
        if key in indexed:
            raise CompareError(f"{label} duplicate cell {key}")
        if game.get("status") != "complete" or game.get("failure") is not None:
            raise CompareError(f"{label} incomplete cell {key}: {game.get('failure')!r}")
        exact_int(game.get("steps"), EXPECTED_STEPS, f"{label} {key} steps")
        exact_int(game.get("episode_steps"), EXPECTED_EPISODE_STEPS, f"{label} {key} episode steps")
        exact_int(game.get("candidate_action_count"), EXPECTED_STEPS, f"{label} {key} action count")
        digest(game.get("candidate_action_sha256"), f"{label} {key} action digest")
        digest(game.get("trace_sha256"), f"{label} {key} trace digest")
        if "finalization_errors" in game:
            raise CompareError(f"{label} cell {key} has finalization errors")

        scores = game.get("scores")
        bank = game.get("bank_snapshot")
        if not isinstance(scores, list) or len(scores) != 2 or not isinstance(bank, list) or len(bank) != 2:
            raise CompareError(f"{label} cell {key} lacks terminal cash evidence")
        for player in (0, 1):
            score = finite(scores[player], f"{label} {key} score {player}")
            balance = finite(bank[player], f"{label} {key} bank {player}")
            if score != balance:
                raise CompareError(f"{label} cell {key} score/bank mismatch at seat {player}")

        actors = game.get("actors")
        if not isinstance(actors, list) or len(actors) != 2:
            raise CompareError(f"{label} cell {key} actor receipt drift")
        for player, actor in enumerate(actors):
            if not isinstance(actor, Mapping):
                raise CompareError(f"{label} cell {key} actor {player} invalid")
            exact_int(actor.get("calls"), EXPECTED_STEPS, f"{label} {key} actor {player} calls")
        indexed[key] = game

    expected_keys = {
        (opponent, seed, seat)
        for opponent in EXPECTED_OPPONENTS
        for seed in EXPECTED_SEEDS
        for seat in (0, 1)
    }
    if set(indexed) != expected_keys:
        raise CompareError(f"{label} panel cell set drift")
    return indexed


def classify(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    audit: Mapping[str, Any],
    evaluator_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    if audit.get("schema_version") != 1 or audit.get("operation") != OPERATION:
        raise CompareError("source audit operation drift")
    evaluator_sha = validate_evaluator(evaluator_receipt, audit)
    control_id = audit.get("control")
    candidate_id = audit.get("candidate")
    if not isinstance(control_id, Mapping) or not isinstance(candidate_id, Mapping):
        raise CompareError("source audit arm identities missing")
    control_sha = digest(control_id.get("sha256"), "control carrier sha256")
    candidate_sha = digest(candidate_id.get("sha256"), "candidate carrier sha256")
    if control_sha == candidate_sha:
        raise CompareError("control and candidate entry identities alias")

    before = validate_report(
        control, label="control", entry_sha256=control_sha,
        evaluator_sha256=evaluator_sha, audit=audit,
    )
    after = validate_report(
        candidate, label="candidate", entry_sha256=candidate_sha,
        evaluator_sha256=evaluator_sha, audit=audit,
    )

    cells = []
    strata: dict[tuple[str, int], list[float]] = defaultdict(list)
    for key in sorted(before):
        opponent, seed, seat = key
        left, right = before[key], after[key]
        own_left = finite(left["scores"][seat], f"control own {key}")
        own_right = finite(right["scores"][seat], f"candidate own {key}")
        rival_left = finite(left["scores"][1-seat], f"control rival {key}")
        rival_right = finite(right["scores"][1-seat], f"candidate rival {key}")
        own_delta = own_right - own_left
        rival_delta = rival_right - rival_left
        margin_delta = (own_right - rival_right) - (own_left - rival_left)
        changed = left["candidate_action_sha256"] != right["candidate_action_sha256"]
        strata[(opponent, seat)].append(own_delta)
        cells.append({
            "opponent": opponent,
            "seed": seed,
            "candidate_seat": seat,
            "action_changed": changed,
            "control_candidate_action_sha256": left["candidate_action_sha256"],
            "candidate_candidate_action_sha256": right["candidate_action_sha256"],
            "control_own_cash": own_left,
            "candidate_own_cash": own_right,
            "own_cash_delta": own_delta,
            "control_opponent_cash": rival_left,
            "candidate_opponent_cash": rival_right,
            "opponent_cash_delta": rival_delta,
            "control_margin": own_left - rival_left,
            "candidate_margin": own_right - rival_right,
            "margin_delta": margin_delta,
        })

    own = [row["own_cash_delta"] for row in cells]
    rival = [row["opponent_cash_delta"] for row in cells]
    margin = [row["margin_delta"] for row in cells]
    activation = sum(row["action_changed"] for row in cells)
    stratum_rows = []
    for (opponent, seat), values in sorted(strata.items()):
        stratum_rows.append({
            "opponent": opponent,
            "candidate_seat": seat,
            "cells": len(values),
            "mean_own_cash_delta": mean(values),
            "median_own_cash_delta": float(statistics.median(values)),
            "min_own_cash_delta": min(values),
            "max_own_cash_delta": max(values),
            "positive_cells": sum(value > 0 for value in values),
            "zero_cells": sum(value == 0 for value in values),
            "negative_cells": sum(value < 0 for value in values),
        })

    metrics = {
        "paired_cells": len(cells),
        "official_games": len(cells) * 2,
        "action_changed_cells": activation,
        "action_unchanged_cells": len(cells) - activation,
        "mean_own_cash_delta": mean(own),
        "median_own_cash_delta": float(statistics.median(own)),
        "min_own_cash_delta": min(own),
        "max_own_cash_delta": max(own),
        "mean_opponent_cash_delta": mean(rival),
        "mean_margin_delta": mean(margin),
        "positive_own_cash_cells": sum(value > 0 for value in own),
        "zero_own_cash_cells": sum(value == 0 for value in own),
        "negative_own_cash_cells": sum(value < 0 for value in own),
    }
    criteria = {
        "candidate_actions_changed": activation > 0,
        "global_mean_own_cash_positive": metrics["mean_own_cash_delta"] > 0,
        "global_median_own_cash_nonnegative": metrics["median_own_cash_delta"] >= 0,
        "all_opponent_seat_strata_nonnegative": all(
            row["mean_own_cash_delta"] >= 0 for row in stratum_rows
        ),
    }
    advance = all(criteria.values())
    canonical = lambda value: json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return {
        "schema_version": 1,
        "operation": OPERATION,
        "verdict": "advance" if advance else "reject",
        "advance": advance,
        "criteria": criteria,
        "metrics": metrics,
        "strata": stratum_rows,
        "cells": cells,
        "identity": {
            "git_head": audit.get("git_head"),
            "archive_sha256": audit.get("archive", {}).get("sha256"),
            "control_carrier_sha256": control_sha,
            "candidate_carrier_sha256": candidate_sha,
            "evaluator_sha256": evaluator_sha,
            "control_report_sha256": hashlib.sha256(canonical(control)).hexdigest(),
            "candidate_report_sha256": hashlib.sha256(canonical(candidate)).hexdigest(),
        },
    }


def markdown(report: Mapping[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# TITAN V3 Capillary action-bound panel",
        "",
        f"**Verdict: {str(report['verdict']).upper()}**",
        "",
        "| Criterion | Pass |",
        "|---|---:|",
    ]
    lines.extend(
        f"| `{key}` | {'YES' if value else 'NO'} |"
        for key, value in report["criteria"].items()
    )
    lines += [
        "",
        "| Global metric | Value |",
        "|---|---:|",
        f"| Paired cells / official games | {metrics['paired_cells']} / {metrics['official_games']} |",
        f"| Action-changed cells | {metrics['action_changed_cells']} |",
        f"| Mean / median own-cash delta | {metrics['mean_own_cash_delta']:+.6f} / {metrics['median_own_cash_delta']:+.6f} |",
        f"| Min / max own-cash delta | {metrics['min_own_cash_delta']:+.6f} / {metrics['max_own_cash_delta']:+.6f} |",
        f"| Mean opponent-cash / margin delta | {metrics['mean_opponent_cash_delta']:+.6f} / {metrics['mean_margin_delta']:+.6f} |",
        f"| Positive / zero / negative own cells | {metrics['positive_own_cash_cells']} / {metrics['zero_own_cash_cells']} / {metrics['negative_own_cash_cells']} |",
        "",
        "| Opponent | Seat | Mean own Δ | Median | Min | Max | + / 0 / - |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["strata"]:
        lines.append(
            f"| {row['opponent']} | {row['candidate_seat']} | "
            f"{row['mean_own_cash_delta']:+.6f} | {row['median_own_cash_delta']:+.6f} | "
            f"{row['min_own_cash_delta']:+.6f} | {row['max_own_cash_delta']:+.6f} | "
            f"{row['positive_cells']} / {row['zero_cells']} / {row['negative_cells']} |"
        )
    lines += ["", "## Exact identities", ""]
    lines.extend(f"- `{key}`: `{value}`" for key, value in report["identity"].items())
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--evaluator-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    report = classify(
        strict_json(args.control), strict_json(args.candidate),
        strict_json(args.audit), strict_json(args.evaluator_receipt),
    )
    atomic_text(args.output, json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    atomic_text(args.markdown, markdown(report))
    print(json.dumps({
        "verdict": report["verdict"],
        "criteria": report["criteria"],
        "metrics": report["metrics"],
    }, sort_keys=True))
    return 0 if report["advance"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
