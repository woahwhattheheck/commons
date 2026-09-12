# SPDX-License-Identifier: Apache-2.0
"""Apply the win-oriented gate to the all-shed intent-priority panel."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping

import compare


EXPERIMENT = "titan-v3-all-shed-intent-priority-20260910-01"
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
EXPECTED_KEYS = {
    (opponent, seed, seat)
    for opponent in EXPECTED_OPPONENTS
    for seed in EXPECTED_SEEDS
    for seat in (0, 1)
}
EXPECTED_CELLS = len(EXPECTED_KEYS)


class AdmissionError(ValueError):
    """The classifier output is incomplete, detached, or internally invalid."""


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionError(f"{label} is not an object")
    return value


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AdmissionError(f"{label} is not numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise AdmissionError(f"{label} is not finite")
    return parsed


def _outcome(own: float, rival: float) -> str:
    if own > rival:
        return "win"
    if own < rival:
        return "loss"
    return "tie"


def assess(
    report: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Recompute a conservative admission verdict from exact paired rows."""
    if receipt.get("schema_version") != 1:
        raise AdmissionError("materialization receipt schema mismatch")
    if receipt.get("experiment") != EXPERIMENT:
        raise AdmissionError("materialization receipt experiment mismatch")
    source = _mapping(receipt.get("source"), "materialization source")
    candidate = _mapping(
        receipt.get("ablation"),
        "materialization candidate",
    )
    if (
        source.get("scheduler_git_blob_sha1")
        != compare.V2_SCHEDULER_BLOB
    ):
        raise AdmissionError("control is not frozen V2")
    if candidate.get("changed_files") != ["scheduler.py"]:
        raise AdmissionError("candidate is not scheduler-only")
    if (
        candidate.get("old_occurrences_before") != 1
        or candidate.get("old_occurrences_after") != 0
        or candidate.get("new_occurrences_before") != 0
        or candidate.get("new_occurrences_after") != 1
    ):
        raise AdmissionError("priority replacement cardinality is invalid")

    underlying = report.get("verdict")
    underlying_exit = report.get("exit_code")
    if not isinstance(underlying, str):
        raise AdmissionError("underlying classifier verdict is missing")
    if type(underlying_exit) is not int:
        raise AdmissionError("underlying classifier exit code is invalid")

    rows = report.get("rows")
    if not isinstance(rows, list) or len(rows) != EXPECTED_CELLS:
        raise AdmissionError(
            f"report must contain exactly {EXPECTED_CELLS} paired rows"
        )

    seen: set[tuple[str, int, int]] = set()
    normalized: list[dict[str, Any]] = []
    transitions: dict[str, int] = defaultdict(int)
    for index, raw in enumerate(rows):
        row = _mapping(raw, f"row {index}")
        opponent = row.get("opponent")
        seed = row.get("seed")
        seat = row.get("seat")
        if type(opponent) is not str or not opponent:
            raise AdmissionError(f"row {index} opponent is invalid")
        if type(seed) is not int:
            raise AdmissionError(f"row {index} seed is invalid")
        if type(seat) is not int or seat not in (0, 1):
            raise AdmissionError(f"row {index} seat is invalid")
        key = (opponent, seed, seat)
        if key in seen:
            raise AdmissionError(f"duplicate paired row {key!r}")
        seen.add(key)

        control_own = _number(
            row.get("control_own"),
            f"row {index} control own",
        )
        control_rival = _number(
            row.get("control_rival"),
            f"row {index} control rival",
        )
        candidate_own = _number(
            row.get("ablation_own"),
            f"row {index} candidate own",
        )
        candidate_rival = _number(
            row.get("ablation_rival"),
            f"row {index} candidate rival",
        )
        own_delta = candidate_own - control_own
        rival_delta = candidate_rival - control_rival
        margin_delta = (
            candidate_own
            - candidate_rival
            - (control_own - control_rival)
        )
        for field, derived in (
            ("own_delta", own_delta),
            ("rival_delta", rival_delta),
            ("margin_delta", margin_delta),
        ):
            supplied = _number(
                row.get(field),
                f"row {index} {field}",
            )
            if supplied != derived:
                raise AdmissionError(
                    f"row {index} {field} is detached from scores"
                )
        changed = row.get("candidate_action_changed")
        if type(changed) is not bool:
            raise AdmissionError(
                f"row {index} candidate_action_changed is not boolean"
            )

        before = _outcome(control_own, control_rival)
        after = _outcome(candidate_own, candidate_rival)
        transitions[f"{before}->{after}"] += 1
        normalized.append(
            {
                "opponent": opponent,
                "seed": seed,
                "seat": seat,
                "control_outcome": before,
                "candidate_outcome": after,
                "control_own": control_own,
                "control_rival": control_rival,
                "candidate_own": candidate_own,
                "candidate_rival": candidate_rival,
                "own_delta": own_delta,
                "rival_delta": rival_delta,
                "margin_delta": margin_delta,
                "candidate_action_changed": changed,
            }
        )

    if seen != EXPECTED_KEYS:
        missing = sorted(EXPECTED_KEYS - seen)
        extra = sorted(seen - EXPECTED_KEYS)
        raise AdmissionError(
            f"paired grid mismatch; missing={missing}, extra={extra}"
        )

    own_deltas = [row["own_delta"] for row in normalized]
    margin_deltas = [row["margin_delta"] for row in normalized]
    changed_cells = sum(row["candidate_action_changed"] for row in normalized)
    new_losses = [
        row
        for row in normalized
        if row["control_outcome"] != "loss"
        and row["candidate_outcome"] == "loss"
    ]
    lost_wins = [
        row
        for row in normalized
        if row["control_outcome"] == "win"
        and row["candidate_outcome"] != "win"
    ]

    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in normalized:
        grouped[(row["opponent"], row["seat"])].append(row)
    strata: dict[str, dict[str, Any]] = {}
    for (opponent, seat), values in sorted(grouped.items()):
        own = [row["own_delta"] for row in values]
        margin = [row["margin_delta"] for row in values]
        strata[f"{opponent}:seat-{seat}"] = {
            "opponent": opponent,
            "seat": seat,
            "cells": len(values),
            "changed_cells": sum(
                row["candidate_action_changed"] for row in values
            ),
            "positive_cells": sum(value > 0 for value in own),
            "zero_cells": sum(value == 0 for value in own),
            "negative_cells": sum(value < 0 for value in own),
            "mean_own_delta": statistics.mean(own),
            "median_own_delta": statistics.median(own),
            "mean_margin_delta": statistics.mean(margin),
            "new_losses": sum(
                row["control_outcome"] != "loss"
                and row["candidate_outcome"] == "loss"
                for row in values
            ),
        }
    expected_strata = {
        f"{opponent}:seat-{seat}"
        for opponent in EXPECTED_OPPONENTS
        for seat in (0, 1)
    }
    if set(strata) != expected_strata:
        raise AdmissionError(
            "opponent-by-seat grid must contain the exact four strata"
        )

    overall = {
        "cells": len(normalized),
        "candidate_action_changed_cells": changed_cells,
        "positive_cells": sum(value > 0 for value in own_deltas),
        "zero_cells": sum(value == 0 for value in own_deltas),
        "negative_cells": sum(value < 0 for value in own_deltas),
        "mean_own_delta": statistics.mean(own_deltas),
        "median_own_delta": statistics.median(own_deltas),
        "minimum_own_delta": min(own_deltas),
        "maximum_own_delta": max(own_deltas),
        "mean_margin_delta": statistics.mean(margin_deltas),
        "new_losses": len(new_losses),
        "lost_wins": len(lost_wins),
    }

    gates = {
        "underlying_upside_screen": (
            underlying == "UPSIDE_SCREEN" and underlying_exit == 0
        ),
        "candidate_action_activation": changed_cells > 0,
        "positive_mean_own_cash": overall["mean_own_delta"] > 0,
        "nonnegative_median_own_cash": (
            overall["median_own_delta"] >= 0
        ),
        "nonnegative_cell_balance": (
            overall["positive_cells"] >= overall["negative_cells"]
        ),
        "positive_mean_margin": overall["mean_margin_delta"] > 0,
        "zero_new_losses": not new_losses,
        "all_opponent_seat_strata_nonnegative": all(
            value["mean_own_delta"] >= 0
            and value["median_own_delta"] >= 0
            and value["positive_cells"] >= value["negative_cells"]
            and value["mean_margin_delta"] >= 0
            and value["new_losses"] == 0
            for value in strata.values()
        ),
    }
    failed = [name for name, passed in gates.items() if not passed]
    verdict = "ADMIT" if not failed else "REJECT"
    reason = (
        "all win-oriented priority gates passed"
        if not failed
        else "failed gates: " + ", ".join(failed)
    )
    return {
        "schema_version": 1,
        "experiment": EXPERIMENT,
        "git_head": report.get("git_head"),
        "verdict": verdict,
        "reason": reason,
        "exit_code": 0 if verdict == "ADMIT" else 1,
        "underlying_verdict": underlying,
        "underlying_exit_code": underlying_exit,
        "gates": gates,
        "overall": overall,
        "outcome_transitions": dict(sorted(transitions.items())),
        "by_opponent_seat": strata,
        "new_loss_rows": new_losses,
        "lost_win_rows": lost_wins,
    }


