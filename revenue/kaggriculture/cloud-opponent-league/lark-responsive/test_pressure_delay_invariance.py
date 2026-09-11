#!/usr/bin/env python3
"""Contracts for the bounded pressure-delay certificate carrier."""

from __future__ import annotations

import copy
import importlib.util
import itertools
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))

# Official interpreter blob 3c202c7e imports only resolve_episode_seed.
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
    "_titan_pressure_delay_mechanics",
    ROOT
    / "revenue/kaggriculture/cloud-execution-lab/reference/engine/kaggriculture.py",
)


def _inventory(value: int = 0) -> dict[str, int]:
    return {product: value for product in candidate.PRODUCTS}


def _sell(product: str, quantity: int, tag: str) -> dict[str, object]:
    return {
        "action": "SELL",
        "type": product,
        "quantity": quantity,
        "tag": tag,
    }


def _engine_order(row: Mapping[str, object]) -> list[object]:
    return ["SELL", row["type"], row["quantity"]]


def _run_exact_market(
    own_orders: Sequence[Any],
    rival_orders: Sequence[Any],
    *,
    inventory_overrides: Mapping[str, int],
    shed_capacity: int = 100,
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
    farms = [{"money": 0}, {"money": 0}]

    def stock(orders: Sequence[Any]) -> dict[str, int]:
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

    privates = [{"shed": stock(own_orders)}, {"shed": stock(rival_orders)}]
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
            "shedCapacity": shed_capacity,
        }
    )
    mechanics._process_market(states, env)
    return int(farms[0]["money"]), int(farms[1]["money"])


