#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Corrected Gemini EGG scarcity-timing frontier for canonical TITAN V4.

This is research/admission infrastructure, not a seller. It deliberately does
*not* implement the falsified "buy EGG out of the market" short squeeze. The
official engine only permits BUY_PRODUCT for WHEAT/FERTILIZER. Instead, this
module searches a narrow corrected descendant: move an already-planned literal
EGG SELL to a later market slot and let the existing full-interpreter
sale-window harness measure the realized open-loop result.

The search is intentionally conservative:
* only one existing positive literal EGG SELL may move;
* every later PASS plus the legal append slot inside the live market cap is tried;
* opponent actions and all non-market actions remain byte-for-byte unchanged;
* rankings require an actually realized equal-unit retiming;
* scarcity-positive evidence requires higher cash on the moved EGG row itself;
* total window cash/margin are consequences, never mechanism attribution.

The engine executes player market orders before town consumption. Therefore a
sale on a town-consumption tick does not capture that tick's scarcity; moving to
a later turn can. `sale_window.compare` remains the sole transition/economic
measurement authority here.
"""
from __future__ import annotations

from typing import Any

SCHEMA = "titan.v4.gemini-egg-townclock-frontier/v1"
ITEM = "EGG"
DEFAULT_MAX_DELAY = 24
DEFAULT_MARKET_CAP = 10


def _exact_int(value: Any, *, minimum: int, label: str) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} must be an exact int >= {minimum}")
    return value


def _market_cap(env: Any) -> int:
    cfg = getattr(env, "configuration", None)
    if cfg is None:
        return DEFAULT_MARKET_CAP
    getter = getattr(cfg, "get", None)
    raw = getter("maxMarketOrdersPerTurn", DEFAULT_MARKET_CAP) if callable(getter) else DEFAULT_MARKET_CAP
    if type(raw) is not int:
        raise ValueError("maxMarketOrdersPerTurn must be an exact int")
    return max(1, raw)


def _action_market(tape: list, turn: int, seat: int) -> list:
    try:
        pair = tape[turn]
        action = pair[seat]
    except (IndexError, TypeError):
        raise ValueError("malformed tape/turn/seat") from None
    if not isinstance(pair, list) or len(pair) != 2 or not isinstance(action, dict):
        raise ValueError("tape must contain two action dictionaries per turn")
    market = action.get("market", [])
    if not isinstance(market, list):
        raise ValueError("market must be a list")
    return market


def source_row(tape: list, seat: int, source_turn: int, source_row_index: int) -> list:
    """Return and authenticate the one EGG SELL this frontier is allowed to move."""
    _exact_int(seat, minimum=0, label="seat")
    if seat not in (0, 1):
        raise ValueError("seat must be 0 or 1")
    _exact_int(source_turn, minimum=0, label="source_turn")
    _exact_int(source_row_index, minimum=0, label="source_row")
    market = _action_market(tape, source_turn, seat)
    if source_row_index >= len(market):
        raise ValueError("source row absent")
    row = market[source_row_index]
    if not (
        isinstance(row, list)
        and len(row) == 3
        and row[0] == "SELL"
        and row[1] == ITEM
        and type(row[2]) is int
        and row[2] > 0
    ):
        raise ValueError("source must be a positive literal EGG SELL")
    return row


def destination_rows(tape: list, seat: int, target_turn: int, cap: int) -> list[int]:
    """Return every legal row destination without displacing inherited economics.

    Literal PASS rows inside the executable prefix are independently legal
    replacement sites. If the inherited queue is shorter than the live cap, the
    one next append index is also legal. No inherited non-PASS row is displaced.
    """
    _exact_int(cap, minimum=1, label="cap")
    market = _action_market(tape, target_turn, seat)
    rows = [index for index, row in enumerate(market[:cap]) if row == ["PASS"]]
    if len(market) < cap:
        rows.append(len(market))
    return rows


def destination_row(tape: list, seat: int, target_turn: int, cap: int) -> int | None:
    """Compatibility helper returning the first legal destination, if any."""
    rows = destination_rows(tape, seat, target_turn, cap)
    return rows[0] if rows else None


def candidate_destinations(
    tape: list,
    *,
    seat: int,
    source_turn: int,
    max_delay: int = DEFAULT_MAX_DELAY,
    cap: int = DEFAULT_MARKET_CAP,
) -> list[tuple[int, int]]:
    """Return all later `(turn,row)` destinations in deterministic tape order."""
    _exact_int(max_delay, minimum=1, label="max_delay")
    _exact_int(source_turn, minimum=0, label="source_turn")
    end = min(len(tape), source_turn + max_delay + 1)
    out: list[tuple[int, int]] = []
    for target_turn in range(source_turn + 1, end):
        out.extend(
            (target_turn, row)
            for row in destination_rows(tape, seat, target_turn, cap)
        )
    return out


def _sale_row_metrics(
    result: dict, branch: str, turn: int, seat: int, row: int
) -> tuple[int, int]:
    """Return exact sold units and sale cash for one observed market row.

    The full-interpreter observer emits one record per parsed market row. Missing,
    duplicated, type-poisoned, or negative metrics fail closed to `(0, 0)` so
    they cannot establish realized retiming or scarcity-price evidence.
    """
    try:
        rows = result[branch]["reports"][turn]["rows"]
    except (KeyError, IndexError, TypeError):
        return (0, 0)
    if not isinstance(rows, list):
        return (0, 0)
    matches = [
        record for record in rows
        if isinstance(record, dict)
        and type(record.get("seat")) is int
        and record.get("seat") == seat
        and type(record.get("row")) is int
        and record.get("row") == row
    ]
    if len(matches) != 1:
        return (0, 0)
    sold = matches[0].get("sold", 0)
    sale_cash = matches[0].get("sale_cash", 0)
    if type(sold) is not int or sold < 0 or type(sale_cash) is not int or sale_cash < 0:
        return (0, 0)
    return (sold, sale_cash)


def _filled_units(result: dict, branch: str, turn: int, seat: int, row: int) -> int:
    """Compatibility projection of the exact row observer."""
    return _sale_row_metrics(result, branch, turn, seat, row)[0]


def _load_sale_window():
    # Lazy import keeps pure shape helpers independently testable/compilable.
    import sale_window  # type: ignore

    return sale_window


def search(
    engine: Any,
    state: Any,
    env: Any,
    tape: list,
    *,
    start_step: int,
    seat: int,
    source_turn: int,
    source_row_index: int,
    max_delay: int = DEFAULT_MAX_DELAY,
) -> dict:
    """Measure all legal later EGG-sale placements under one fixed action tape.

    Every candidate is evaluated by the canonical full-interpreter sale-window
    counterfactual. The opponent remains fixed/open-loop exactly as required by
    that harness. `best_positive` means mechanism-positive *EGG row cash*: the
    same positive number of EGG units filled later and the target row earned more
    sale cash than the baseline source row. Total window cash/margin remain
    reported consequences and cannot independently mint scarcity evidence.
    """
    _exact_int(start_step, minimum=0, label="start_step")
    src = source_row(tape, seat, source_turn, source_row_index)
    cap = _market_cap(env)
    sw = _load_sale_window()

    candidates = []
    for target_turn, target_row in candidate_destinations(
        tape, seat=seat, source_turn=source_turn, max_delay=max_delay, cap=cap
    ):
        moved = sw.shift_sale(
            tape, seat, source_turn, source_row_index, target_turn, target_row
        )
        result = sw.compare(engine, state, env, tape, moved, start_step, seat)
        source_filled, source_sale_cash = _sale_row_metrics(
            result, "baseline", source_turn, seat, source_row_index
        )
        target_filled, target_sale_cash = _sale_row_metrics(
            result, "candidate", target_turn, seat, target_row
        )
        realized = source_filled > 0 and target_filled == source_filled
        sale_cash_delta = target_sale_cash - source_sale_cash
        scarcity_positive = realized and sale_cash_delta > 0
        own_delta = result["window_cash_delta"][seat]
        margin_delta = result["window_margin_delta"]
        row = {
            "target_turn": target_turn,
            "target_step": start_step + target_turn,
            "target_row": target_row,
            "delay_turns": target_turn - source_turn,
            "engagement": result["engagement"],
            "source_filled_units": source_filled,
            "target_filled_units": target_filled,
            "realized_retiming": realized,
            "source_sale_cash": source_sale_cash,
            "target_sale_cash": target_sale_cash,
            "sale_cash_delta": sale_cash_delta,
            "scarcity_price_positive": scarcity_positive,
            "own_cash_delta": own_delta,
            "window_margin_delta": margin_delta,
            "terminal_margin_delta": result["terminal_margin_delta"],
        }
        candidates.append(row)

    ranked = sorted(
        candidates,
        key=lambda row: (
            not row["realized_retiming"],
            not row["scarcity_price_positive"],
            -row["sale_cash_delta"],
            -row["own_cash_delta"],
            -row["window_margin_delta"],
            row["delay_turns"],
            row["target_turn"],
            row["target_row"],
        ),
    )
    positive = [row for row in ranked if row["scarcity_price_positive"]]
    return {
        "schema": SCHEMA,
        "item": ITEM,
        "source_turn": source_turn,
        "source_step": start_step + source_turn,
        "source_row": source_row_index,
        "source_requested_units": src[2],
        "max_delay": max_delay,
        "market_cap": cap,
        "candidate_count": len(candidates),
        "candidates": ranked,
        "best_positive": positive[0] if positive else None,
        "policy_claim": False,
        "optimality_claim": False,
        "runtime_mutation": False,
        "literal_direct_egg_short_squeeze_supported": False,
        "interpretation": (
            "bounded full-interpreter open-loop search over all legal later placements of one existing EGG SELL; "
            "scarcity-positive requires equal positive filled units and higher target-row EGG sale cash; "
            "window cash/margin are consequences, not mechanism attribution or activation"
        ),
    }
