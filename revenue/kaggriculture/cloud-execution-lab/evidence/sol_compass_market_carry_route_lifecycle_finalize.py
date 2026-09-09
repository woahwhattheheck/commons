#!/usr/bin/env python3
"""Observation-timed route liquidation finalizer for the WHEAT carry audit.

The market-carry overlay evaluates its active lot before the selected parent
market action executes. At age == active_max_age it erases attribution from the
pre-action observation, so a WHEAT sale emitted on that action cannot count as
observed liquidation. This finalizer replaces the legacy optimistic summary
with that exact observation boundary while preserving it for comparison.
"""
from __future__ import annotations

import ast
from collections import Counter
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

SOURCE_HEAD = "b6b080a6842107f7e9086f64cb0b2b9c38377696"
PARENT_BLOB = "bdb9cf58148a3c7961c085f4902759537decabf6"
CANDIDATE_BLOB = "e1634810bd980e3dd850a5451e792ff20d1123af"
PARENT_PATH = "reference/next-panel/vendor/arlene.py"
CANDIDATE_PATH = "candidates/v3-market-carry/market_carry.py"


def git_blob(root: Path, path: str) -> str:
    return subprocess.check_output(
        [
            "git",
            "rev-parse",
            f"HEAD:revenue/kaggriculture/cloud-execution-lab/{path}",
        ],
        cwd=root.parents[2],
        text=True,
    ).strip()


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def constructor_defaults(candidate_path: Path) -> dict[str, Any]:
    tree = ast.parse(candidate_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "MarketCarry":
            continue
        for child in node.body:
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if child.name != "__init__":
                continue
            names = [arg.arg for arg in child.args.args]
            defaults = child.args.defaults
            paired_names = names[len(names) - len(defaults) :]
            return {
                name: ast.literal_eval(default)
                for name, default in zip(paired_names, defaults)
            }
    raise AssertionError("MarketCarry.__init__ defaults not found")


def synthetic_observation(parent: Any, step: int, wheat: int) -> dict[str, Any]:
    products = tuple(parent.PRODUCTS)
    shed = {item: 0 for item in products}
    shed.update({animal: 0 for animal in parent.ANIMALS})
    seeds = {item: 0 for item in products}
    empty_tiles = [[None for _ in range(parent.BOARD)] for _ in range(parent.BOARD)]
    farm = {
        "money": 100_000,
        "farmer": [0, 0],
        "hands": [],
        "tiles": empty_tiles,
        "hires_today": 0,
        "unlocked_quadrants": ["NW", "NE", "SW", "SE"],
    }
    rival = {
        "money": 100_000,
        "farmer": [0, 0],
        "hands": [],
        "tiles": [[None for _ in range(parent.BOARD)] for _ in range(parent.BOARD)],
        "hires_today": 0,
        "unlocked_quadrants": ["NW", "NE", "SW", "SE"],
    }
    shed["WHEAT"] = int(wheat)
    return {
        "step": int(step),
        "day": int(step) // 24,
        "hour": int(step) % 24,
        "player": 0,
        "farms": [farm, rival],
        "private": {"seeds": seeds, "inventories": [{}], "shed": shed},
        "market": {
            "prices": {item: 25 for item in products},
            "inventory": {item: 10_000 for item in products},
        },
        "town": {"unlocked_shops": []},
    }


def emitted_wheat(action: Any, cap: int) -> int:
    if not isinstance(action, dict):
        return 0
    total = 0
    for order in list(action.get("market") or ())[: int(cap)]:
        if (
            isinstance(order, list)
            and len(order) > 2
            and order[0] == "SELL"
            and order[1] == "WHEAT"
        ):
            try:
                total += max(0, int(order[2]))
            except (TypeError, ValueError):
                continue
    return total


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    report_path = Path("WHEAT-AUDIT.json")
    markdown_path = Path("WHEAT-AUDIT.md")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("source_head") != SOURCE_HEAD:
        raise AssertionError("report source head drift")
    if git_blob(root, PARENT_PATH) != PARENT_BLOB:
        raise AssertionError("parent blob drift")
    if git_blob(root, CANDIDATE_PATH) != CANDIDATE_BLOB:
        raise AssertionError("candidate blob drift")

    defaults = constructor_defaults(root / CANDIDATE_PATH)
    min_day = int(defaults["min_day"])
    terminal_buffer = int(defaults["terminal_buffer_steps"])
    active_age = int(defaults["active_max_age"])
    max_units = int(defaults["max_units"])
    if active_age < 2:
        raise AssertionError("active age too short for observation-timed audit")

    parent = load_module("_sol_compass_lifecycle_parent", root / PARENT_PATH)
    routes = parent.routes()
    turns = int(parent.TURNS)
    entry_steps = [
        step
        for step in range(min_day * 24, (turns - 2) - terminal_buffer + 1)
        if step % 4 == 0
    ]
    quantities = sorted({max(1, max_units - 2), max(1, max_units - 1), max_units})

    cases: list[dict[str, Any]] = []
    for starting_route in sorted(routes):
        for entry_step in entry_steps:
            for quantity in quantities:
                agent = parent.Agent()
                agent.R = routes
                agent.cur = starting_route
                remaining = int(quantity)
                sales = []
                completed_action_age = None

                # Actions at ages 1..active_age-1 can be observed before the
                # overlay's age-based attribution erasure.
                for age in range(1, active_age):
                    step = entry_step + age
                    action = agent.act(synthetic_observation(parent, step, remaining))
                    offered = emitted_wheat(action, parent.MAX_ORDERS)
                    sold = min(remaining, offered)
                    remaining -= sold
                    sales.append(
                        {
                            "age": age,
                            "step": step,
                            "offered": offered,
                            "sold": sold,
                            "remaining_after_action": remaining,
                        }
                    )
                    if remaining == 0:
                        completed_action_age = age
                        break

                residual_at_clear_observation = remaining
                clear_step_offer = 0
                clear_step_sale = 0
                if residual_at_clear_observation > 0:
                    clear_step = entry_step + active_age
                    clear_action = agent.act(
                        synthetic_observation(
                            parent, clear_step, residual_at_clear_observation
                        )
                    )
                    clear_step_offer = emitted_wheat(clear_action, parent.MAX_ORDERS)
                    clear_step_sale = min(
                        residual_at_clear_observation, clear_step_offer
                    )
                    sales.append(
                        {
                            "age": active_age,
                            "step": clear_step,
                            "offered": clear_step_offer,
                            "sold": clear_step_sale,
                            "remaining_after_action": (
                                residual_at_clear_observation - clear_step_sale
                            ),
                            "not_observed_before_attribution_erasure": True,
                        }
                    )

                observed_clear_age = (
                    completed_action_age + 1
                    if completed_action_age is not None
                    else active_age
                )
                cases.append(
                    {
                        "starting_route": starting_route,
                        "entry_step": entry_step,
                        "quantity": quantity,
                        "full_on_first_parent_action": completed_action_age == 1,
                        "fully_liquidated_before_cooldown_observation": (
                            completed_action_age is not None
                        ),
                        "completion_action_age": completed_action_age,
                        "observed_clear_age": observed_clear_age,
                        "residual_at_cooldown_observation": (
                            residual_at_clear_observation
                        ),
                        "clear_step_parent_offer": clear_step_offer,
                        "clear_step_parent_sale": clear_step_sale,
                        "sales": sales,
                    }
                )

    by_quantity: dict[str, Any] = {}
    for quantity in quantities:
        rows = [row for row in cases if row["quantity"] == quantity]
        residual_rows = [
            row for row in rows if row["residual_at_cooldown_observation"] > 0
        ]
        completion_ages = [
            row["completion_action_age"]
            for row in rows
            if row["completion_action_age"] is not None
        ]
        by_quantity[str(quantity)] = {
            "cases": len(rows),
            "full_on_first_parent_action": sum(
                row["full_on_first_parent_action"] for row in rows
            ),
            "fully_observed_before_cooldown": sum(
                row["fully_liquidated_before_cooldown_observation"] for row in rows
            ),
            "residual_attribution_erased_at_cooldown": len(residual_rows),
            "worst_residual_at_cooldown": max(
                (
                    row["residual_at_cooldown_observation"]
                    for row in residual_rows
                ),
                default=0,
            ),
            "residual_cases_with_parent_sale_on_clear_action": sum(
                row["clear_step_parent_sale"] > 0 for row in residual_rows
            ),
            "residual_cases_without_parent_sale_on_clear_action": sum(
                row["clear_step_parent_sale"] == 0 for row in residual_rows
            ),
            "completion_action_age_histogram": dict(
                sorted(Counter(completion_ages).items())
            ),
            "residual_histogram": dict(
                sorted(
                    Counter(
                        row["residual_at_cooldown_observation"]
                        for row in residual_rows
                    ).items()
                )
            ),
        }

    by_starting_route: dict[str, Any] = {}
    for route in sorted(routes):
        rows = [row for row in cases if row["starting_route"] == route]
        by_starting_route[route] = {
            "cases": len(rows),
            "fully_observed_before_cooldown": sum(
                row["fully_liquidated_before_cooldown_observation"] for row in rows
            ),
            "residual_attribution_erased_at_cooldown": sum(
                row["residual_at_cooldown_observation"] > 0 for row in rows
            ),
        }

    residual_examples = [
        row for row in cases if row["residual_at_cooldown_observation"] > 0
    ][:30]
    safe_examples = [
        row
        for row in cases
        if row["fully_liquidated_before_cooldown_observation"]
        and not row["full_on_first_parent_action"]
    ][:20]

    legacy_summary = report.pop("route_liquidation", None)
    report["route_liquidation_legacy_optimistic"] = legacy_summary
    report["route_liquidation"] = {
        "semantics": (
            "The overlay checks pre-action observed shed state. Parent sales at "
            "ages 1..active_max_age-1 can be observed before age erasure; an "
            "age-active_max_age sale cannot."
        ),
        "source_head": SOURCE_HEAD,
        "parent_blob": PARENT_BLOB,
        "candidate_blob": CANDIDATE_BLOB,
        "active_max_age": active_age,
        "entry_steps": {
            "count": len(entry_steps),
            "first": min(entry_steps),
            "last": max(entry_steps),
        },
        "starting_routes": sorted(routes),
        "quantities": quantities,
        "by_quantity": by_quantity,
        "by_starting_route": by_starting_route,
        "residual_examples": residual_examples,
        "delayed_but_observed_examples": safe_examples,
        "fixture_boundary": (
            "Neutral full-land public state with only candidate-added WHEAT in "
            "private shed. This remains favorable to liquidation and excludes "
            "the final TITAN feed-stock withholding layer."
        ),
        "audit_source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
    }

    total_residual = sum(
        row["residual_attribution_erased_at_cooldown"]
        for row in by_quantity.values()
    )
    if total_residual <= 0:
        raise AssertionError("expected at least one residual-attribution witness")
    repair = (
        "do not erase active-lot attribution before a liquidation action is "
        "observed in the next state; include shed and worker-held WHEAT"
    )
    if repair not in report["disposition"]["required_repair"]:
        report["disposition"]["required_repair"].append(repair)
    report["disposition"]["promotion_ready"] = False

    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with markdown_path.open("a", encoding="utf-8") as handle:
        handle.write(
            "\n## Observation-timed route lifecycle\n\n"
            f"The audit covered `{len(entry_steps)}` candidate entry steps, "
            f"`{len(routes)}` starting routes, and quantities "
            f"`{quantities}`. A parent sale emitted on age `{active_age}` is "
            "not counted as safe liquidation because the overlay erases active "
            "attribution from that step's pre-action observation.\n\n"
        )
        for quantity in quantities:
            row = by_quantity[str(quantity)]
            handle.write(
                f"- q={quantity}: `{row['fully_observed_before_cooldown']}`/"
                f"`{row['cases']}` fully observed before cooldown; "
                f"`{row['residual_attribution_erased_at_cooldown']}` erase "
                f"attribution with residual stock; worst residual "
                f"`{row['worst_residual_at_cooldown']}`.\n"
            )
        handle.write(
            "\nThis is still favorable to the candidate because the synthetic "
            "state contains no pre-existing stock pressure and does not apply "
            "TITAN's feed-stock withholding layer.\n"
        )

    print("OBSERVATION_TIMED_REPORT_SHA256", sha256(report_path.read_bytes()).hexdigest())
    print("RESIDUAL_ATTRIBUTION_CASES", total_residual)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
