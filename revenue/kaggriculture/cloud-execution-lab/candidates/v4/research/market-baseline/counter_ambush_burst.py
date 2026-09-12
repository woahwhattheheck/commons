#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""TITAN V4 COMEBACK: source-bound multi-callback Apex max-envelope economics.

Research only. This extends the canonical COMEBACK evidence package without
adding action-selection authority. The pinned Apex source authenticates a
conditional <=8 STRAWBERRY SELL rule at callbacks 499/500/501; it does *not*
authenticate that all three sells actually fire in a realized trajectory.

Accordingly this module evaluates the 8+8+8 sequence only as a deterministic
maximum-envelope stress case. Realized-event authority requires separate
state/replay evidence proving the source predicates and returned market rows.
"""
from __future__ import annotations

import hashlib
import json
import types
from pathlib import Path
from typing import Any, Iterable, Sequence

BASE_COUNTER_AMBUSH_BLOB = "041b47d3741bdb1f4bd676325fb9949c36ffe51e"
APEX_STRAWBERRY_MAX_ENVELOPE = ((499, 8), (500, 8), (501, 8))

ENGINE_REL = Path(
    "revenue/kaggriculture/cloud-execution-lab/reference/engine/kaggriculture.py"
)
APEX_REL = Path(
    "revenue/kaggriculture/cloud-frontier-policy/next-panel/vendor/apex/main.py"
)
REFERENCE_REL = Path(
    "revenue/kaggriculture/cloud-execution-lab/candidates/v4/"
    "research/reference-policy-bank/REFERENCE-POLICIES.json"
)


class BurstError(ValueError):
    pass


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def load_pinned_base(path: Path):
    data = path.read_bytes()
    actual = git_blob(data)
    if actual != BASE_COUNTER_AMBUSH_BLOB:
        raise BurstError(
            f"COMEBACK base drift: expected {BASE_COUNTER_AMBUSH_BLOB}, got {actual}"
        )
    module = types.ModuleType("titan_v4_comeback_pinned_base")
    module.__file__ = str(path)
    try:
        exec(compile(data, str(path), "exec"), module.__dict__)
    except Exception as exc:
        raise BurstError("cannot load pinned COMEBACK base") from exc

    required = (
        "sell_units",
        "town_drain",
        "predump_counterfactual",
        "APEX_ANTI_CLONE",
        "APEX_MAIN_SHA256",
        "verify_apex_source",
        "verify_engine",
    )
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        raise BurstError(f"pinned COMEBACK base contract missing: {missing}")

    source_events = [
        event
        for event in module.APEX_ANTI_CLONE.get("events", ())
        if event.get("item") == "STRAWBERRY"
        and tuple(event.get("steps", ())) == (499, 500, 501)
    ]
    if (
        len(source_events) != 1
        or source_events[0].get("min_shed") != 8
        or source_events[0].get("max_sell") != 8
    ):
        raise BurstError(
            "pinned COMEBACK base no longer authenticates the conditional "
            "Apex 499/500/501 STRAWBERRY <=8 source rule"
        )
    return module


def default_repo_root() -> Path:
    here = Path(__file__).resolve().parent
    return here.parents[6]


def verify_report_sources(base, repo_root: Path) -> dict[str, Any]:
    """Authenticate the actual Apex, reference manifest, and official engine."""
    try:
        root = repo_root.resolve(strict=True)
        apex = root / APEX_REL
        reference = root / REFERENCE_REL
        engine = root / ENGINE_REL
        apex_identity = base.verify_apex_source(apex, reference)
        engine_identity = base.verify_engine(engine)
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError) as exc:
        raise BurstError(f"COMEBACK provenance verification failed: {exc}") from exc
    return {
        "apex_and_reference": dict(apex_identity),
        "official_engine": dict(engine_identity),
    }


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise BurstError(f"{label} must be a positive integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BurstError(f"{label} must be a nonnegative integer")
    return value


def normalize_events(events: Sequence[Sequence[int]]) -> tuple[tuple[int, int], ...]:
    if isinstance(events, (str, bytes)) or not isinstance(events, Sequence) or not events:
        raise BurstError("nonempty event sequence required")
    out: list[tuple[int, int]] = []
    previous = -1
    for index, row in enumerate(events):
        if isinstance(row, (str, bytes)) or not isinstance(row, Sequence) or len(row) != 2:
            raise BurstError(f"event[{index}] must be [step, units]")
        step = _nonnegative_int(row[0], f"event[{index}].step")
        units = _positive_int(row[1], f"event[{index}].units")
        if step <= previous:
            raise BurstError("event steps must be strictly increasing")
        out.append((step, units))
        previous = step
    return tuple(out)


def _run_rival_path(
    base,
    *,
    item: str,
    inventory: int,
    events: tuple[tuple[int, int], ...],
    unlocked_shops: tuple[str, ...],
) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    for step, units in events:
        before = inventory
        sold = base.sell_units(item, inventory, units)
        drain = base.town_drain(item, step, unlocked_shops)
        inventory = max(0, sold["ending_inventory"] - drain)
        rows.append(
            {
                "step": step,
                "units": units,
                "starting_inventory": before,
                "rival_gross": sold["gross"],
                "ending_inventory_before_town": sold["ending_inventory"],
                "town_drain_after": drain,
                "ending_inventory": inventory,
            }
        )
    return rows, inventory


def envelope_counterfactual(
    base,
    *,
    item: str,
    starting_inventory: int,
    own_units: int,
    events: Sequence[Sequence[int]],
    pre_step: int,
    unlocked_shops: Iterable[str] = (),
) -> dict[str, Any]:
    """Stress-test a t-1 sale under a supplied hypothetical rival-fill envelope."""
    if not isinstance(item, str) or not item:
        raise BurstError("nonempty item required")
    inventory0 = _nonnegative_int(starting_inventory, "starting_inventory")
    own = _positive_int(own_units, "own_units")
    pre = _nonnegative_int(pre_step, "pre_step")
    normalized = normalize_events(events)
    if pre + 1 != normalized[0][0]:
        raise BurstError("pre_step must be exactly one callback before the first envelope event")
    shops = tuple(unlocked_shops)

    early = base.sell_units(item, inventory0, own)
    pre_drain = base.town_drain(item, pre, shops)
    early_start = max(0, early["ending_inventory"] - pre_drain)
    early_events, early_after = _run_rival_path(
        base,
        item=item,
        inventory=early_start,
        events=normalized,
        unlocked_shops=shops,
    )

    baseline_start = max(0, inventory0 - pre_drain)
    baseline_events, baseline_after = _run_rival_path(
        base,
        item=item,
        inventory=baseline_start,
        events=normalized,
        unlocked_shops=shops,
    )
    late = base.sell_units(item, baseline_after, own)

    event_rows: list[dict[str, Any]] = []
    cumulative_suppression = 0
    for early_row, baseline_row in zip(early_events, baseline_events):
        suppression = baseline_row["rival_gross"] - early_row["rival_gross"]
        cumulative_suppression += suppression
        event_rows.append(
            {
                "step": early_row["step"],
                "units": early_row["units"],
                "town_drain_after": early_row["town_drain_after"],
                "rival_gross_after_early_sale": early_row["rival_gross"],
                "rival_gross_without_early_sale": baseline_row["rival_gross"],
                "rival_suppression": suppression,
                "inventory_after_early_path": early_row["ending_inventory"],
                "inventory_after_baseline_path": baseline_row["ending_inventory"],
            }
        )

    own_gain = early["gross"] - late["gross"]
    return {
        "scenario_semantics": "conditional_max_envelope_not_observed_events",
        "item": item,
        "pre_step": pre,
        "post_envelope_sale_step": normalized[-1][0] + 1,
        "events": event_rows,
        "town_drain_after_pre": pre_drain,
        "own_early_gross": early["gross"],
        "own_post_envelope_gross": late["gross"],
        "own_timing_gain": own_gain,
        "cumulative_rival_suppression": cumulative_suppression,
        "gross_relative_margin_swing": own_gain + cumulative_suppression,
        "early_path_inventory_after_envelope": early_after,
        "baseline_inventory_before_late_sale": baseline_after,
        "late_path_inventory_after_own_sale": late["ending_inventory"],
        "realized_events_authenticated": False,
        "decision_authority": False,
        "result_authority": False,
    }


def authenticated_apex_envelope_report(
    base_path: Path, repo_root: Path | None = None
) -> dict[str, Any]:
    """Return verified source-rule custody plus a non-authoritative max scenario."""
    base = load_pinned_base(base_path)
    verified_sources = verify_report_sources(
        base, default_repo_root() if repo_root is None else repo_root
    )
    shops = (
        "BRUNCH_SPOT",
        "ICE_CREAM_SHOP",
        "SMOOTHIE_SHOP",
        "FARMERS_MARKET",
    ) * 2
    envelope = envelope_counterfactual(
        base,
        item="STRAWBERRY",
        starting_inventory=10000,
        own_units=8,
        events=APEX_STRAWBERRY_MAX_ENVELOPE,
        pre_step=498,
        unlocked_shops=shops,
    )
    first_only = base.predump_counterfactual(
        item="STRAWBERRY",
        starting_inventory=10000,
        own_units=8,
        rival_units=8,
        pre_step=498,
        unlocked_shops=shops,
    )
    isolated = first_only["gross_relative_margin_swing"]
    apex_identity = verified_sources["apex_and_reference"]
    return {
        "schema": "titan-v4-comeback-apex-max-envelope/v3",
        "base_counter_ambush_git_blob": BASE_COUNTER_AMBUSH_BLOB,
        "verified_sources": verified_sources,
        "apex_main_sha256": apex_identity["apex_main_sha256"],
        "source_rule_authenticated": True,
        "realized_events_authenticated": False,
        "source_rule": {
            "item": "STRAWBERRY",
            "steps": [499, 500, 501],
            "min_shed": 8,
            "max_sell_per_callback": 8,
            "semantics": "conditional_source_rule_not_realized_event",
        },
        "max_envelope_events": [list(row) for row in APEX_STRAWBERRY_MAX_ENVELOPE],
        "conditional_max_shop_drain_scenario": envelope,
        "max_envelope_isolated_first_event_swing": isolated,
        "max_envelope_naive_three_times_isolated_swing": isolated * 3,
        "max_envelope_minus_naive_isolated": (
            envelope["gross_relative_margin_swing"] - isolated * 3
        ),
        "required_realization_evidence": [
            "per-callback state/replay proving the conditional source branch fired",
            "returned market row after wrapper mutation/cap for each callback",
            "realized STRAWBERRY sell quantity/fill at each callback",
        ],
        "decision_authority": False,
        "result_authority": False,
        "activation_authority": False,
    }


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    print(
        json.dumps(
            authenticated_apex_envelope_report(here / "counter_ambush.py"),
            indent=2,
            sort_keys=True,
        )
    )
