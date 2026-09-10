# SPDX-License-Identifier: Apache-2.0
"""Fail-closed admission for a matched 2x2 TITAN gameplay factorial."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
from typing import Any, Iterable, Mapping

ARMS = ("control", "own_only", "strict_only", "both")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
OUTCOME_RANK = {"loss": 0, "draw": 1, "win": 2}


class AdmissionError(ValueError):
    """One report cannot support a matched, source-bound comparison."""


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AdmissionError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise AdmissionError(f"{label} must be finite")
    return result


def _integer(value: Any, label: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AdmissionError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise AdmissionError(f"{label} must be >= {minimum}")
    return value


def _outcome(margin: float) -> str:
    if margin > 0:
        return "win"
    if margin < 0:
        return "loss"
    return "draw"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _validate_identity(name: str, report: Mapping[str, Any]) -> dict[str, Any]:
    seeds = report.get("seeds")
    if not isinstance(seeds, list) or not seeds:
        raise AdmissionError(f"{name}: missing nonempty seeds")
    checked_seeds = [_integer(seed, f"{name}.seeds") for seed in seeds]
    if len(checked_seeds) != len(set(checked_seeds)):
        raise AdmissionError(f"{name}: duplicate top-level seeds")
    opponents = report.get("opponents")
    if not isinstance(opponents, dict) or not opponents:
        raise AdmissionError(f"{name}: missing opponents")
    labels = sorted(opponents)
    if any(not isinstance(label, str) or not label for label in labels):
        raise AdmissionError(f"{name}: invalid opponent label")
    progress = report.get("progress")
    if not isinstance(progress, dict) or progress.get("state") != "complete":
        raise AdmissionError(f"{name}: evaluator did not publish complete progress")
    reproducibility = report.get("reproducibility")
    if not isinstance(reproducibility, dict):
        raise AdmissionError(f"{name}: missing reproducibility recheck")
    if reproducibility.get("checked") is not True or reproducibility.get("same_trace_and_scores") is not True:
        raise AdmissionError(f"{name}: reproducibility recheck failed")
    original_trace = reproducibility.get("original_trace")
    replay_trace = reproducibility.get("replay_trace")
    if (not isinstance(original_trace, str) or HEX64.fullmatch(original_trace) is None
            or replay_trace != original_trace):
        raise AdmissionError(f"{name}: reproducibility trace binding failed")
    for field in (
        "engine_ref", "engine_sha256", "loader_sha256", "evaluator_sha256",
        "python", "platform", "agent_rng_seed", "limits",
    ):
        if field not in report:
            raise AdmissionError(f"{name}: missing {field}")
    return {
        "engine_ref": report["engine_ref"],
        "engine_sha256": report["engine_sha256"],
        "loader_sha256": report["loader_sha256"],
        "evaluator_sha256": report["evaluator_sha256"],
        "python": report["python"],
        "platform": report["platform"],
        "seeds": checked_seeds,
        "opponent_labels": labels,
        "opponents": opponents,
        "agent_rng_seed": report["agent_rng_seed"],
        "limits": report["limits"],
    }


def validate_report(name: str, report: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(report, Mapping):
        raise AdmissionError(f"{name}: report must be an object")
    identity = _validate_identity(name, report)
    games = report.get("games")
    if not isinstance(games, list) or not games:
        raise AdmissionError(f"{name}: missing games")
    rows: dict[tuple[str, int, int], dict[str, Any]] = {}
    observed_seeds: set[int] = set()
    observed_opponents: set[str] = set()
    seats_by_pair: dict[tuple[str, int], set[int]] = defaultdict(set)
    for index, game in enumerate(games):
        prefix = f"{name}.games[{index}]"
        if not isinstance(game, Mapping):
            raise AdmissionError(f"{prefix} must be an object")
        opponent = game.get("opponent")
        if not isinstance(opponent, str) or not opponent:
            raise AdmissionError(f"{prefix}.opponent must be nonempty text")
        seed = _integer(game.get("seed"), f"{prefix}.seed")
        seat = _integer(game.get("candidate_seat"), f"{prefix}.candidate_seat")
        if seat not in (0, 1):
            raise AdmissionError(f"{prefix}.candidate_seat must be 0 or 1")
        key = (opponent, seed, seat)
        if key in rows:
            raise AdmissionError(f"{name}: duplicate game cell {key!r}")
        if game.get("status") != "complete":
            raise AdmissionError(f"{name}: incomplete game cell {key!r}")
        if game.get("failure") is not None:
            raise AdmissionError(f"{name}: completed game carries failure at {key!r}")
        scores = game.get("scores")
        if not isinstance(scores, list) or len(scores) != 2:
            raise AdmissionError(f"{name}: invalid scores at {key!r}")
        left = _number(scores[0], f"{prefix}.scores[0]")
        right = _number(scores[1], f"{prefix}.scores[1]")
        own, rival = (left, right) if seat == 0 else (right, left)
        margin = own - rival
        action_digest = game.get("candidate_action_sha256")
        if not isinstance(action_digest, str) or HEX64.fullmatch(action_digest) is None:
            raise AdmissionError(f"{name}: invalid candidate action digest at {key!r}")
        action_count = _integer(
            game.get("candidate_action_count"),
            f"{prefix}.candidate_action_count",
            minimum=1,
        )
        steps = _integer(game.get("steps"), f"{prefix}.steps", minimum=1)
        if action_count != steps:
            raise AdmissionError(f"{name}: action count/step mismatch at {key!r}")
        trace_digest = game.get("trace_sha256")
        if not isinstance(trace_digest, str) or HEX64.fullmatch(trace_digest) is None:
            raise AdmissionError(f"{name}: invalid complete trace digest at {key!r}")
        rows[key] = {
            "own": own,
            "rival": rival,
            "margin": margin,
            "outcome": _outcome(margin),
            "candidate_action_sha256": action_digest,
            "candidate_action_count": action_count,
            "trace_sha256": trace_digest,
        }
        observed_seeds.add(seed)
        observed_opponents.add(opponent)
        seats_by_pair[(opponent, seed)].add(seat)
    if observed_seeds != set(identity["seeds"]):
        raise AdmissionError(f"{name}: game seeds do not match top-level seeds")
    if observed_opponents != set(identity["opponent_labels"]):
        raise AdmissionError(f"{name}: game opponents do not match top-level opponents")
    missing_seats = [pair for pair, seats in seats_by_pair.items() if seats != {0, 1}]
    if missing_seats:
        raise AdmissionError(f"{name}: both seats missing for {missing_seats[0]!r}")
    expected_cells = len(identity["seeds"]) * len(identity["opponent_labels"]) * 2
    if len(rows) != expected_cells:
        raise AdmissionError(
            f"{name}: expected {expected_cells} cells, found {len(rows)}"
        )
    progress = report["progress"]
    if (progress.get("planned_games") != expected_cells
            or progress.get("recorded_games") != expected_cells
            or progress.get("active_game") is not None
            or progress.get("recheck_requested") is not True):
        raise AdmissionError(f"{name}: terminal progress counters are not bound")
    return {"identity": identity, "rows": rows}


def _mean(values: Iterable[float]) -> float:
    sequence = list(values)
    if not sequence:
        raise AdmissionError("cannot summarize an empty cell set")
    return float(statistics.mean(sequence))


def _median(values: Iterable[float]) -> float:
    sequence = list(values)
    if not sequence:
        raise AdmissionError("cannot summarize an empty cell set")
    return float(statistics.median(sequence))


def _record(rows: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    output = {"wins": 0, "draws": 0, "losses": 0}
    for row in rows:
        key = {"win": "wins", "draw": "draws", "loss": "losses"}[row["outcome"]]
        output[key] += 1
    return output


def _summarize_delta_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise AdmissionError("cannot summarize an empty contrast")
    metrics: dict[str, Any] = {}
    for field in ("own_delta", "rival_delta", "margin_delta"):
        values = [float(row[field]) for row in rows]
        metrics[field.removesuffix("_delta")] = {
            "mean_delta": _mean(values),
            "median_delta": _median(values),
            "min_delta": min(values),
            "max_delta": max(values),
            "total_delta": float(sum(values)),
        }
    return {
        "cells": len(rows),
        "action_changed_cells": sum(row["action_changed"] for row in rows),
        "trace_changed_cells": sum(row["trace_changed"] for row in rows),
        "new_losses": sum(row["new_loss"] for row in rows),
        "lost_wins": sum(row["lost_win"] for row in rows),
        "gained_wins": sum(row["gained_win"] for row in rows),
        "base_record": _record(row["base"] for row in rows),
        "candidate_record": _record(row["candidate"] for row in rows),
        **metrics,
    }


def contrast(
    base_name: str,
    candidate_name: str,
    base_rows: Mapping[tuple[str, int, int], Mapping[str, Any]],
    candidate_rows: Mapping[tuple[str, int, int], Mapping[str, Any]],
) -> dict[str, Any]:
    if set(base_rows) != set(candidate_rows):
        raise AdmissionError(f"cell grid mismatch: {base_name} vs {candidate_name}")
    delta_rows: list[dict[str, Any]] = []
    by_stratum: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for key in sorted(base_rows):
        base = base_rows[key]
        candidate = candidate_rows[key]
        action_changed = (
            base["candidate_action_sha256"] != candidate["candidate_action_sha256"]
            or base["candidate_action_count"] != candidate["candidate_action_count"]
        )
        base_rank = OUTCOME_RANK[base["outcome"]]
        candidate_rank = OUTCOME_RANK[candidate["outcome"]]
        row = {
            "opponent": key[0],
            "seed": key[1],
            "candidate_seat": key[2],
            "base": dict(base),
            "candidate": dict(candidate),
            "own_delta": candidate["own"] - base["own"],
            "rival_delta": candidate["rival"] - base["rival"],
            "margin_delta": candidate["margin"] - base["margin"],
            "action_changed": action_changed,
            "trace_changed": base["trace_sha256"] != candidate["trace_sha256"],
            "new_loss": candidate["outcome"] == "loss" and base["outcome"] != "loss",
            "lost_win": base["outcome"] == "win" and candidate["outcome"] != "win",
            "gained_win": candidate["outcome"] == "win" and base["outcome"] != "win",
            "outcome_rank_delta": candidate_rank - base_rank,
        }
        delta_rows.append(row)
        by_stratum[(key[0], key[2])].append(row)
    return {
        "base": base_name,
        "candidate": candidate_name,
        "overall": _summarize_delta_rows(delta_rows),
        "by_opponent_seat": {
            f"{opponent}|seat={seat}": _summarize_delta_rows(rows)
            for (opponent, seat), rows in sorted(by_stratum.items())
        },
        "cells": [
            {
                key: value
                for key, value in row.items()
                if key not in ("base", "candidate")
            }
            for row in delta_rows
        ],
    }


def _interaction(
    rows: Mapping[str, Mapping[tuple[str, int, int], Mapping[str, Any]]]
) -> dict[str, Any]:
    keys = set(rows["control"])
    if any(set(rows[arm]) != keys for arm in ARMS):
        raise AdmissionError("cannot compute interaction on mismatched grids")
    cell_rows: list[dict[str, Any]] = []
    by_stratum: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for key in sorted(keys):
        values: dict[str, float] = {}
        for metric in ("own", "rival", "margin"):
            values[metric] = (
                rows["both"][key][metric]
                - rows["strict_only"][key][metric]
                - rows["own_only"][key][metric]
                + rows["control"][key][metric]
            )
        row = {
            "opponent": key[0],
            "seed": key[1],
            "candidate_seat": key[2],
            **{f"{metric}_interaction": value for metric, value in values.items()},
        }
        cell_rows.append(row)
        by_stratum[(key[0], key[2])].append(row)

    def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {"cells": len(items)}
        for metric in ("own", "rival", "margin"):
            values = [float(item[f"{metric}_interaction"]) for item in items]
            output[metric] = {
                "mean": _mean(values),
                "median": _median(values),
                "min": min(values),
                "max": max(values),
                "total": float(sum(values)),
            }
        return output

    overall = summarize(cell_rows)
    own_mean = overall["own"]["mean"]
    margin_mean = overall["margin"]["mean"]
    if own_mean >= 0 and margin_mean > 0:
        classification = "synergistic"
    elif own_mean <= 0 and margin_mean < 0:
        classification = "antagonistic"
    elif own_mean == 0 and margin_mean == 0:
        classification = "additive"
    else:
        classification = "mixed"
    return {
        "formula": "(BOTH - STRICT_ONLY) - (OWN_ONLY - CONTROL)",
        "equivalent_formula": "BOTH - OWN_ONLY - STRICT_ONLY + CONTROL",
        "overall": overall,
        "by_opponent_seat": {
            f"{opponent}|seat={seat}": summarize(items)
            for (opponent, seat), items in sorted(by_stratum.items())
        },
        "classification": classification,
        "cells": cell_rows,
    }


def _safe_contrast(value: Mapping[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    overall = value["overall"]
    if overall["new_losses"]:
        reasons.append(f"{overall['new_losses']} new loss(es)")
    if overall["lost_wins"]:
        reasons.append(f"{overall['lost_wins']} lost win(s)")
    for metric in ("own", "margin"):
        if overall[metric]["mean_delta"] < 0:
            reasons.append(f"global mean {metric} delta is negative")
    for name, stratum in value["by_opponent_seat"].items():
        for metric in ("own", "margin"):
            if stratum[metric]["mean_delta"] < 0:
                reasons.append(f"{name} mean {metric} delta is negative")
    return not reasons, reasons


def analyze_reports(reports: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    if set(reports) != set(ARMS):
        raise AdmissionError(f"reports must contain exactly {ARMS!r}")
    validated = {arm: validate_report(arm, reports[arm]) for arm in ARMS}
    reference_identity = validated["control"]["identity"]
    for arm in ARMS[1:]:
        if _canonical(validated[arm]["identity"]) != _canonical(reference_identity):
            raise AdmissionError(f"evaluation identity mismatch: control vs {arm}")
    grids = {arm: set(validated[arm]["rows"]) for arm in ARMS}
    if any(grid != grids["control"] for grid in grids.values()):
        raise AdmissionError("factorial arms do not share the exact game grid")
    rows = {arm: validated[arm]["rows"] for arm in ARMS}
    contrasts = {
        "own_vs_control": contrast("control", "own_only", rows["control"], rows["own_only"]),
        "strict_vs_control": contrast("control", "strict_only", rows["control"], rows["strict_only"]),
        "both_vs_control": contrast("control", "both", rows["control"], rows["both"]),
        "own_under_strict": contrast("strict_only", "both", rows["strict_only"], rows["both"]),
        "strict_under_own": contrast("own_only", "both", rows["own_only"], rows["both"]),
    }
    interaction = _interaction(rows)

    activity = {
        "own_factor_at_control": contrasts["own_vs_control"]["overall"]["action_changed_cells"] > 0,
        "strict_factor_at_control": contrasts["strict_vs_control"]["overall"]["action_changed_cells"] > 0,
        "own_factor_under_strict": contrasts["own_under_strict"]["overall"]["action_changed_cells"] > 0,
        "strict_factor_under_own": contrasts["strict_under_own"]["overall"]["action_changed_cells"] > 0,
        "combined_vs_control": contrasts["both_vs_control"]["overall"]["action_changed_cells"] > 0,
    }
    safety: dict[str, bool] = {}
    safety_reasons: dict[str, list[str]] = {}
    for name, value in contrasts.items():
        okay, reasons = _safe_contrast(value)
        safety[name] = okay
        safety_reasons[name] = reasons
    both = contrasts["both_vs_control"]["overall"]
    positive_signal = (
        both["own"]["mean_delta"] > 0 or both["margin"]["mean_delta"] > 0
    )
    gates = {
        "exact_matched_grid": True,
        "both_seats": True,
        "all_games_complete": True,
        **activity,
        **{f"safe_{name}": value for name, value in safety.items()},
        "combined_positive_signal": positive_signal,
    }
    # Safety violations dominate activity classification. A factor that is
    # inactive in one contrast cannot hide a new loss, lost win, or negative
    # contextual marginal elsewhere under the softer INACTIVE disposition.
    if not all(safety.values()):
        verdict = "REJECT"
    elif not all(activity.values()):
        verdict = "INACTIVE"
    elif not positive_signal:
        verdict = "REJECT"
    else:
        verdict = "ADVANCE_COMPOSITION"
    return {
        "schema_version": 1,
        "operation": "TITAN-V3-OWN-VALUE-X-STRICT-PRESSURE-FACTORIAL-20260910-01",
        "verdict": verdict,
        "identity": reference_identity,
        "cells_per_arm": len(rows["control"]),
        "total_games": len(rows["control"]) * len(ARMS),
        "gates": gates,
        "safety_reasons": safety_reasons,
        "contrasts": contrasts,
        "interaction": interaction,
        "canonical_release_modified": False,
        "promotion_authorized": False,
        "hosted_leaderboard_claim": False,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# TITAN own-value × strict-pressure factorial",
        "",
        f"**Verdict:** `{report['verdict']}`",
        "",
        f"Matched cells per arm: **{report['cells_per_arm']}**; total official-engine games: **{report['total_games']}**.",
        "",
        "| Contrast | Action-active cells | Mean own Δ | Mean rival Δ | Mean margin Δ | New losses | Lost wins |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    labels = {
        "own_vs_control": "OWN_ONLY − CONTROL",
        "strict_vs_control": "STRICT_ONLY − CONTROL",
        "both_vs_control": "BOTH − CONTROL",
        "own_under_strict": "BOTH − STRICT_ONLY",
        "strict_under_own": "BOTH − OWN_ONLY",
    }
    for key, label in labels.items():
        overall = report["contrasts"][key]["overall"]
        lines.append(
            "| {label} | {active}/{cells} | {own:+.3f} | {rival:+.3f} | {margin:+.3f} | {new} | {lost} |".format(
                label=label,
                active=overall["action_changed_cells"],
                cells=overall["cells"],
                own=overall["own"]["mean_delta"],
                rival=overall["rival"]["mean_delta"],
                margin=overall["margin"]["mean_delta"],
                new=overall["new_losses"],
                lost=overall["lost_wins"],
            )
        )
    interaction = report["interaction"]
    lines.extend(
        (
            "",
            "## Interaction",
            "",
            f"Formula: `{interaction['formula']}`",
            "",
            f"Classification: **{interaction['classification']}**; mean own interaction "
            f"`{interaction['overall']['own']['mean']:+.3f}`, mean margin interaction "
            f"`{interaction['overall']['margin']['mean']:+.3f}`.",
            "",
            "## Gates",
            "",
        )
    )
    for name, passed in report["gates"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} `{name}`")
    rejected = {
        name: reasons
        for name, reasons in report["safety_reasons"].items()
        if reasons
    }
    if rejected:
        lines.extend(("", "## Rejection reasons", ""))
        for name, reasons in rejected.items():
            for reason in reasons:
                lines.append(f"- `{name}`: {reason}")
    lines.extend(
        (
            "",
            "This is an evidence-only composition screen. It does not modify the canonical release, authorize promotion, or claim hosted-leaderboard gain.",
            "",
        )
    )
    return "\n".join(lines)


def _atomic_write(path: Path, data: bytes) -> None:
    import os
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for arm in ARMS:
        parser.add_argument(f"--{arm.replace('_', '-')}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    paths = {
        "control": args.control,
        "own_only": args.own_only,
        "strict_only": args.strict_only,
        "both": args.both,
    }
    try:
        reports = {
            arm: json.loads(path.read_text(encoding="utf-8"))
            for arm, path in paths.items()
        }
        result = analyze_reports(reports)
        result["report_files"] = {
            arm: {"path_name": path.name, "sha256": _sha256_file(path)}
            for arm, path in paths.items()
        }
        status = 0
    except (AdmissionError, json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
        result = {
            "schema_version": 1,
            "operation": "TITAN-V3-OWN-VALUE-X-STRICT-PRESSURE-FACTORIAL-20260910-01",
            "verdict": "INVALID",
            "error": f"{type(exc).__name__}: {exc}",
            "canonical_release_modified": False,
            "promotion_authorized": False,
            "hosted_leaderboard_claim": False,
        }
        status = 2
    _atomic_write(
        args.output,
        (json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8"),
    )
    markdown = (
        render_markdown(result)
        if result["verdict"] != "INVALID"
        else "# TITAN own-value × strict-pressure factorial\n\n"
             f"**Verdict:** `INVALID`\n\n`{result['error']}`\n"
    )
    _atomic_write(args.markdown, markdown.encode("utf-8"))
    print(
        json.dumps(
            {
                "verdict": result["verdict"],
                "promotion_authorized": False,
                "total_games": result.get("total_games"),
            },
            sort_keys=True,
        )
    )
    return status


if __name__ == "__main__":
    raise SystemExit(main())
