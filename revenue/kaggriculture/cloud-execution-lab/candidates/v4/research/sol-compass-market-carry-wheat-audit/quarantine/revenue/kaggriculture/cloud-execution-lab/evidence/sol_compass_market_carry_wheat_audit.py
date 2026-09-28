#!/usr/bin/env python3
"""Exact-head WHEAT feasibility and parent-liquidation audit for TITAN market carry.

This script is evidence-only. It does not modify policy state, canonical pointers,
archives, configuration, or provider state.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any

SOURCE_HEAD = "b6b080a6842107f7e9086f64cb0b2b9c38377696"
EXPECTED_BLOBS = {
    "candidate": "e1634810bd980e3dd850a5451e792ff20d1123af",
    "parent": "bdb9cf58148a3c7961c085f4902759537decabf6",
    "engine": "3c202c7ee921da239356789e266b694635103fc4",
    "mechanics": "044a4f9c0a4a44dde10ada57563238bcaf82075d",
    "frozen": "fc7baf5c179818a55037f6a61d92984d81d1a21c",
    "runtime": "ee2714e5702b219717ddd75122672a6d621fb268",
    "config": "3a3bef83899d3010fad623b628d9e95d9978111b",
}
PATHS = {
    "candidate": "candidates/v3-market-carry/market_carry.py",
    "parent": "reference/next-panel/vendor/arlene.py",
    "engine": "reference/engine/kaggriculture.py",
    "mechanics": "mechanics.py",
    "frozen": "frozen_selected.py",
    "runtime": "titan_runtime.py",
    "config": "TITAN-CONFIG.json",
}


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def git_blob(root: Path, ref: str, path: str) -> str:
    import subprocess
    return subprocess.check_output(
        ["git", "rev-parse", f"{ref}:revenue/kaggriculture/cloud-execution-lab/{path}"],
        cwd=root.parents[2],
        text=True,
    ).strip()


def intervals(values: list[int]) -> list[list[int]]:
    if not values:
        return []
    values = sorted(set(values))
    out: list[list[int]] = []
    start = prior = values[0]
    for value in values[1:]:
        if value == prior + 1:
            prior = value
            continue
        out.append([start, prior])
        start = prior = value
    out.append([start, prior])
    return out


def minimum_cash_for_cost(cost: int, reserve: int, fraction_bps: int) -> int:
    # Need both cash-reserve >= cost and floor(cash*fraction_bps/10000) >= cost.
    by_reserve = reserve + cost
    by_fraction = math.ceil(cost * 10_000 / fraction_bps)
    while by_fraction * fraction_bps // 10_000 < cost:
        by_fraction += 1
    return max(by_reserve, by_fraction)


def synthetic_observation(parent: Any, step: int, wheat: int) -> dict[str, Any]:
    products = tuple(parent.PRODUCTS)
    shed = {item: 0 for item in products}
    shed["WHEAT"] = wheat
    farm = {
        "money": 100_000,
        "farmer": [0, 0],
        "hands": [],
        "tiles": [[None for _ in range(parent.BOARD)] for _ in range(parent.BOARD)],
        "hires_today": 0,
        "unlocked_quadrants": ["NW"],
    }
    rival = {
        "money": 100_000,
        "farmer": [0, 0],
        "hands": [],
        "tiles": [[None for _ in range(parent.BOARD)] for _ in range(parent.BOARD)],
        "hires_today": 0,
        "unlocked_quadrants": ["SE"],
    }
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": 0,
        "farms": [farm, rival],
        "private": {
            "seeds": {item: 0 for item in products},
            "inventories": [{}],
            "shed": shed,
        },
        "market": {
            "prices": {item: 25 for item in products},
            "inventory": {item: 10_000 for item in products},
        },
        "town": {"unlocked_shops": []},
    }


def emitted_wheat(action: dict[str, Any], cap: int = 10) -> int:
    return sum(
        max(0, int(order[2]))
        for order in (action.get("market") or [])[:cap]
        if isinstance(order, list)
        and len(order) > 2
        and order[:2] == ["SELL", "WHEAT"]
    )


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    repo = root.parents[2]
    sys.path.insert(0, str(root))

    actual_blobs = {name: git_blob(root, "HEAD", path) for name, path in PATHS.items()}
    source_blobs = {name: git_blob(root, SOURCE_HEAD, path) for name, path in PATHS.items()}
    if source_blobs != EXPECTED_BLOBS:
        raise AssertionError({"reason": "source_head_blob_drift", "actual": source_blobs})
    if actual_blobs != EXPECTED_BLOBS:
        raise AssertionError({"reason": "worktree_source_drift", "actual": actual_blobs})

    mechanics = load_module("_sol_compass_mechanics", root / PATHS["mechanics"])
    parent = load_module("_sol_compass_parent", root / PATHS["parent"])
    carry_module = load_module("_sol_compass_market_carry", root / PATHS["candidate"])
    carry = carry_module.MarketCarry(mechanics)

    engine_text = (root / PATHS["engine"]).read_text(encoding="utf-8")
    candidate_text = (root / PATHS["candidate"]).read_text(encoding="utf-8")
    frozen_text = (root / PATHS["frozen"]).read_text(encoding="utf-8")
    runtime_text = (root / PATHS["runtime"]).read_text(encoding="utf-8")
    if 'item in ("WHEAT", "FERTILIZER")' not in engine_text:
        raise AssertionError("official BUY_PRODUCT domain changed")
    if 'item == NON_CARRY_ITEM or item in same_turn_sells' not in candidate_text:
        raise AssertionError("candidate product filter changed")
    if "p not in ('WHEAT','FERTILIZER')" not in frozen_text:
        raise AssertionError("frozen seller product universe changed")
    if "returned = self._feed_stock_selected" not in runtime_text:
        raise AssertionError("feed-stock finalizer ordering changed")

    params = mechanics.MARKET_PARAMS
    wheat_params = params["WHEAT"]
    equilibrium = int(wheat_params["I0"])
    scan_low = max(0, equilibrium - 2_000)
    scan_high = equilibrium + 2_000
    price_low = scan_low - carry.max_units - carry.rival_buy_stress - 16
    price_high = scan_high + carry.max_units + 16
    price = {
        inventory: int(mechanics.market_price("WHEAT", inventory, params))
        for inventory in range(price_low, price_high + 1)
    }
    prefix = [0]
    for inventory in range(price_low, price_high + 1):
        prefix.append(prefix[-1] + price[inventory])

    def price_sum(first: int, last_exclusive: int) -> int:
        if first >= last_exclusive:
            return 0
        return prefix[last_exclusive - price_low] - prefix[first - price_low]

    def metrics(inventory: int, demand: int, stress: int, quantity: int) -> dict[str, int]:
        # Exact loops from MarketCarry, collapsed to sums after verifying every
        # sale quote in this scan is above the engine's <=1 stop condition.
        cost_a = price_sum(inventory - quantity, inventory)
        after_buy_a = inventory - quantity
        sale_a_first = after_buy_a + stress - demand
        sale_a = price_sum(sale_a_first, sale_a_first + quantity)

        stressed_inventory = inventory - carry.rival_buy_stress
        cost_b = price_sum(stressed_inventory - quantity, stressed_inventory)
        after_buy_b = stressed_inventory - quantity
        sale_b_first = after_buy_b - demand
        sale_b = price_sum(sale_b_first, sale_b_first + quantity)
        if min(price[i] for i in range(sale_a_first, sale_a_first + quantity)) <= 1:
            raise AssertionError("sale A stop condition entered scanned band")
        if min(price[i] for i in range(sale_b_first, sale_b_first + quantity)) <= 1:
            raise AssertionError("sale B stop condition entered scanned band")

        worst_cost = max(cost_a, cost_b)
        worst_receipt = min(sale_a, sale_b)
        profit = worst_receipt - worst_cost
        roi_bps = profit * 10_000 // max(1, worst_cost)
        return {
            "worst_cost": worst_cost,
            "worst_receipt": worst_receipt,
            "profit": profit,
            "roi_bps": roi_bps,
        }

    wheat_shop_rates = {
        shop: (2 if len(tuple(products)) == 1 else 1)
        for shop, products in mechanics.SHOPS.items()
        if "WHEAT" in tuple(products)
    }
    max_shop_instances = int(mechanics.MAX_SHOP_INSTANCES)
    max_shop_demand = max_shop_instances * max(wheat_shop_rates.values())
    max_demand = max_shop_demand + 1  # town center on a coincident interval

    feasibility: list[dict[str, Any]] = []
    for stress in range(1, max_demand + 1):
        for demand in range(1, max_demand + 1):
            qualifying_inventories: list[int] = []
            best: tuple[tuple[int, int, int, int], dict[str, int]] | None = None
            for inventory in range(scan_low, scan_high + 1):
                for quantity in range(1, carry.max_units + 1):
                    row = metrics(inventory, demand, stress, quantity)
                    qualifies = (
                        row["profit"] >= carry.min_profit
                        and row["profit"] >= carry.min_profit_per_unit * quantity
                        and row["roi_bps"] >= carry.min_roi_bps
                    )
                    if not qualifies:
                        continue
                    qualifying_inventories.append(inventory)
                    key = (
                        row["profit"],
                        row["roi_bps"],
                        quantity,
                        -row["worst_cost"],
                    )
                    if best is None or key > best[0]:
                        best = (
                            key,
                            {
                                "inventory": inventory,
                                "quantity": quantity,
                                **row,
                                "minimum_cash": minimum_cash_for_cost(
                                    row["worst_cost"],
                                    carry.min_cash_reserve,
                                    carry.cash_fraction_bps,
                                ),
                            },
                        )
            if qualifying_inventories:
                feasibility.append(
                    {
                        "rival_supply_stress": stress,
                        "visible_rival_supply": max(0, stress - carry.unseen_rival_supply),
                        "demand": demand,
                        "inventory_intervals": intervals(qualifying_inventories),
                        "best": best[1] if best is not None else None,
                    }
                )

    routes = parent.routes()
    candidate_steps = [
        step
        for step in range(carry.min_day * 24, (720 - 2) - carry.terminal_buffer_steps + 1)
        if step % 4 == 0
    ]
    quantities = [10, 11, 12]
    liquidation_rows: list[dict[str, Any]] = []
    for route_id, route in sorted(routes.items()):
        for entry_step in candidate_steps:
            for quantity in quantities:
                agent = parent.Agent()
                agent.R = routes
                agent.cur = route_id
                remaining = quantity
                sales: list[dict[str, int]] = []
                for step in range(entry_step + 1, min(entry_step + carry.active_max_age, 718) + 1):
                    observation = synthetic_observation(parent, step, remaining)
                    action = agent.act(observation)
                    offered = emitted_wheat(action, parent.MAX_ORDERS)
                    sold = min(remaining, offered)
                    sales.append({"step": step, "offered": offered, "sold": sold})
                    remaining -= sold
                    if remaining == 0:
                        break
                liquidation_rows.append(
                    {
                        "route": route_id,
                        "entry_step": entry_step,
                        "quantity": quantity,
                        "sold_next_observation": sales[0]["sold"] if sales else 0,
                        "fully_sold_next_observation": bool(sales and sales[0]["sold"] == quantity),
                        "fully_sold_within_active_age": remaining == 0,
                        "clear_step": sales[-1]["step"] if remaining == 0 and sales else None,
                        "residual_at_cooldown": remaining,
                        "sales": sales,
                    }
                )

    by_quantity: dict[str, Any] = {}
    for quantity in quantities:
        rows = [row for row in liquidation_rows if row["quantity"] == quantity]
        total = len(rows)
        residuals = [row["residual_at_cooldown"] for row in rows]
        delays = [
            row["clear_step"] - row["entry_step"]
            for row in rows
            if row["clear_step"] is not None
        ]
        by_quantity[str(quantity)] = {
            "cases": total,
            "full_next_observation": sum(row["fully_sold_next_observation"] for row in rows),
            "full_within_active_age": sum(row["fully_sold_within_active_age"] for row in rows),
            "not_full_by_cooldown": sum(not row["fully_sold_within_active_age"] for row in rows),
            "worst_residual_at_cooldown": max(residuals, default=0),
            "max_clear_delay_when_cleared": max(delays, default=None),
        }

    counterexamples = [
        row
        for row in liquidation_rows
        if row["quantity"] == 12 and not row["fully_sold_next_observation"]
    ][:20]
    cooldown_failures = [
        row
        for row in liquidation_rows
        if row["quantity"] == 12 and not row["fully_sold_within_active_age"]
    ][:20]

    # A parent-only synthetic result is an optimistic upper bound for final TITAN:
    # FrozenSelected deliberately excludes WHEAT, market pressure/early capital
    # preserve quantities, and protect_feed_stock may withhold up to two units.
    if not counterexamples:
        raise AssertionError("expected at least one route/step without immediate liquidation")

    report = {
        "schema_version": 1,
        "source_head": SOURCE_HEAD,
        "source_blobs": source_blobs,
        "audit_source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "legal_buy_product_domain": ["WHEAT", "FERTILIZER"],
        "candidate_excludes": "FERTILIZER",
        "candidate_legal_carry_universe": ["WHEAT"],
        "wheat_shop_rates": wheat_shop_rates,
        "max_shop_instances": max_shop_instances,
        "max_wheat_demand": max_demand,
        "scan": {
            "inventory_low": scan_low,
            "inventory_high": scan_high,
            "thresholds": {
                "max_units": carry.max_units,
                "cash_fraction_bps": carry.cash_fraction_bps,
                "min_cash_reserve": carry.min_cash_reserve,
                "min_profit": carry.min_profit,
                "min_profit_per_unit": carry.min_profit_per_unit,
                "min_roi_bps": carry.min_roi_bps,
                "unseen_rival_supply": carry.unseen_rival_supply,
                "rival_buy_stress": carry.rival_buy_stress,
            },
            "feasible_rows": feasibility,
        },
        "route_liquidation": {
            "interpretation": (
                "Parent Arlene output with only the purchased WHEAT in shed; "
                "this is an optimistic quantity upper bound before TITAN's feed-stock guard."
            ),
            "entry_steps": {
                "count": len(candidate_steps),
                "first": min(candidate_steps),
                "last": max(candidate_steps),
            },
            "route_ids": sorted(routes),
            "by_quantity": by_quantity,
            "q12_non_immediate_examples": counterexamples,
            "q12_cooldown_failure_examples": cooldown_failures,
        },
        "disposition": {
            "engine_legal": True,
            "universally_feasible": False,
            "immediate_liquidation_guaranteed": False,
            "promotion_ready": False,
            "required_repair": [
                "restrict BUY_PRODUCT acquisition to the engine-legal domain",
                "bind admission to realized executable WHEAT fills",
                "price the actual planned liquidation step and retained quantity",
                "keep the active lot until observed WHEAT returns to baseline; do not clear residual stock by age alone",
            ],
        },
    }

    out_json = Path("WHEAT-AUDIT.json")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    feasible_lines = []
    for row in feasibility:
        best = row["best"]
        feasible_lines.append(
            f"| {row['rival_supply_stress']} | {row['visible_rival_supply']} | "
            f"{row['demand']} | {row['inventory_intervals']} | "
            f"{best['quantity']} | {best['profit']} | {best['roi_bps']} | "
            f"{best['minimum_cash']} |"
        )
    summary_lines = [
        "# TITAN v3 market-carry WHEAT audit",
        "",
        f"- Source head: `{SOURCE_HEAD}`",
        "- Legal candidate universe after the engine domain and candidate exclusion: `WHEAT` only.",
        f"- Maximum deterministic WHEAT absorption: `{max_demand}`.",
        f"- Exact inventory scan: `{scan_low}..{scan_high}`.",
        "",
        "## Feasible gate bands",
        "",
        "| stress | visible rival | demand | inventory intervals | best q | best profit | best ROI bps | min cash |",
        "|---:|---:|---:|---|---:|---:|---:|---:|",
        *feasible_lines,
        "",
        "## Parent liquidation upper bound",
        "",
    ]
    for quantity in quantities:
        row = by_quantity[str(quantity)]
        summary_lines.append(
            f"- q={quantity}: {row['full_next_observation']}/{row['cases']} full next-observation; "
            f"{row['full_within_active_age']}/{row['cases']} full within age {carry.active_max_age}; "
            f"{row['not_full_by_cooldown']} retain stock when the overlay cooldown can clear."
        )
    summary_lines += [
        "",
        "This parent-only result is optimistic: FrozenSelected does not optimize WHEAT, "
        "and the enabled feed-stock guard may withhold up to two WHEAT units.",
        "",
        "## Disposition",
        "",
        "**HOLD.** Legal WHEAT opportunities exist only in narrow demand/inventory bands, "
        "while the candidate values an immediate full sale that the canonical seller does not guarantee. "
        "Admission must price the actual liquidation plan and reconcile residual inventory before promotion.",
        "",
    ]
    Path("WHEAT-AUDIT.md").write_text("\n".join(summary_lines), encoding="utf-8")
    print(Path("WHEAT-AUDIT.md").read_text(encoding="utf-8"))
    print("REPORT_SHA256", sha256(out_json.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
