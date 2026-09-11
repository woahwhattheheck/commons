#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-only audit for B2 rival front-run residual on frozen V3.1 tapes.

Frozen R04 already enables ROW_ORDER, which sorts only the leading SELL block. The
only row-order residual is therefore a SELL that appears after the first non-SELL row.
This audit enumerates those occurrences and classifies the rows that would have to be
crossed to promote that SELL immediately before the first non-SELL barrier.

Market slot indices are preserved exactly.  In particular, falsey placeholders are
NOT compacted away: R04's own ``order_sells`` stops its leading block at a falsey slot,
and the official engine advances market rows by raw list index.  A falsey/malformed
barrier therefore makes a simple promotion shape unsafe rather than disappearing from
the audit.

A later candidate may only use shapes classified ``fixed_prefix_only`` and must still
prove at runtime that the crossed fixed-cost operations were already affordable without
cash from the promoted sale. That keeps their success/failure semantics unchanged while
moving the SELL to an earlier lockstep market index. BUY_PRODUCT is never classified
safe here because its quote depends on market inventory; crossing another SELL is also
excluded because it changes our own market-price sequence.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OVERLAY = HERE.parents[1] / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

from r01_tapes import load_tapes  # noqa: E402

FIXED_PREFIX_OPS = {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_ANIMAL"}
EXCLUDED_SELL_ITEMS = {"WHEAT", "FERTILIZER"}


def _rows(action):
    if not isinstance(action, dict):
        return []
    rows = action.get("market", [])
    return rows if isinstance(rows, list) else []


def _op(row):
    if not isinstance(row, list) or not row or not isinstance(row[0], str):
        return "MALFORMED"
    return row[0]


def _sell(row):
    return (
        isinstance(row, list)
        and len(row) >= 3
        and row[0] == "SELL"
        and isinstance(row[1], str)
        and type(row[2]) is int
        and row[2] > 0
    )


def audit():
    tapes = load_tapes()
    occurrences = []
    by_item = Counter()
    by_barrier = Counter()
    by_crossed_shape = Counter()
    by_plan = Counter()
    fixed_by_plan = Counter()
    fixed_steps_by_plan = defaultdict(list)
    falsey_barrier_late_sells = 0

    for plan, tape in enumerate(tapes):
        for step, action in enumerate(tape):
            # Preserve the exact raw slot vector.  Do not compact None/[]: both R04
            # ROW_ORDER and the engine's lockstep execution are index-sensitive.
            rows = _rows(action)
            if not rows:
                continue
            lead = 0
            while lead < len(rows) and _op(rows[lead]) == "SELL":
                lead += 1
            if lead == len(rows):
                continue

            barrier = rows[lead]
            barrier_op = _op(barrier)
            barrier_falsey = barrier in (None, [])

            for index in range(lead + 1, len(rows)):
                row = rows[index]
                if not _sell(row):
                    continue
                item = row[1]
                crossed = rows[lead:index]
                crossed_ops = [_op(r) for r in crossed]
                fixed_prefix_only = bool(crossed) and all(
                    op in FIXED_PREFIX_OPS for op in crossed_ops
                )
                # WHEAT/FERTILIZER are kept out of any future generic promotion.
                candidate_shape = fixed_prefix_only and item not in EXCLUDED_SELL_ITEMS
                if barrier_falsey:
                    falsey_barrier_late_sells += 1
                record = {
                    "plan": plan,
                    "step": step,
                    "day": step // 24,
                    "hour": step % 24,
                    "row_index": index,
                    "promotion_index": lead,
                    "rows_advanced": index - lead,
                    "sell": list(row),
                    "barrier_op": barrier_op,
                    "barrier_falsey": barrier_falsey,
                    "crossed_rows": [list(r) if isinstance(r, list) else r for r in crossed],
                    "crossed_ops": crossed_ops,
                    "fixed_prefix_only": fixed_prefix_only,
                    "candidate_shape": candidate_shape,
                    "needs_runtime_affordability_proof": candidate_shape,
                }
                occurrences.append(record)
                by_item[item] += 1
                by_barrier["FALSEY" if barrier_falsey else barrier_op] += 1
                by_crossed_shape["/".join(crossed_ops)] += 1
                by_plan[plan] += 1
                if candidate_shape:
                    fixed_by_plan[plan] += 1
                    fixed_steps_by_plan[plan].append(step)

    return {
        "schema": "titan-v31-b2-row-frontrun-audit-v2",
        "frozen_tape_count": len(tapes),
        "engine_contract": {
            "same_row_quote": "both players use same pre-commit market inventory",
            "residual": "SELL rows after first non-SELL/raw-slot barrier; ROW_ORDER already owns leading SELL block",
            "promotion_target": "same raw slot immediately before first barrier",
            "slot_custody": "falsey placeholders are preserved exactly and are never candidate-safe",
        },
        "totals": {
            "late_sell_occurrences": len(occurrences),
            "late_sells_behind_falsey_barrier": falsey_barrier_late_sells,
            "candidate_shape_occurrences": sum(fixed_by_plan.values()),
            "plans_with_late_sell": len(by_plan),
            "plans_with_candidate_shape": len(fixed_by_plan),
        },
        "by_item": dict(sorted(by_item.items())),
        "by_barrier": dict(sorted(by_barrier.items())),
        "by_crossed_shape": dict(sorted(by_crossed_shape.items())),
        "by_plan": {str(k): v for k, v in sorted(by_plan.items())},
        "candidate_by_plan": {str(k): v for k, v in sorted(fixed_by_plan.items())},
        "candidate_steps_by_plan": {
            str(k): sorted(v) for k, v in sorted(fixed_steps_by_plan.items())
        },
        "occurrences": occurrences,
    }


def main():
    print(json.dumps(audit(), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
