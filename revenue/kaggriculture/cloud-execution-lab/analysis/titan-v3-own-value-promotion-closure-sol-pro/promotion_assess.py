#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Assess one fully retained native paired panel under a committed policy."""
from __future__ import annotations

from promotion_core import *
from promotion_seed import *
from promotion_manifest import *
from promotion_trajectory import *
from promotion_policy import *
from promotion_policy import _lower_quantile, _mean, _validate_panel_header

def assess(
    panel: Mapping[str, Any],
    policy: Mapping[str, Any],
    prior_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_policy, run, seeds, opponents = _validate_panel_header(
        panel, policy, prior_ledger
    )
    raw_cells = panel["cells"]
    if not isinstance(raw_cells, list):
        raise PromotionClosureError("panel cells must be a list")
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for raw in raw_cells:
        row = compare_cell(raw)
        key = (row["opponent"], row["seed"], row["candidate_seat"])
        if key in seen:
            raise PromotionClosureError(f"panel duplicates cell {key}")
        seen.add(key)
        rows.append(row)
    expected = {
        (opponent, seed, seat)
        for opponent in opponents
        for seed in seeds
        for seat in (0, 1)
    }
    if seen != expected:
        raise PromotionClosureError(
            f"panel grid mismatch: expected {len(expected)}, got {len(seen)}"
        )
    rows.sort(key=lambda row: (row["opponent"], row["seed"], row["candidate_seat"]))

    own = [row["own_cash_delta"] for row in rows]
    margin = [row["margin_delta"] for row in rows]
    opponent_seat: dict[str, list[dict[str, Any]]] = {}
    by_seed: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        opponent_seat.setdefault(
            f"{row['opponent']}|seat{row['candidate_seat']}", []
        ).append(row)
        by_seed.setdefault(row["seed"], []).append(row)

    opponent_seat_summary = {
        label: {
            "cells": len(group),
            "mean_own_cash_delta": _mean([row["own_cash_delta"] for row in group]),
            "mean_margin_delta": _mean([row["margin_delta"] for row in group]),
        }
        for label, group in sorted(opponent_seat.items())
    }
    seed_rows = [
        {
            "seed": seed,
            "cells": len(group),
            "mean_own_cash_delta": _mean([row["own_cash_delta"] for row in group]),
            "mean_margin_delta": _mean([row["margin_delta"] for row in group]),
        }
        for seed, group in sorted(by_seed.items())
    ]
    positive_seeds = sum(row["mean_own_cash_delta"] > 0 for row in seed_rows)
    negative_seeds = sum(row["mean_own_cash_delta"] < 0 for row in seed_rows)
    zero_seeds = len(seed_rows) - positive_seeds - negative_seeds
    sign_tail = Fraction(1, 2**positive_seeds) if positive_seeds and not negative_seeds else Fraction(1, 1)

    summary = {
        "cells": len(rows),
        "score_active_cells": sum(row["score_changed"] for row in rows),
        "realized_action_cells": sum(row["realized_first_divergence"] for row in rows),
        "mean_own_cash_delta": _mean(own),
        "median_own_cash_delta": statistics.median(own),
        "mean_margin_delta": _mean(margin),
        "min_own_cash_delta": min(own),
        "min_margin_delta": min(margin),
        "lower_quantile": normalized_policy["lower_quantile"],
        "lower_quantile_own_cash_delta": _lower_quantile(
            own, normalized_policy["lower_quantile"]
        ),
        "lower_quantile_margin_delta": _lower_quantile(
            margin, normalized_policy["lower_quantile"]
        ),
        "new_losses": sum(row["new_loss"] for row in rows),
        "lost_wins": sum(row["lost_win"] for row in rows),
        "outcome_regressions": sum(row["outcome_regression"] for row in rows),
        "opponent_seat": opponent_seat_summary,
        "seed_clusters": seed_rows,
        "positive_seed_clusters": positive_seeds,
        "zero_seed_clusters": zero_seeds,
        "negative_seed_clusters": negative_seeds,
        "seed_sign_tail": {
            "numerator": sign_tail.numerator,
            "denominator": sign_tail.denominator,
            "value": float(sign_tail),
        },
    }
    checks = {
        "score_active": summary["score_active_cells"] > 0,
        "positive_global_mean_own": (
            summary["mean_own_cash_delta"]
            >= normalized_policy["min_global_mean_own_delta"]
        ),
        "positive_global_mean_margin": (
            summary["mean_margin_delta"]
            >= normalized_policy["min_global_mean_margin_delta"]
        ),
        "opponent_seat_own_floor": all(
            row["mean_own_cash_delta"]
            >= normalized_policy["min_opponent_seat_mean_own_delta"]
            for row in opponent_seat_summary.values()
        ),
        "opponent_seat_margin_floor": all(
            row["mean_margin_delta"]
            >= normalized_policy["min_opponent_seat_mean_margin_delta"]
            for row in opponent_seat_summary.values()
        ),
        "cell_own_floor": summary["min_own_cash_delta"]
        >= normalized_policy["min_cell_own_delta"],
        "cell_margin_floor": summary["min_margin_delta"]
        >= normalized_policy["min_cell_margin_delta"],
        "lower_quantile_own_floor": summary["lower_quantile_own_cash_delta"]
        >= normalized_policy["min_lower_quantile_own_delta"],
        "lower_quantile_margin_floor": summary["lower_quantile_margin_delta"]
        >= normalized_policy["min_lower_quantile_margin_delta"],
        "seed_own_floor": all(
            row["mean_own_cash_delta"]
            >= normalized_policy["min_seed_mean_own_delta"]
            for row in seed_rows
        ),
        "seed_margin_floor": all(
            row["mean_margin_delta"]
            >= normalized_policy["min_seed_mean_margin_delta"]
            for row in seed_rows
        ),
        "clustered_support": (
            positive_seeds >= normalized_policy["min_positive_seed_clusters"]
            and negative_seeds <= normalized_policy["max_negative_seed_clusters"]
            and float(sign_tail) <= normalized_policy["max_seed_sign_tail"]
        ),
        "zero_new_losses": (
            not normalized_policy["require_zero_new_losses"]
            or summary["new_losses"] == 0
        ),
        "zero_lost_wins": (
            not normalized_policy["require_zero_lost_wins"]
            or summary["lost_wins"] == 0
        ),
        "zero_outcome_regressions": (
            not normalized_policy["require_zero_outcome_regressions"]
            or summary["outcome_regressions"] == 0
        ),
    }
    verdict = "PROMOTION_CANDIDATE" if all(checks.values()) else "HOLD"
    return {
        "schema_version": "titan-v3-own-value-promotion-closure-report/v1",
        "operation": panel["operation"],
        "hypothesis": panel["hypothesis"],
        "head": panel["head"],
        "run": run,
        "policy": normalized_policy,
        "policy_sha256": json_sha256(normalized_policy),
        "verdict": verdict,
        "promotion_authority": False,
        "fresh_game_spend_performed_by_this_module": False,
        "checks": checks,
        "summary": summary,
        "rows": rows,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    ledger_parser = sub.add_parser("verify-ledger")
    ledger_parser.add_argument("--ledger", type=Path, required=True)

    assess_parser = sub.add_parser("assess")
    assess_parser.add_argument("--panel", type=Path, required=True)
    assess_parser.add_argument("--policy", type=Path, required=True)
    assess_parser.add_argument("--prior-ledger", type=Path, required=True)
    assess_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "verify-ledger":
            ledger = validate_seed_ledger(strict_load(args.ledger, "seed ledger"))
            print(
                json.dumps(
                    {"entries": len(ledger["entries"]), "sha256": json_sha256(ledger)},
                    sort_keys=True,
                )
            )
            return 0
        panel = strict_load(args.panel, "trajectory panel")
        policy = strict_load(args.policy, "promotion policy")
        ledger = strict_load(args.prior_ledger, "prior seed ledger")
        report = assess(panel, policy, ledger)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"verdict": report["verdict"], "checks": report["checks"]}, sort_keys=True))
        return 0 if report["verdict"] == "PROMOTION_CANDIDATE" else 1
    except PromotionClosureError as exc:
        print(f"promotion closure error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
