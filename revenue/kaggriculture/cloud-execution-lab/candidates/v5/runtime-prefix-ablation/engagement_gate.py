# SPDX-License-Identifier: Apache-2.0
"""Provenance-safe engagement predicates for the runtime-prefix ablation.

The submitted V3.1 -> V4 delta lives at three *internal wrapper inputs*.
A final returned action is downstream of those wrappers and can therefore erase
exactly the suffix rows that would have engaged the older full-queue logic.
Consequently final-action scans are useful positive steering evidence only: a
zero final-action scan must never authorize a COLD verdict.
"""
from __future__ import annotations

from typing import Any, Mapping

STAGES = ("seed", "operating_stock", "redundant_hire")
FINAL_ACTION_SURFACE = "final_returned_action"
WRAPPER_INPUT_SURFACE = "exact_wrapper_input"


def _is_order(row: Any, *head: str) -> bool:
    return isinstance(row, list) and len(row) >= len(head) and tuple(row[: len(head)]) == head


def _market_parts(action: Mapping[str, Any], cfg: Mapping[str, Any]):
    market = action.get("market")
    if not isinstance(market, list):
        return None, None, None, "market_not_list"
    try:
        cap = max(1, int(cfg.get("maxMarketOrdersPerTurn", 10)))
    except (TypeError, ValueError, OverflowError):
        return None, None, None, "invalid_market_cap"
    return market, market[:cap], market[cap:], None


def classify_wrapper_input(
    stage: str, action: Mapping[str, Any], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    """Classify the exact action entering one submitted-V4 wrapper.

    This is the correct structural surface for the V3.1/V4 prefix delta.  The
    caller is responsible for proving that ``action`` is the input to the named
    wrapper; this function deliberately does not infer that provenance from a
    final returned action.
    """
    if stage not in STAGES:
        raise ValueError(f"unknown runtime-prefix stage: {stage}")
    market, prefix, suffix, error = _market_parts(action, cfg)
    if error is not None:
        return {
            "stage": stage,
            "surface": WRAPPER_INPUT_SURFACE,
            "candidate": False,
            "reason": error,
            "authorizes_global_cold": False,
        }

    assert market is not None and prefix is not None and suffix is not None
    nonempty_suffix = any(bool(row) for row in suffix)
    report: dict[str, Any] = {
        "stage": stage,
        "surface": WRAPPER_INPUT_SURFACE,
        "candidate": False,
        "reason": "no_scope_or_gate_delta",
        "cap": len(prefix) if len(market) >= len(prefix) else len(market),
        "market_rows": len(market),
        "suffix_rows": len(suffix),
        "nonempty_suffix": nonempty_suffix,
        # One callback can prove engagement, but absence on one callback never
        # proves the family globally cold.
        "authorizes_global_cold": False,
    }

    if stage == "seed":
        old_gate = any(_is_order(row, "BUY_SEED") for row in market)
        new_gate = any(_is_order(row, "BUY_SEED") for row in prefix)
        report.update(
            gate_delta=old_gate != new_gate,
            scope_candidate=bool(new_gate and nonempty_suffix),
        )
    elif stage == "operating_stock":
        old_gate = any(_is_order(row, "SELL", "FERTILIZER") for row in market)
        new_gate = any(_is_order(row, "SELL", "FERTILIZER") for row in prefix)
        report.update(
            gate_delta=old_gate != new_gate,
            scope_candidate=bool(new_gate and nonempty_suffix),
        )
    else:
        old_gate = any(_is_order(row, "HIRE") for row in market)
        new_gate = any(_is_order(row, "HIRE") for row in prefix)
        report.update(gate_delta=old_gate != new_gate, scope_candidate=False)

    report["candidate"] = bool(report["gate_delta"] or report["scope_candidate"])
    if report["candidate"]:
        report["reason"] = "wrapper_scope_or_gate_diff"
    return report


def classify_final_action_hint(
    action: Mapping[str, Any], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    """Positive-only steering hint from a final returned action.

    The same structural predicates are evaluated for convenience, but the
    provenance is explicitly non-authoritative for COLD because the action is
    downstream of the wrappers under test.
    """
    stage_reports = [classify_wrapper_input(stage, action, cfg) for stage in STAGES]
    candidate = any(report["candidate"] for report in stage_reports)
    return {
        "surface": FINAL_ACTION_SURFACE,
        "candidate": candidate,
        "verdict": "POSSIBLE_ENGAGEMENT" if candidate else "NO_FINAL_ACTION_WITNESS",
        "authorizes_global_cold": False,
        "stages": stage_reports,
    }


def final_action_census(reports: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate final-action hints without ever upgrading absence to COLD."""
    candidates = sum(bool(report.get("candidate")) for report in reports)
    return {
        "surface": FINAL_ACTION_SURFACE,
        "callbacks": len(reports),
        "candidate_callbacks": candidates,
        "verdict": "POSSIBLE_ENGAGEMENT" if candidates else "INCONCLUSIVE_NO_FINAL_ACTION_WITNESS",
        "authorizes_global_cold": False,
    }
