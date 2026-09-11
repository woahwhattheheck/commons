#!/usr/bin/env python3
"""Exact-engine contracts for pressure stock-baseline custody."""
from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))

# The pinned mechanics source imports only resolve_episode_seed from the
# package. Supply that exact import surface so this contract stays stdlib-only.
pkg = ModuleType("kaggle_environments")
pkg.__path__ = []  # type: ignore[attr-defined]
utils = ModuleType("kaggle_environments.utils")
utils.resolve_episode_seed = lambda _env: 0
sys.modules.setdefault("kaggle_environments", pkg)
sys.modules.setdefault("kaggle_environments.utils", utils)

import pressure_delay_invariance as candidate  # noqa: E402


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


mechanics = _load_module(
    "_titan_pressure_stock_baseline_mechanics",
    ROOT
    / "revenue/kaggriculture/cloud-execution-lab/reference/engine/kaggriculture.py",
)


def _sell(product: str, quantity: int, tag: str) -> dict[str, object]:
    return {
        "action": "SELL",
        "type": product,
        "quantity": quantity,
        "tag": tag,
    }


def _inventory(wheat: int) -> dict[str, int]:
    return {
        product: wheat if product == "WHEAT" else mechanics.MARKET_I0
        for product in candidate.PRODUCTS
    }


