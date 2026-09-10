# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys
import types
import unittest

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[2]
for root in (LAB.parent / "cloud-runtime-pulse", LAB):
    text = str(root.resolve(strict=True))
    if text not in sys.path:
        sys.path.append(text)

from decay_observer import (
    REACHABILITY_OPERATION,
    actor_occupancy_at,
    make_decay_safe_frozen_selected,
)
import scheduler


def plant(yield_units=4, *, crop="MELON", planted_day=0, lifespan=100, **extra):
    value = {
        "kind": "PLANT",
        "crop": crop,
        "planted_day": planted_day,
        "max_lifespan_step": lifespan,
        "yield_units": yield_units,
    }
    value.update(extra)
    return value


def animal(yield_units=3, *, name="GOOSE"):
    return {"kind": "COOP", "animal": name, "yield_units": yield_units}


def farm_with_tile(
    tile,
    *,
    coordinate=(0, 0),
    size=2,
    farmer=(1, 1),
    hands=(),
):
    tiles = [[None for _ in range(size)] for _ in range(size)]
    x, y = coordinate
    tiles[y][x] = copy.deepcopy(tile)
    return {
        "tiles": tiles,
        "farmer": list(farmer),
        "hands": [list(position) for position in hands],
    }


def observation(step, rival_farm, *, player=0):
    own = farm_with_tile(None)
    farms = [own, copy.deepcopy(rival_farm)]
    if player == 1:
        farms.reverse()
    return {"step": step, "player": player, "farms": farms}


def bare(cls):
    value = object.__new__(cls)
    value.previous = None
    value.observed_harvests = {}
    return value


Patched = make_decay_safe_frozen_selected(
    scheduler.SellScheduler,
    products=scheduler.PRODUCTS,
    animals=scheduler.m.ANIMALS,
)


class ActorOccupancyProofTests(unittest.TestCase):
    def test_complete_farm_proves_farmer_or_hand_occupancy(self):
        farm = farm_with_tile(plant(), farmer=(1, 1), hands=((0, 0),))
        self.assertTrue(actor_occupancy_at(farm, 0, 0))
        self.assertTrue(actor_occupancy_at(farm, 1, 1))
        self.assertFalse(actor_occupancy_at(farm, 1, 0))

    def test_adjacent_actor_is_not_reachable_harvest(self):
        farm = farm_with_tile(plant(), farmer=(1, 0), hands=())
        self.assertFalse(actor_occupancy_at(farm, 0, 0))

    def test_malformed_or_incomplete_shape_is_unknown(self):
        valid = farm_with_tile(plant())
        cases = [
            None,
            {},
            {**valid, "farmer": None},
            {**valid, "farmer": [True, 1]},
            {**valid, "farmer": [1.0, 1]},
            {**valid, "farmer": [1]},
            {**valid, "hands": None},
            {**valid, "hands": [[5, 5]]},
            {**valid, "tiles": []},
            {**valid, "tiles": [[None], "bad"]},
        ]
        for case in cases:
            with self.subTest(case=case):
                self.assertIsNone(actor_occupancy_at(case, 0, 0))


class ObserverReachabilityTests(unittest.TestCase):
    def compare(
        self,
        before,
        after,
        *,
        farmer=(1, 1),
        hands=(),
        old_step=100,
        new_step=101,
        player=0,
        malformed=None,
    ):
        old_farm = farm_with_tile(before, farmer=farmer, hands=hands)
        new_farm = farm_with_tile(after, farmer=farmer, hands=hands)
        if malformed == "missing_farmer":
            old_farm.pop("farmer")
        elif malformed == "bad_hands":
            old_farm["hands"] = "bad"
        elif malformed == "out_of_bounds":
            old_farm["farmer"] = [9, 9]

        old = observation(old_step, old_farm, player=player)
        new = observation(new_step, new_farm, player=player)
        control = bare(scheduler.SellScheduler)
        candidate = bare(Patched)
        control.previous = copy.deepcopy(old)
        candidate.previous = copy.deepcopy(old)
        scheduler.SellScheduler.observe(control, copy.deepcopy(new))
        Patched.observe(candidate, copy.deepcopy(new))
        return control.observed_harvests, candidate.observed_harvests

    def test_unoccupied_plant_to_weed_is_not_harvest(self):
        control, candidate = self.compare(plant(1), {"kind": "WEED"})
        self.assertEqual(control, {"MELON": [(101, 1)]})
        self.assertEqual(candidate, {})

    def test_unoccupied_larger_drop_is_not_harvest(self):
        control, candidate = self.compare(plant(5), plant(2))
        self.assertEqual(control, {"MELON": [(101, 3)]})
        self.assertEqual(candidate, {})

    def test_unoccupied_disappearance_is_not_harvest(self):
        control, candidate = self.compare(plant(4), None)
        self.assertEqual(control, {"MELON": [(101, 4)]})
        self.assertEqual(candidate, {})

    def test_unoccupied_animal_decline_is_not_harvest(self):
        control, candidate = self.compare(animal(3), animal(1))
        self.assertEqual(control, {"EGG": [(101, 2)]})
        self.assertEqual(candidate, {})

    def test_adjacent_actor_cannot_move_and_harvest(self):
        control, candidate = self.compare(
            plant(1), {"kind": "WEED"}, farmer=(1, 0)
        )
        self.assertEqual(control, {"MELON": [(101, 1)]})
        self.assertEqual(candidate, {})

    def test_farmer_on_tile_preserves_possible_harvest(self):
        control, candidate = self.compare(plant(4), plant(0), farmer=(0, 0))
        self.assertEqual(candidate, control)
        self.assertEqual(candidate, {"MELON": [(101, 4)]})

    def test_hand_on_tile_preserves_possible_harvest(self):
        control, candidate = self.compare(
            plant(4), plant(0), farmer=(1, 1), hands=((0, 0),)
        )
        self.assertEqual(candidate, control)
        self.assertEqual(candidate, {"MELON": [(101, 4)]})

    def test_noncontiguous_observations_preserve_incumbent(self):
        control, candidate = self.compare(
            plant(4), None, old_step=98, new_step=101
        )
        self.assertEqual(candidate, control)
        self.assertEqual(candidate, {"MELON": [(101, 4)]})

    def test_malformed_actor_custody_preserves_incumbent(self):
        for malformed in ("missing_farmer", "bad_hands", "out_of_bounds"):
            with self.subTest(malformed=malformed):
                control, candidate = self.compare(
                    plant(4), None, malformed=malformed
                )
                self.assertEqual(candidate, control)
                self.assertEqual(candidate, {"MELON": [(101, 4)]})

    def test_both_candidate_seats_use_the_public_rival_farm(self):
        for player in (0, 1):
            with self.subTest(player=player):
                control, candidate = self.compare(
                    plant(1), {"kind": "WEED"}, player=player
                )
                self.assertEqual(control, {"MELON": [(101, 1)]})
                self.assertEqual(candidate, {})

    def test_class_exposes_stacked_operation_marker(self):
        self.assertEqual(
            Patched._titan_rival_harvest_actor_reachability,
            REACHABILITY_OPERATION,
        )


