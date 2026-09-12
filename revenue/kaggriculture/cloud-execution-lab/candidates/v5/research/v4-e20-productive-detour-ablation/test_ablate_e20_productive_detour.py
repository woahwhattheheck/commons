# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import subprocess
import types
import unittest

HERE = Path(__file__).resolve().parent
REPO = HERE
while REPO != REPO.parent and not (REPO / ".git").exists():
    REPO = REPO.parent

SPEC = importlib.util.spec_from_file_location(
    "e20_ablation", HERE / "ablate_e20_productive_detour.py"
)
A = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(A)


def git_show(commit: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{A.HELPER_PATH}"],
        cwd=REPO,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def load_source(name: str, source: bytes):
    module = types.ModuleType(name)
    exec(compile(source, f"<{name}>", "exec"), module.__dict__)
    return module


class FakeMechanics:
    PRODUCTS = {"WHEAT"}
    CROPS = {"WHEAT": {"first_yield_day": 0}}
    ANIMALS = {}

    @staticmethod
    def _apply_unit_action(farm, private, worker, action, board, day, day_len, cap):
        return None

    @staticmethod
    def _hire_cost(hires_today, mult):
        return 1 * mult

    @staticmethod
    def _do_hire(farm, private, board, mult):
        cost = FakeMechanics._hire_cost(farm["hires_today"], mult)
        farm["money"] -= cost
        farm["hires_today"] += 1
        farm["hands"].append([4, 4])
        private["inventories"].append({})

    @staticmethod
    def market_price(item, inventory, params):
        return 100


def fixture(*, harvestable: bool = True):
    tiles = [[{} for _x in range(10)] for _y in range(10)]
    tiles[4][4] = {
        "kind": "PLANT",
        "crop": "WHEAT",
        "yield_units": 1 if harvestable else 0,
        "planted_day": 0,
        "max_lifespan_step": -1,
        "watered_today": True,
    }
    obs = {
        "step": 18,
        "day": 0,
        "player": 0,
        "farms": [
            {"tiles": tiles, "farmer": [0, 0], "hands": [], "hires_today": 0, "money": 100},
            {"tiles": [[{} for _x in range(10)] for _y in range(10)]},
        ],
        "private": {"seeds": {}, "shed": {}, "inventories": []},
        "market": {"inventory": {"WHEAT": 10000}, "prices": {"WHEAT": 100}, "params": None},
    }
    cfg = {
        "boardSize": 10,
        "turnsPerDay": 24,
        "episodeSteps": 720,
        "shedCapacity": 100,
        "maxMarketOrdersPerTurn": 10,
        "farmHandCostMult": 1,
    }
    selected = {"farmer": ["PASS"], "hands": [], "market": [["HIRE"]]}
    route = [
        {"farmer": ["PASS"], "hands": [["PASS"]], "market": []}
        for _ in range(24)
    ]
    return obs, cfg, selected, route


class ExactSubmittedV4E20AblationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v4 = git_show(A.V4_COMMIT)
        cls.v31 = git_show(A.V31_COMMIT)
        cls.off = A.ablate_productive_detour(cls.v4, cls.v31)
        cls.v4_module = load_source("submitted_v4_redundant_hire", cls.v4)
        cls.off_module = load_source("submitted_v4_e20_detour_off", cls.off)

    def test_exact_source_authority(self):
        self.assertEqual(A.git_blob(self.v4), A.V4_HELPER_GIT_BLOB)
        self.assertEqual(A.git_blob(self.v31), A.V31_HELPER_GIT_BLOB)

    def test_ablation_keeps_every_v4_byte_before_e20_tail(self):
        marker = A.V4_E20_START.encode()
        prefix = self.v4[: self.v4.index(marker)]
        self.assertTrue(self.off.startswith(prefix))
        v31_tail = self.v31[
            self.v31.index(A.V31_DELETE_TAIL_START.encode()) :
        ]
        self.assertTrue(self.off.endswith(v31_tail))
        self.assertIn(b"def _productive_detour(", self.off)
        compile(self.off, "<e20-off-contract>", "exec")

    def test_productive_witness_is_the_only_behavioral_divergence(self):
        obs, cfg, selected, route = fixture(harvestable=True)
        v4_route = copy.deepcopy(route)
        off_route = copy.deepcopy(route)

        v4_action, v4_report = self.v4_module.propose_redundant_hires(
            FakeMechanics, copy.deepcopy(obs), copy.deepcopy(cfg), copy.deepcopy(selected),
            route=v4_route, route_id="submitted-v4", route_switch_steps=[]
        )
        off_action, off_report = self.off_module.propose_redundant_hires(
            FakeMechanics, copy.deepcopy(obs), copy.deepcopy(cfg), copy.deepcopy(selected),
            route=off_route, route_id="submitted-v4", route_switch_steps=[]
        )

        # Shipped V4 spends the redundant worker on a newly authored future job.
        self.assertEqual(v4_action["market"], [["HIRE"]])
        self.assertTrue(v4_report["route_changed"])
        self.assertEqual(v4_report["protected_workers"], 1)
        self.assertEqual(v4_report["completed_jobs"], 1)
        self.assertEqual(v4_route[19]["hands"][0], ["HARVEST"])
        self.assertEqual(v4_route[20]["hands"][0], ["DROP"])

        # Counterfactual keeps the V4 physical redundancy proof but does not
        # invent the productive detour or mutate producer-owned future route.
        self.assertEqual(off_action["market"], [["SELL", "WHEAT", 0]])
        self.assertEqual(off_route, route)
        self.assertTrue(off_report["changed"])
        self.assertEqual(off_report["reason"], "redundant_watering_or_empty_tail")
        self.assertNotIn("route_changed", off_report)

    def test_no_productive_opportunity_matches_v4_action_and_route(self):
        obs, cfg, selected, route = fixture(harvestable=False)
        v4_route = copy.deepcopy(route)
        off_route = copy.deepcopy(route)
        v4_action, _ = self.v4_module.propose_redundant_hires(
            FakeMechanics, copy.deepcopy(obs), copy.deepcopy(cfg), copy.deepcopy(selected),
            route=v4_route, route_id="submitted-v4", route_switch_steps=[]
        )
        off_action, _ = self.off_module.propose_redundant_hires(
            FakeMechanics, copy.deepcopy(obs), copy.deepcopy(cfg), copy.deepcopy(selected),
            route=off_route, route_id="submitted-v4", route_switch_steps=[]
        )
        self.assertEqual(v4_action, off_action)
        self.assertEqual(v4_route, off_route)
        self.assertEqual(v4_route, route)

    def test_wrong_sources_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "V4 .* drift"):
            A.ablate_productive_detour(self.v4 + b"\n# drift\n", self.v31)
        with self.assertRaisesRegex(ValueError, "V3.1 .* drift"):
            A.ablate_productive_detour(self.v4, self.v31 + b"\n# drift\n")


if __name__ == "__main__":
    unittest.main()
