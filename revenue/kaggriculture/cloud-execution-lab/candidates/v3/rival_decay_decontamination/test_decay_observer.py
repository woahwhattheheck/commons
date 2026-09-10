# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import importlib
import importlib.util
from pathlib import Path
import random
import sys
import types
import unittest

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[2]
SOURCE_ROOTS = (
    LAB,
    LAB.parent / "cloud-runtime-pulse",
    LAB.parent / "cloud-quickstep",
    LAB.parent / "cloud-opponent-league" / "lark-responsive",
    LAB.parent / "cloud-committed-seed-retry",
    LAB.parent / "cloud-economic-stress" / "funded-payback",
)
for root in reversed(tuple(str(path.resolve(strict=True)) for path in SOURCE_ROOTS)):
    while root in sys.path:
        sys.path.remove(root)
    sys.path.insert(0, root)


def load_exact(name: str, path: Path):
    expected = path.resolve(strict=True)
    spec = importlib.util.spec_from_file_location(name, expected)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {expected}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if Path(module.__file__).resolve() != expected:
        raise RuntimeError(f"wrong module loaded: {module.__file__}")
    return module


decay_observer = load_exact(
    "_titan_rival_decay_observer_under_test", HERE / "decay_observer.py"
)
is_exact_age_decay = decay_observer.is_exact_age_decay
make_decay_safe_frozen_selected = decay_observer.make_decay_safe_frozen_selected
scheduler = importlib.import_module("scheduler")
if Path(scheduler.__file__).resolve() != (LAB / "scheduler.py").resolve():
    raise RuntimeError(f"wrong scheduler loaded: {scheduler.__file__}")


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


def observation(step, rival_tile, *, player=0):
    farms = [{"tiles": [[None]]}, {"tiles": [[copy.deepcopy(rival_tile)]]}]
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


class ExactOriginTests(unittest.TestCase):
    def test_exact_lane_and_scheduler_origins(self):
        self.assertEqual(
            Path(decay_observer.__file__).resolve(),
            (HERE / "decay_observer.py").resolve(),
        )
        self.assertEqual(
            Path(scheduler.__file__).resolve(),
            (LAB / "scheduler.py").resolve(),
        )


class ExactTransitionTests(unittest.TestCase):
    def test_exact_surviving_parity_decay(self):
        self.assertTrue(is_exact_age_decay(plant(4), plant(3), 100))
        self.assertTrue(is_exact_age_decay(plant(2), plant(1), 102))

    def test_preserves_ambiguous_and_non_engine_transitions(self):
        cases = [
            (plant(4), plant(2), 100),
            (plant(4), plant(3), 99),
            (plant(4), plant(3), 101),
            (plant(4), {"kind": "WEED"}, 100),
            (plant(4), None, 100),
            (plant(4), plant(3, crop="CARROT"), 100),
            (plant(4), plant(3, planted_day=1), 100),
            (plant(4), plant(3, lifespan=102), 100),
            ({"kind": "COOP", "animal": "GOOSE", "yield_units": 4},
             {"kind": "COOP", "animal": "GOOSE", "yield_units": 3}, 100),
            (plant(1), {"kind": "WEED"}, 100),
            (plant("bad"), plant(3), 100),
        ]
        for before, after, step in cases:
            with self.subTest(before=before, after=after, step=step):
                self.assertFalse(is_exact_age_decay(before, after, step))


