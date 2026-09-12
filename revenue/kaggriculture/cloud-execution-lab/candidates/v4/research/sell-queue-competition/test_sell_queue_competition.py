#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import itertools
import math
from pathlib import Path
import random
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sell_queue_competition", HERE / "sell_queue_competition.py")
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class OfficialLike:
    PRICE_FLOOR = 1
    MARKET_PARAMS = {
        "WHEAT":      {"base": 25,  "I0": 10000, "T": 400, "below_func": "sqrt",  "below_target": .80, "above_func": "log",    "above_target": .20},
        "CARROT":     {"base": 35,  "I0": 10000, "T": 450, "below_func": "hinge", "below_target": 1.0, "above_func": "sqrt",   "above_target": .70},
        "TOMATO":     {"base": 60,  "I0": 10000, "T": 200, "below_func": "hinge", "below_target": .40, "above_func": "sqrt",   "above_target": .60},
        "STRAWBERRY": {"base": 120, "I0": 10000, "T": 100, "below_func": "sqrt",  "below_target": .70, "above_func": "linear", "above_target": 1.60},
        "MELON":      {"base": 250, "I0": 10000, "T": 300, "below_func": "log",   "below_target": .20, "above_func": "sq",     "above_target": 3.60},
        "EGG":        {"base": 50,  "I0": 10000, "T": 332, "below_func": "hinge", "below_target": .40, "above_func": "log",    "above_target": .20},
        "MILK":       {"base": 160, "I0": 10000, "T": 122, "below_func": "sqrt",  "below_target": .60, "above_func": "linear", "above_target": 1.60},
        "WOOL":       {"base": 200, "I0": 10000, "T": 105, "below_func": "log",   "below_target": .20, "above_func": "sq",     "above_target": 3.20},
        "FERTILIZER": {"base": 100, "I0": 10000, "T": 200, "below_func": "linear","below_target": .40, "above_func": "linear", "above_target": .40},
    }

    @staticmethod
    def _shape(name, x, T):
        x = max(0.0, x)
        if name == "linear": return x
        if name == "sq": return x * x
        if name == "sqrt": return math.sqrt(x)
        if name == "log": return math.log(1.0 + x)
        if name == "log10": return math.log10(1.0 + x)
        if name == "hinge":
            u = x / T
            return u + 8.0 * max(0.0, u - 1.0) ** 2
        return x

    @classmethod
    def market_price(cls, item, inventory, params=None):
        p = (params or cls.MARKET_PARAMS)[item]
        base, I0, T = p["base"], p["I0"], p["T"]
        if inventory < I0:
            f = p["below_func"]
            amp = p["below_target"] * base / cls._shape(f, T, T)
            price = base + amp * cls._shape(f, I0 - inventory, T)
        else:
            f = p["above_func"]
            amp = p["above_target"] * base / cls._shape(f, T, T)
            price = base - amp * cls._shape(f, inventory - I0, T)
        return max(1, int(round(price)))


MODEL = OfficialLike