def _stock(orders: Sequence[Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    for order in orders:
        if (
            isinstance(order, list)
            and len(order) == 3
            and order[0] == "SELL"
            and order[1] in mechanics.PRODUCTS
            and isinstance(order[2], int)
            and not isinstance(order[2], bool)
            and order[2] > 0
        ):
            result[order[1]] = result.get(order[1], 0) + order[2]
    return result


def _run_exact_market(
    own_orders: Sequence[Any],
    rival_orders: Sequence[Any],
    *,
    inventory_overrides: Mapping[str, int],
    own_money: int,
) -> tuple[int, int]:
    inventory = dict.fromkeys(mechanics.PRODUCTS, mechanics.MARKET_I0)
    inventory.update(inventory_overrides)
    market = {
        "inventory": inventory,
        "prices": {
            item: mechanics.market_price(item, stock)
            for item, stock in inventory.items()
        },
    }
    farms = [{"money": own_money}, {"money": 0}]
    privates = [{"shed": _stock(own_orders)}, {"shed": _stock(rival_orders)}]
    states = [
        SimpleNamespace(
            observation=SimpleNamespace(
                market=market,
                farms=farms,
                private=privates[0],
            ),
            action={"market": copy.deepcopy(list(own_orders))},
        ),
        SimpleNamespace(
            observation=SimpleNamespace(
                market=market,
                farms=farms,
                private=privates[1],
            ),
            action={"market": copy.deepcopy(list(rival_orders))},
        ),
    ]
    env = SimpleNamespace(
        configuration={
            "boardSize": 10,
            "maxMarketOrdersPerTurn": 10,
            "farmHandCostMult": 1,
            "shedCapacity": 100,
        }
    )
    mechanics._process_market(states, env)
    return int(farms[0]["money"]), int(farms[1]["money"])


def _partition(public: int, bought: int, rival: int):
    buy = {
        "action": "BUY_PRODUCT",
        "type": "WHEAT",
        "quantity": bought,
        "tag": "stock-changing-barrier",
    }
    target = _sell("WHEAT", 1, "demoted-target")
    pressure = _sell("MILK", 1, "promoted-pressure")
    result = candidate.certified_pressure_partition(
        [buy, target, pressure],
        pressure_by_product={"WHEAT": 0, "MILK": 1},
        inventory=_inventory(public),
        max_rival_units=rival,
        price_by_stock=lambda product, stock: mechanics.market_price(product, stock),
    )
    return buy, target, pressure, result


class StockBaselineContracts(unittest.TestCase):
    def test_prior_product_buy_blocks_false_plateau_reorder(self) -> None:
        buy, target, pressure, result = _partition(9900, 11, 1)

        # Public q(9900)==q(9901)==35, but an executable 11-unit buy can
        # rebase the target to q(9889)=36 and q(9890)=35. Without exact prefix
        # execution, the target stock is unknown and must be a hard barrier.
        self.assertEqual(result.actions, (buy, target, pressure))
        self.assertFalse(result.changed)
        self.assertEqual(result.decisions[1].kind, "barrier")
        certificate = result.decisions[1].certificate
        self.assertIsNotNone(certificate)
        assert certificate is not None
        self.assertEqual(certificate.reason, "invalid_bound_or_inventory")
        self.assertIsNone(certificate.stock)

        parent = [
            ["BUY_PRODUCT", "WHEAT", 11],
            ["SELL", "WHEAT", 1],
            ["SELL", "MILK", 1],
        ]
        unsafe = [
            ["BUY_PRODUCT", "WHEAT", 11],
            ["SELL", "MILK", 1],
            ["SELL", "WHEAT", 1],
        ]
        rival_orders = [[], ["SELL", "WHEAT", 1], []]
        parent_cash = _run_exact_market(
            parent,
            rival_orders,
            inventory_overrides={"WHEAT": 9900},
            own_money=100000,
        )
        unsafe_cash = _run_exact_market(
            unsafe,
            rival_orders,
            inventory_overrides={"WHEAT": 9900},
            own_money=100000,
        )
        self.assertEqual(parent_cash, (99810, 36))
        self.assertEqual(unsafe_cash, (99809, 36))
        self.assertEqual(unsafe_cash[0] - parent_cash[0], -1)
        self.assertEqual(
            (unsafe_cash[0] - unsafe_cash[1])
            - (parent_cash[0] - parent_cash[1]),
            -1,
        )

    def test_stock_neutral_market_barrier_preserves_later_baseline(self) -> None:
        hire = {"action": "HIRE", "tag": "stock-neutral-barrier"}
        target = _sell("WHEAT", 1, "demoted-target")
        pressure = _sell("MILK", 1, "promoted-pressure")
        result = candidate.certified_pressure_partition(
            [hire, target, pressure],
            pressure_by_product={"WHEAT": 0, "MILK": 1},
            inventory=_inventory(9900),
            max_rival_units=1,
            price_by_stock=lambda _product, _stock: 7,
        )
        self.assertEqual(result.actions, (hire, pressure, target))
        self.assertTrue(result.changed)
        self.assertEqual(result.decisions[1].kind, "demotable")

    def test_opaque_barrier_poisons_every_later_product_baseline(self) -> None:
        opaque = object()
        target = _sell("WHEAT", 1, "demoted-target")
        pressure = _sell("MILK", 1, "promoted-pressure")
        result = candidate.certified_pressure_partition(
            [opaque, target, pressure],
            pressure_by_product={"WHEAT": 0, "MILK": 1},
            inventory=_inventory(9900),
            max_rival_units=1,
            price_by_stock=lambda _product, _stock: 7,
        )
        self.assertEqual(result.actions, (opaque, target, pressure))
        self.assertFalse(result.changed)
        self.assertEqual(result.decisions[1].kind, "barrier")
        certificate = result.decisions[1].certificate
        self.assertIsNotNone(certificate)
        assert certificate is not None
        self.assertIsNone(certificate.stock)

    def test_product_buy_splitter_blocks_later_same_product_reorder(self) -> None:
        # The predecessor used BUY_PRODUCT as a generic segment splitter while
        # keeping public inventory. That is the stale-baseline hole: WHEAT after
        # a WHEAT buy must not remain a known public stock.
        safe_a = _sell("TOMATO", 1, "safe-a")
        exposed_a = _sell("MILK", 1, "exposed-a")
        barrier = {
            "action": "BUY_PRODUCT",
            "type": "WHEAT",
            "quantity": 1,
            "tag": "buy-barrier",
        }
        safe_b = _sell("WHEAT", 1, "safe-b")
        exposed_b = _sell("EGG", 1, "exposed-b")
        result = candidate.certified_pressure_partition(
            [safe_a, exposed_a, barrier, safe_b, exposed_b],
            pressure_by_product={
                "TOMATO": 0,
                "MILK": 1,
                "WHEAT": 0,
                "EGG": 1,
            },
            inventory=_inventory(mechanics.MARKET_I0),
            max_rival_units=3,
            price_by_stock=lambda _product, _stock: 5,
        )
        self.assertEqual(
            result.actions,
            (exposed_a, safe_a, barrier, safe_b, exposed_b),
        )
        self.assertEqual(result.decisions[3].kind, "barrier")
        certificate = result.decisions[3].certificate
        self.assertIsNotNone(certificate)
        assert certificate is not None
        self.assertIsNone(certificate.stock)
        self.assertEqual(certificate.reason, "invalid_bound_or_inventory")

    def test_exact_curve_census_blocks_all_false_public_certificates(self) -> None:
        prices = {
            stock: mechanics.market_price("WHEAT", stock)
            for stock in range(9600, 10151)
        }
        false_cases = 0
        for public in range(9700, 10051):
            for bought in range(1, 101):
                actual = public - bought
                for rival in range(1, 101):
                    if prices[public] != prices[public + rival]:
                        continue
                    if prices[actual] == prices[actual + rival]:
                        continue
                    false_cases += 1
                    _buy, _target, _pressure, result = _partition(
                        public,
                        bought,
                        rival,
                    )
                    self.assertFalse(result.changed, (public, bought, rival))
                    self.assertEqual(result.decisions[1].kind, "barrier")
        self.assertEqual(false_cases, 169226)


if __name__ == "__main__":
    unittest.main(verbosity=2)