class DelayCertificateTests(unittest.TestCase):
    def test_exact_plateau_predecessor_is_blocked(self) -> None:
        tomato = _sell("TOMATO", 1, "tomato-parent")
        milk = _sell("MILK", 1, "milk-parent")
        actions = [tomato, milk]
        inventory = _inventory(mechanics.MARKET_I0)
        inventory.update({"TOMATO": 9999, "MILK": 9999})
        quote = lambda product, stock: mechanics.market_price(product, stock)

        result = candidate.certified_pressure_partition(
            actions,
            pressure_by_product={"TOMATO": 0, "MILK": 9},
            inventory=inventory,
            max_rival_units=100,
            price_by_stock=quote,
        )

        self.assertEqual(result.actions, (tomato, milk))
        self.assertFalse(result.changed)
        self.assertEqual(result.decisions[0].kind, "barrier")
        certificate = result.decisions[0].certificate
        self.assertIsNotNone(certificate)
        assert certificate is not None
        self.assertFalse(certificate.safe)
        self.assertEqual(certificate.reason, "receipt_changes_with_delay")

        parent = [_engine_order(tomato), _engine_order(milk)]
        unsafe_proxy = [_engine_order(milk), _engine_order(tomato)]
        rival = [["SELL", "TOMATO", 2], []]
        parent_cash = _run_exact_market(
            parent,
            rival,
            inventory_overrides={"TOMATO": 9999, "MILK": 9999},
        )
        unsafe_cash = _run_exact_market(
            unsafe_proxy,
            rival,
            inventory_overrides={"TOMATO": 9999, "MILK": 9999},
        )
        repaired_cash = _run_exact_market(
            [_engine_order(row) for row in result.actions],
            rival,
            inventory_overrides={"TOMATO": 9999, "MILK": 9999},
        )
        self.assertEqual(parent_cash, (229, 117))
        self.assertEqual(unsafe_cash, (226, 120))
        self.assertEqual(repaired_cash, parent_cash)
        self.assertEqual(unsafe_cash[0] - parent_cash[0], -3)
        self.assertEqual(
            (unsafe_cash[0] - unsafe_cash[1])
            - (parent_cash[0] - parent_cash[1]),
            -6,
        )

    def test_flat_quote_permits_stable_promotion(self) -> None:
        neutral = _sell("TOMATO", 2, "neutral")
        exposed = _sell("MILK", 1, "exposed")
        result = candidate.certified_pressure_partition(
            [neutral, exposed],
            pressure_by_product={"TOMATO": 0, "MILK": 4},
            inventory=_inventory(),
            max_rival_units=100,
            price_by_stock=lambda _product, _stock: 7,
        )
        self.assertEqual(result.actions, (exposed, neutral))
        self.assertTrue(result.changed)
        self.assertEqual(result.decisions[0].kind, "demotable")
        certificate = result.decisions[0].certificate
        self.assertIsNotNone(certificate)
        assert certificate is not None
        self.assertTrue(certificate.safe)
        self.assertEqual(certificate.baseline_receipt, 14)
        self.assertEqual(certificate.endpoint_receipt, 14)
        self.assertEqual(certificate.checked_quotes, 102)

    def test_declining_quote_is_a_hard_barrier(self) -> None:
        neutral = _sell("TOMATO", 1, "unsafe-neutral")
        exposed = _sell("MILK", 1, "exposed")
        result = candidate.certified_pressure_partition(
            [neutral, exposed],
            pressure_by_product={"TOMATO": 0, "MILK": 1},
            inventory=_inventory(),
            max_rival_units=3,
            price_by_stock=lambda _product, stock: max(1, 10 - stock),
        )
        self.assertEqual(result.actions, (neutral, exposed))
        self.assertFalse(result.changed)
        self.assertEqual(result.decisions[0].kind, "barrier")

    def test_nonmonotone_window_fails_even_when_endpoints_match(self) -> None:
        curve = (5, 4, 5)
        quote = lambda _product, stock: curve[stock]
        certificate = candidate.certify_delay_invariance(
            "TOMATO", 0, 1, 2, quote
        )
        self.assertFalse(certificate.safe)
        self.assertEqual(certificate.reason, "nonmonotone_quote_window")
        self.assertFalse(
            candidate.exhaustive_delay_invariant("TOMATO", 0, 1, 2, quote)
        )

    def test_endpoint_implementation_matches_exhaustive_monotone_oracle(self) -> None:
        cases = 0
        for curve in itertools.product(range(1, 5), repeat=7):
            if any(left < right for left, right in zip(curve, curve[1:])):
                continue
            quote = lambda _product, stock, values=curve: values[stock]
            for quantity in range(1, 4):
                for bound in range(0, len(curve) - quantity + 1):
                    certificate = candidate.certify_delay_invariance(
                        "TOMATO", 0, quantity, bound, quote
                    )
                    oracle = candidate.exhaustive_delay_invariant(
                        "TOMATO", 0, quantity, bound, quote
                    )
                    self.assertEqual(
                        certificate.safe,
                        oracle,
                        (curve, quantity, bound, certificate),
                    )
                    cases += 1
        self.assertEqual(cases, 2160)

    def test_malformed_inputs_and_quotes_fail_closed(self) -> None:
        neutral = _sell("TOMATO", 1, "neutral")
        exposed = _sell("MILK", 1, "exposed")
        actions = [neutral, exposed]
        common = {
            "actions": actions,
            "inventory": _inventory(),
            "price_by_stock": lambda _product, _stock: 9,
        }
        malformed_pressures = (
            {"TOMATO": True, "MILK": 1},
            {"TOMATO": float("nan"), "MILK": 1},
            {"TOMATO": float("inf"), "MILK": 1},
            {"MILK": 1},
        )
        for pressure in malformed_pressures:
            with self.subTest(pressure=pressure):
                result = candidate.certified_pressure_partition(
                    pressure_by_product=pressure,
                    max_rival_units=4,
                    **common,
                )
                self.assertEqual(result.actions, tuple(actions))
                self.assertFalse(result.changed)

        for bound in (True, -1, 1.5, {"MILK": 4}):
            with self.subTest(bound=bound):
                result = candidate.certified_pressure_partition(
                    pressure_by_product={"TOMATO": 0, "MILK": 1},
                    max_rival_units=bound,
                    **common,
                )
                self.assertEqual(result.actions, tuple(actions))
                self.assertFalse(result.changed)

        for bad_quote in (
            lambda _product, _stock: True,
            lambda _product, _stock: 0,
            lambda _product, _stock: 1.5,
            lambda _product, _stock: (_ for _ in ()).throw(ValueError("bad")),
        ):
            with self.subTest(quote=bad_quote):
                result = candidate.certified_pressure_partition(
                    actions,
                    pressure_by_product={"TOMATO": 0, "MILK": 1},
                    inventory=_inventory(),
                    max_rival_units=4,
                    price_by_stock=bad_quote,
                )
                self.assertEqual(result.actions, tuple(actions))
                self.assertFalse(result.changed)

    def test_invalid_inventory_is_a_barrier(self) -> None:
        neutral = _sell("TOMATO", 1, "neutral")
        exposed = _sell("MILK", 1, "exposed")
        inventory = _inventory()
        inventory["TOMATO"] = True
        result = candidate.certified_pressure_partition(
            [neutral, exposed],
            pressure_by_product={"TOMATO": 0, "MILK": 1},
            inventory=inventory,
            max_rival_units=4,
            price_by_stock=lambda _product, _stock: 9,
        )
        self.assertEqual(result.actions, (neutral, exposed))
        self.assertEqual(
            result.decisions[0].certificate.reason,
            "invalid_bound_or_inventory",
        )

    def test_barriers_split_reordering_segments(self) -> None:
        safe_a = _sell("TOMATO", 1, "safe-a")
        exposed_a = _sell("MILK", 1, "exposed-a")
        barrier = {"action": "HIRE", "tag": "segment-barrier"}
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
            inventory=_inventory(),
            max_rival_units=3,
            price_by_stock=lambda _product, _stock: 5,
        )
        self.assertEqual(
            result.actions,
            (exposed_a, safe_a, barrier, exposed_b, safe_b),
        )
        self.assertIs(result.actions[2], barrier)

    def test_uncertified_lot_blocks_every_later_pressure_lot(self) -> None:
        safe = _sell("WHEAT", 1, "safe")
        unsafe = _sell("TOMATO", 1, "unsafe")
        exposed_1 = _sell("MILK", 1, "exposed-1")
        exposed_2 = _sell("EGG", 1, "exposed-2")

        def quote(product: str, stock: int) -> int:
            if product == "TOMATO":
                return max(1, 8 - stock)
            return 5

        result = candidate.certified_pressure_partition(
            [safe, unsafe, exposed_1, exposed_2],
            pressure_by_product={
                "WHEAT": 0,
                "TOMATO": 0,
                "MILK": 1,
                "EGG": 1,
            },
            inventory=_inventory(),
            max_rival_units=2,
            price_by_stock=quote,
        )
        self.assertEqual(
            result.actions,
            (safe, unsafe, exposed_1, exposed_2),
        )
        self.assertEqual(result.decisions[1].kind, "barrier")

    def test_stable_order_and_object_identity_are_preserved(self) -> None:
        neutral_1 = _sell("TOMATO", 1, "neutral-1")
        exposed_1 = _sell("MILK", 1, "exposed-1")
        neutral_2 = _sell("TOMATO", 2, "neutral-2")
        exposed_2 = _sell("MILK", 2, "exposed-2")
        actions = [neutral_1, exposed_1, neutral_2, exposed_2]
        snapshot = copy.deepcopy(actions)
        result = candidate.certified_pressure_partition(
            actions,
            pressure_by_product={"TOMATO": 0, "MILK": 2},
            inventory=_inventory(),
            max_rival_units={"TOMATO": 4, "MILK": 4},
            price_by_stock=lambda _product, _stock: 11,
        )
        self.assertEqual(
            result.actions,
            (exposed_1, exposed_2, neutral_1, neutral_2),
        )
        self.assertIs(result.actions[0], exposed_1)
        self.assertIs(result.actions[1], exposed_2)
        self.assertIs(result.actions[2], neutral_1)
        self.assertIs(result.actions[3], neutral_2)
        self.assertEqual(actions, snapshot)

    def test_exact_receipt_input_contract(self) -> None:
        quote = lambda _product, stock: 10 - stock
        self.assertEqual(candidate.exact_sale_receipt("TOMATO", 0, 3, quote), 27)
        self.assertIsNone(candidate.exact_sale_receipt("TOMATO", True, 1, quote))
        self.assertIsNone(candidate.exact_sale_receipt("TOMATO", 0, False, quote))
        self.assertIsNone(candidate.exact_sale_receipt("UNKNOWN", 0, 1, quote))


if __name__ == "__main__":
    unittest.main(verbosity=2)