class SellQueueCompetition(unittest.TestCase):
    def test_endpoint_proxy_misranks_source_real_witness(self):
        self.assertEqual(mod.endpoint_proxy_cost(MODEL, "MELON", 10025, 60), 3960)
        self.assertEqual(mod.endpoint_proxy_cost(MODEL, "WOOL", 10025, 30), 4200)
        self.assertEqual(mod.mirror_displacement_cost(MODEL, "MELON", 10025, 60), 6083)
        self.assertEqual(mod.mirror_displacement_cost(MODEL, "WOOL", 10025, 30), 3071)

    def test_exact_optimizer_turns_proxy_tie_into_3012_edge(self):
        inventory = {"MELON": 10025, "WOOL": 10025}
        shed = {"MELON": 60, "WOOL": 30}
        baseline = [["SELL", "WOOL", 30], ["SELL", "MELON", 60]]
        proposal, cert = mod.optimize_mirror_queue(MODEL, baseline, inventory, shed)
        self.assertEqual(proposal, [["SELL", "MELON", 60], ["SELL", "WOOL", 30]])
        self.assertEqual(cert["predicted_mirror_edge"], 3012)
        c0, o0, _ = mod.simulate_sell_queues(MODEL, baseline, baseline, inventory, shed)
        self.assertEqual(c0 - o0, 0)
        cand, opp, _ = mod.simulate_sell_queues(MODEL, proposal, baseline, inventory, shed)
        self.assertEqual(cand - opp, 3012)

    def test_assignment_is_not_descending_sort(self):
        permutation, edge = mod.optimal_indices([1, 5, 10])
        self.assertEqual(permutation, [1, 2, 0])
        self.assertEqual(edge, 14)
        self.assertEqual(mod.edge_for_indices([1, 5, 10], [2, 1, 0]), 9)

    def test_dp_matches_bruteforce(self):
        rng = random.Random(21704)
        for n in range(2, 7):
            for _ in range(30):
                costs = [rng.randrange(0, 500) for _ in range(n)]
                perm, edge = mod.optimal_indices(costs)
                brute = max(mod.edge_for_indices(costs, p) for p in itertools.permutations(range(n)))
                self.assertEqual(edge, max(0, brute))
                self.assertEqual(mod.edge_for_indices(costs, perm), edge)

    def test_closed_form_matches_direct_lockstep_random(self):
        rng = random.Random(9122026)
        products = list(MODEL.MARKET_PARAMS)
        for _ in range(200):
            n = rng.randrange(2, 6)
            items = rng.sample(products, n)
            quantities = [rng.randrange(1, 21) for _ in range(n)]
            baseline = [["SELL", item, qty] for item, qty in zip(items, quantities)]
            candidate = baseline[:]
            rng.shuffle(candidate)
            inventory = {item: rng.randrange(9800, 10401) for item in items}
            shed = {item: qty for item, qty in zip(items, quantities)}
            predicted = mod.predicted_edge_for_rows(
                MODEL, baseline, candidate, inventory, shed
            )
            cand, opp, _ = mod.simulate_sell_queues(
                MODEL, candidate, baseline, inventory, shed
            )
            self.assertEqual(cand - opp, predicted)

    def test_duplicate_product_fails_closed(self):
        rows = [["SELL", "WOOL", 1], ["SELL", "WOOL", 1]]
        with self.assertRaises(mod.EvidenceError):
            mod.optimize_mirror_queue(MODEL, rows, {"WOOL": 10000}, {"WOOL": 2})

    def test_executable_prefix_and_barrier_are_preserved(self):
        rows = [
            ["SELL", "WOOL", 30],
            ["SELL", "MELON", 60],
            ["HIRE"],
            ["SELL", "STRAWBERRY", 10],
        ]
        result, cert = mod.optimize_mirror_queue(
            MODEL,
            rows,
            {"WOOL": 10025, "MELON": 10025, "STRAWBERRY": 10000},
            {"WOOL": 30, "MELON": 60, "STRAWBERRY": 10},
            max_orders=4,
        )
        self.assertEqual(result[2:], rows[2:])
        self.assertEqual(cert["block_len"], 2)

    def test_cap_makes_suffix_inert(self):
        rows = [
            ["SELL", "WOOL", 30],
            ["SELL", "MELON", 60],
            "poison suffix outside cap",
        ]
        result, cert = mod.optimize_mirror_queue(
            MODEL,
            rows,
            {"WOOL": 10025, "MELON": 10025},
            {"WOOL": 30, "MELON": 60},
            max_orders=2,
        )
        self.assertEqual(result[2], rows[2])
        self.assertEqual(cert["executable_limit"], 2)

    def test_negative_public_inventory_is_valid_engine_state(self):
        cost = mod.mirror_displacement_cost(MODEL, "WHEAT", -5, 10)
        self.assertGreaterEqual(cost, 0)

    def test_zero_fill_is_safe_identity_cost(self):
        self.assertEqual(mod.mirror_displacement_cost(MODEL, "WOOL", 10000, 0), 0)

    def test_scan_finds_real_rank_inversions(self):
        scan = mod.scan_proxy_inversions(MODEL)
        self.assertGreater(scan["proxy_exact_rank_inversions"], 0)
        self.assertIsNotNone(scan["worst_in_grid"])

    @unittest.skipUnless(mod.MECHANICS_PATH.exists(), "repo-mounted mechanics.py unavailable")
    def test_repo_mechanics_exact_blob_and_witness(self):
        model = mod.load_pinned_mechanics()
        report = mod.witness(model)
        self.assertEqual(report["direct_edge"], 3012)
        self.assertEqual(report["predicted_edge"], 3012)


if __name__ == "__main__":
    unittest.main()