class OfficialOneActionWitnessTests(unittest.TestCase):
    @staticmethod
    def load_engine():
        package = types.ModuleType("kaggle_environments")
        utils = types.ModuleType("kaggle_environments.utils")
        utils.resolve_episode_seed = lambda env: 0
        prior_package = sys.modules.get("kaggle_environments")
        prior_utils = sys.modules.get("kaggle_environments.utils")
        sys.modules["kaggle_environments"] = package
        sys.modules["kaggle_environments.utils"] = utils
        path = LAB / "reference/engine/kaggriculture.py"
        spec = importlib.util.spec_from_file_location("_actor_reachability_engine", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if prior_package is None:
            sys.modules.pop("kaggle_environments", None)
        else:
            sys.modules["kaggle_environments"] = prior_package
        if prior_utils is None:
            sys.modules.pop("kaggle_environments.utils", None)
        else:
            sys.modules["kaggle_environments.utils"] = prior_utils
        return module

    def test_three_unoccupied_decay_to_weed_transitions_create_zero_supply(self):
        engine = self.load_engine()
        rival_farm = {
            "tiles": [
                [plant(1), plant(1)],
                [plant(1), None],
            ],
            "farmer": [1, 1],
            "hands": [],
        }
        old = observation(100, rival_farm)
        engine._decay_plants(rival_farm, 100)
        self.assertEqual(
            [rival_farm["tiles"][0][0], rival_farm["tiles"][0][1], rival_farm["tiles"][1][0]],
            [{"kind": "WEED"}, {"kind": "WEED"}, {"kind": "WEED"}],
        )
        new = observation(101, rival_farm)

        control = bare(scheduler.SellScheduler)
        candidate = bare(Patched)
        control.previous = copy.deepcopy(old)
        candidate.previous = copy.deepcopy(old)
        scheduler.SellScheduler.observe(control, copy.deepcopy(new))
        Patched.observe(candidate, copy.deepcopy(new))

        self.assertEqual(
            control.observed_harvests,
            {"MELON": [(101, 1), (101, 1), (101, 1)]},
        )
        self.assertEqual(candidate.observed_harvests, {})
        self.assertEqual(
            scheduler.SellScheduler.rival_supply(control, new, "MELON"), 3
        )
        self.assertEqual(Patched.rival_supply(candidate, new, "MELON"), 0)

        common = dict(
            item="MELON",
            quantity=4,
            inventory=9550,
            params=None,
            shops=[],
            config={"townShopSellInterval": 4, "townCenterSellInterval": 24},
            now=90,
            dates=(90, 96),
            reference=((90, 4),),
            minimum_now=0,
            capacity_ok=lambda _plan: True,
            last=718,
        )
        clean_plan, clean = scheduler.optimize_lot(rival_quantity=0, **common)
        polluted_plan, polluted = scheduler.optimize_lot(rival_quantity=3, **common)
        self.assertEqual(clean_plan, ((90, 3),))
        self.assertEqual(clean["worst_relative_gain"], 1.0)
        self.assertEqual((polluted_plan, ((90, 4),)))
        self.assertEqual(polluted["worst_relative_gain"], 0.0)

    def test_actor_must_start_on_tile_to_harvest(self):
        engine = self.load_engine()
        farm = {
            "tiles": [[None, plant(4)], [None, None]],
            "farmer": [0, 0],
            "hands": [],
        }
        private = {"shed": {}, "seeds": {}, "inventories": [{}]}
        engine._apply_unit_action(
            farm,
            private,
            0,
            ["EAST"],
            2,
            10,
            24,
            100,
        )
        self.assertEqual(farm["farmer"], [1, 0])
        self.assertEqual(farm["tiles"][0][1]["yield_units"], 4)
        self.assertEqual(private["inventories"], [{}])


if __name__ == "__main__":
    unittest.main()
