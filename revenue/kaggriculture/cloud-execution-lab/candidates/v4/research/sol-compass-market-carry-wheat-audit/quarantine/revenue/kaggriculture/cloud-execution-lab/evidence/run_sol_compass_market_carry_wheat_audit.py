#!/usr/bin/env python3
"""Binding-corrected runner for the SOL-COMPASS WHEAT carry audit.

The original audit engine is retained byte-for-byte. This runner corrects source
labels before execution: the SELL product universe is defined by scheduler.py,
and MAX_SHOP_INSTANCES is defined only by the pinned official engine. Every
source remains independently pinned in the final report.
"""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import sys

SCHEDULER_BLOB = "a483b24dd72b580d7d8811636b54d2d44f391575"
FROZEN_SELECTED_BLOB = "fc7baf5c179818a55037f6a61d92984d81d1a21c"


def load_legacy(path: Path):
    spec = importlib.util.spec_from_file_location("_sol_compass_wheat_audit_engine", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def add_hidden_rival_wheat_stress(report: dict) -> None:
    """Stress each admitted best lot against the rival's unobserved shed stock.

    This is deliberately favorable to the candidate: acquisition has no rival
    BUY pressure and liquidation is immediate after same-tick rival supply and
    town demand. Any loss here survives seller-latency uncertainty.
    """
    mechanics = sys.modules["_sol_compass_mechanics"]
    carry_module = sys.modules["_sol_compass_market_carry"]
    carry = carry_module.MarketCarry(mechanics)
    params = mechanics.MARKET_PARAMS
    rows = []
    for feasible in report["scan"]["feasible_rows"]:
        best = feasible["best"]
        inventory = int(best["inventory"])
        quantity = int(best["quantity"])
        demand = int(feasible["demand"])
        modeled_supply = int(feasible["rival_supply_stress"])
        acquisition_cost, after_buy = carry.buy_cost(
            "WHEAT", inventory, quantity, params
        )
        profile = []
        first_below_min_profit = None
        first_negative = None
        for actual_supply in range(0, 101):
            receipt, _ = carry.sale_receipt(
                "WHEAT",
                after_buy + actual_supply - demand,
                quantity,
                params,
            )
            profit = int(receipt) - int(acquisition_cost)
            profile.append(
                {
                    "actual_same_tick_rival_supply": actual_supply,
                    "receipt": int(receipt),
                    "profit": profit,
                }
            )
            if first_below_min_profit is None and profit < carry.min_profit:
                first_below_min_profit = actual_supply
            if first_negative is None and profit < 0:
                first_negative = actual_supply
        rows.append(
            {
                "modeled_supply_stress": modeled_supply,
                "visible_rival_supply": int(feasible["visible_rival_supply"]),
                "demand": demand,
                "inventory": inventory,
                "quantity": quantity,
                "candidate_worst_profit": int(best["worst_profit"]),
                "favorable_acquisition_cost": int(acquisition_cost),
                "profit_at_modeled_supply": profile[modeled_supply]["profit"],
                "first_actual_supply_below_min_profit": first_below_min_profit,
                "first_actual_supply_negative": first_negative,
                "profit_at_rival_shed_cap": profile[100]["profit"],
                "selected_profile": [
                    profile[index]
                    for index in (0, modeled_supply, 4, 8, 12, 25, 50, 100)
                    if 0 <= index < len(profile)
                ],
            }
        )
    negative_thresholds = [
        row["first_actual_supply_negative"]
        for row in rows
        if row["first_actual_supply_negative"] is not None
    ]
    report["hidden_rival_wheat_stress"] = {
        "interpretation": (
            "Immediate-liquidation upper bound with no rival BUY pressure. "
            "Actual rival WHEAT shed stock is private and may contribute up to "
            "the shed capacity; the candidate models only unseen_rival_supply=1."
        ),
        "max_actual_supply": 100,
        "negative_threshold_min": min(negative_thresholds, default=None),
        "negative_threshold_max": max(negative_thresholds, default=None),
        "rows": rows,
    }
    report["disposition"]["required_repair"].append(
        "account for unobserved rival WHEAT shed supply or admit only after realized post-market evidence"
    )


def main() -> int:
    here = Path(__file__).resolve().parent
    root = here.parent
    legacy_path = here / "sol_compass_market_carry_wheat_audit.py"
    legacy = load_legacy(legacy_path)

    # Preserve a separately named pin for the imported FrozenSelected consumer.
    legacy.PATHS["frozen_selected"] = legacy.PATHS["frozen"]
    legacy.EXPECTED_BLOBS["frozen_selected"] = FROZEN_SELECTED_BLOB

    # The static product-universe assertion belongs to scheduler.py. Repoint
    # only that preflight label; the calculation and parent-route audit remain
    # the original exact bytes.
    legacy.PATHS["frozen"] = "scheduler.py"
    legacy.EXPECTED_BLOBS["frozen"] = SCHEDULER_BLOB

    # mechanics.py intentionally extracts deterministic primitives but omits
    # MAX_SHOP_INSTANCES. Derive that audit bound from the already pinned
    # official engine source at load time; reject absent or ambiguous values.
    original_module_loader = legacy.load_module

    def load_with_engine_bound(name, path):
        module = original_module_loader(name, path)
        if name == "_sol_compass_mechanics":
            engine_text = (root / "reference/engine/kaggriculture.py").read_text(
                encoding="utf-8"
            )
            matches = re.findall(
                r"^MAX_SHOP_INSTANCES\s*=\s*([0-9]+)\s*$",
                engine_text,
                flags=re.MULTILINE,
            )
            if len(matches) != 1:
                raise AssertionError("ambiguous official MAX_SHOP_INSTANCES")
            module.MAX_SHOP_INSTANCES = int(matches[0])
        return module

    legacy.load_module = load_with_engine_bound

    # Complete the synthetic private schema used only for parent liquidation.
    # The legacy fixture already supplies every product and crop key. Official
    # private state also includes animal objects in shed; add zero-valued keys
    # so the optimistic parent probe cannot depend on a partial mapping.
    original_synthetic = legacy.synthetic_observation

    def complete_synthetic(parent, step, wheat):
        observation = original_synthetic(parent, step, wheat)
        for animal in parent.ANIMALS:
            observation["private"]["shed"].setdefault(animal, 0)
        return observation

    legacy.synthetic_observation = complete_synthetic

    result = int(legacy.main())

    report_path = Path("WHEAT-AUDIT.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    sources = dict(report["source_blobs"])
    scheduler = sources.pop("frozen")
    frozen_selected = sources.pop("frozen_selected")
    if scheduler != SCHEDULER_BLOB or frozen_selected != FROZEN_SELECTED_BLOB:
        raise AssertionError("binding correction did not preserve exact source blobs")
    sources["scheduler"] = scheduler
    sources["frozen_selected"] = frozen_selected
    report["source_blobs"] = sources
    report["audit_engine_source_sha256"] = report.pop("audit_source_sha256")
    report["audit_runner_source_sha256"] = sha256(Path(__file__).read_bytes()).hexdigest()
    report["binding_correction"] = {
        "reason": "SELL universe comes from scheduler.py; shop cap comes from official engine",
        "scheduler_blob": scheduler,
        "frozen_selected_blob": frozen_selected,
        "max_shop_instances_source": "reference/engine/kaggriculture.py",
        "max_shop_instances": int(sys.modules["_sol_compass_mechanics"].MAX_SHOP_INSTANCES),
        "calculation_engine_unchanged": True,
        "synthetic_private_schema_complete": True,
    }
    add_hidden_rival_wheat_stress(report)
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    hidden = report["hidden_rival_wheat_stress"]
    summary = Path("WHEAT-AUDIT.md")
    with summary.open("a", encoding="utf-8") as handle:
        handle.write(
            "\n## Source-binding correction\n\n"
            "The executable audit pins `scheduler.py` as the source of the "
            "WHEAT/FERTILIZER SELL exclusion, independently pins "
            "`frozen_selected.py` as its importing consumer, and parses "
            "`MAX_SHOP_INSTANCES` from the pinned official engine. The synthetic "
            "private state includes zero-valued official animal shed keys. No "
            "economic calculation or parent-route logic was changed.\n\n"
            "## Hidden rival WHEAT stress\n\n"
            "Even under immediate liquidation and no rival BUY pressure, the "
            f"best admitted bands become negative at actual same-tick rival supply "
            f"between `{hidden['negative_threshold_min']}` and "
            f"`{hidden['negative_threshold_max']}` units. The rival shed is private "
            "and may hold up to 100 total units; the candidate hard-codes one "
            "unseen rival unit. See `WHEAT-AUDIT.json` for every band.\n"
        )

    print("FINAL_REPORT_SHA256", sha256(report_path.read_bytes()).hexdigest())
    return result


if __name__ == "__main__":
    raise SystemExit(main())