class ObserverParityTests(unittest.TestCase):
    def compare(self, before, after, *, old_step=100, new_step=101):
        control = bare(scheduler.SellScheduler)
        candidate = bare(Patched)
        old = observation(old_step, before)
        new = observation(new_step, after)
        control.previous = copy.deepcopy(old)
        candidate.previous = copy.deepcopy(old)
        scheduler.SellScheduler.observe(control, copy.deepcopy(new))
        Patched.observe(candidate, copy.deepcopy(new))
        return control.observed_harvests, candidate.observed_harvests

    def test_exact_decay_unit_is_removed(self):
        control, candidate = self.compare(plant(4), plant(3))
        self.assertEqual(control, {"MELON": [(101, 1)]})
        self.assertEqual(candidate, {})

    def test_noncontiguous_observation_is_unchanged(self):
        control, candidate = self.compare(
            plant(4), plant(3), old_step=98, new_step=101
        )
        self.assertEqual(candidate, control)
        self.assertEqual(candidate, {"MELON": [(101, 1)]})

    def test_larger_decline_keeps_non_decay_remainder(self):
        control, candidate = self.compare(plant(4), plant(2))
        self.assertEqual(control, {"MELON": [(101, 2)]})
        self.assertEqual(candidate, control)

    def test_incumbent_parity_outside_exact_domain(self):
        rng = random.Random(20260910)
        for _ in range(400):
            old_units = rng.randint(0, 8)
            drop = rng.randint(0, 4)
            new_units = max(0, old_units - drop)
            transition = rng.randint(90, 112)
            before = plant(old_units, lifespan=100)
            after = plant(new_units, lifespan=100)
            exact = is_exact_age_decay(before, after, transition)
            control, candidate = self.compare(
                before, after, old_step=transition, new_step=transition + 1
            )
            if exact:
                self.assertEqual(control, {"MELON": [(transition + 1, 1)]})
                self.assertEqual(candidate, {})
            else:
                self.assertEqual(candidate, control)


class OfficialEngineWitnessTests(unittest.TestCase):
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
        try:
            module = load_exact("_decay_test_engine", path)
        finally:
            if prior_package is None:
                sys.modules.pop("kaggle_environments", None)
            else:
                sys.modules["kaggle_environments"] = prior_package
            if prior_utils is None:
                sys.modules.pop("kaggle_environments.utils", None)
            else:
                sys.modules["kaggle_environments.utils"] = prior_utils
        return module

    def test_three_official_decay_ticks_do_not_manufacture_rival_lot(self):
        engine = self.load_engine()
        control = bare(scheduler.SellScheduler)
        candidate = bare(Patched)
        rival_farm = {"tiles": [[plant(4)]]}
        initial = observation(100, rival_farm["tiles"][0][0])
        control.previous = copy.deepcopy(initial)
        candidate.previous = copy.deepcopy(initial)

        for transition in range(100, 105):
            engine._decay_plants(rival_farm, transition)
            current = observation(transition + 1, rival_farm["tiles"][0][0])
            scheduler.SellScheduler.observe(control, copy.deepcopy(current))
            Patched.observe(candidate, copy.deepcopy(current))
            control.previous = copy.deepcopy(current)
            candidate.previous = copy.deepcopy(current)

        self.assertEqual(rival_farm["tiles"][0][0]["yield_units"], 1)
        self.assertEqual(control.observed_harvests, {
            "MELON": [(101, 1), (103, 1), (105, 1)]
        })
        self.assertEqual(candidate.observed_harvests, {})
        final = observation(105, rival_farm["tiles"][0][0])
        self.assertEqual(scheduler.SellScheduler.rival_supply(control, final, "MELON"), 3)
        self.assertEqual(Patched.rival_supply(candidate, final, "MELON"), 1)

    def test_supply_change_flips_concrete_optimizer_decision(self):
        common = dict(
            item="MELON",
            quantity=2,
            inventory=80,
            params=None,
            shops=[],
            config={"townShopSellInterval": 4, "townCenterSellInterval": 24},
            now=100,
            dates=(100, 104, 108),
            reference=((100, 2),),
            minimum_now=0,
            capacity_ok=lambda _plan: True,
            last=718,
        )
        clean_plan, clean = scheduler.optimize_lot(rival_quantity=1, **common)
        polluted_plan, polluted = scheduler.optimize_lot(rival_quantity=3, **common)
        self.assertEqual(clean_plan, ((108, 2),))
        self.assertGreater(clean["worst_relative_gain"], 100.0)
        self.assertEqual(polluted_plan, ((100, 2),))
        self.assertEqual(polluted["worst_relative_gain"], 0.0)


if __name__ == "__main__":
    unittest.main()