def markdown(result: Mapping[str, Any]) -> str:
    lines = [
        "# TITAN V3 all-shed intent-priority admission",
        "",
        f"**Verdict:** `{result['verdict']}` — {result['reason']}",
        "",
    ]
    overall = result.get("overall")
    if isinstance(overall, Mapping):
        lines.extend(
            [
                f"- Complete paired cells: {overall['cells']}",
                (
                    "- Candidate-action-changed cells: "
                    f"{overall['candidate_action_changed_cells']}"
                ),
                (
                    "- Mean / median own-cash delta: "
                    f"{overall['mean_own_delta']:+.3f} / "
                    f"{overall['median_own_delta']:+.3f}"
                ),
                (
                    "- Mean margin delta: "
                    f"{overall['mean_margin_delta']:+.3f}"
                ),
                (
                    "- Positive / zero / negative own cells: "
                    f"{overall['positive_cells']} / "
                    f"{overall['zero_cells']} / "
                    f"{overall['negative_cells']}"
                ),
                (
                    "- New losses / lost wins: "
                    f"{overall['new_losses']} / {overall['lost_wins']}"
                ),
                "",
                "## Admission gates",
                "",
            ]
        )
        for name, passed in result["gates"].items():
            lines.append(f"- {'PASS' if passed else 'FAIL'} — `{name}`")
        lines.extend(
            [
                "",
                "## Opponent × seat strata",
                "",
                (
                    "| Stratum | Cells | Changed | + / 0 / - | "
                    "Mean own Δ | Median own Δ | Mean margin Δ | New losses |"
                ),
                (
                    "|---|---:|---:|---:|---:|---:|---:|---:|"
                ),
            ]
        )
        for name, value in result["by_opponent_seat"].items():
            lines.append(
                f"| {name} | {value['cells']} | "
                f"{value['changed_cells']} | "
                f"{value['positive_cells']} / "
                f"{value['zero_cells']} / "
                f"{value['negative_cells']} | "
                f"{value['mean_own_delta']:+.3f} | "
                f"{value['median_own_delta']:+.3f} | "
                f"{value['mean_margin_delta']:+.3f} | "
                f"{value['new_losses']} |"
            )
        lines.extend(["", "## Outcome transitions", ""])
        for transition, count in result["outcome_transitions"].items():
            lines.append(f"- `{transition}`: {count}")
    lines.extend(
        [
            "",
            (
                "This is an exact offline causal admission gate, not a "
                "leaderboard result or submission authorization."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    try:
        result = assess(
            compare.strict_object(args.report),
            compare.strict_object(args.receipt),
        )
    except (
        AdmissionError,
        compare.CompareError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        result = {
            "schema_version": 1,
            "experiment": EXPERIMENT,
            "verdict": "INVALID",
            "reason": str(exc),
            "exit_code": 2,
        }

    compare.atomic_write(
        args.output,
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
    )
    compare.atomic_write(args.markdown, markdown(result))
    print(
        json.dumps(
            {
                "verdict": result["verdict"],
                "reason": result["reason"],
                "exit_code": result["exit_code"],
                "overall": result.get("overall"),
                "gates": result.get("gates"),
                "by_opponent_seat": result.get(
                    "by_opponent_seat"
                ),
            },
            sort_keys=True,
        )
    )
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
