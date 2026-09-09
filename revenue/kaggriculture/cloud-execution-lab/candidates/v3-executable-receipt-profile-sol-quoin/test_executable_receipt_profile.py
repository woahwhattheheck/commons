# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest import mock

from executable_receipt_profile import (
    executable_market_prefix,
    git_blob_sha1,
    install,
)

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]


def _install_repository_import_roots() -> list[Path]:
    """Resolve bare integrated-source imports from the canonical build map.

    The checked-in lab modules intentionally use bare root imports. Several of
    those roots (for example ``observed_clone``) are mapped from sibling source
    directories by ``build_integrated.source_files`` rather than stored directly
    in the lab. Exact-tree tests must reproduce that declared source closure,
    not depend on an ambient developer PYTHONPATH.
    """
    lab = LAB.resolve()
    lab_text = str(lab)
    if lab_text not in sys.path:
        sys.path.insert(0, lab_text)
    from build_integrated import source_files

    ordered = [lab]
    seen = {lab}
    for member, source in source_files().items():
        if Path(member).parent != Path("."):
            continue
        origin = (lab / source).resolve()
        if not origin.is_file():
            raise FileNotFoundError(
                f"mapped root module {member} missing at {origin}"
            )
        parent = origin.parent
        if parent not in seen:
            seen.add(parent)
            ordered.append(parent)

    # Preserve the build map's deterministic priority while removing stale
    # ambient copies of these roots.
    for root in reversed(ordered):
        value = str(root)
        while value in sys.path:
            sys.path.remove(value)
        sys.path.insert(0, value)
    return ordered


class _Base:
    def receipt_profile(self, obs, selected, farm, private, end, item, config):
        route = self.controller.R[self.controller.cur]
        return [selected.get("market", [])] + [
            route[t].get("market", []) for t in range(int(obs["step"]), end + 1)
        ]


def _fake_module(path: Path):
    return SimpleNamespace(__file__=str(path), FrozenSelected=_Base)


class PrefixViewUnitTests(unittest.TestCase):
    def test_action_view_slices_without_mutating_input(self):
        action = {"farmer": ["PASS"], "market": [[], ["HIRE"], ["BUY_LAND"]]}
        before = copy.deepcopy(action)
        viewed = executable_market_prefix(action, 2)
        self.assertEqual(viewed["market"], [[], ["HIRE"]])
        self.assertEqual(action, before)
        self.assertIsNot(viewed, action)

    def test_non_dict_and_non_list_payloads_preserve_predecessor_shape(self):
        self.assertEqual(executable_market_prefix(["PASS"], 1), ["PASS"])
        action = {"market": "malformed"}
        self.assertEqual(executable_market_prefix(action, 1), action)

    def test_installed_wrapper_slices_current_and_future_queues(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "frozen_selected.py"
            source.write_text("# fake frozen selected\n", encoding="utf-8")
            module = _fake_module(source)
            frozen_blob = git_blob_sha1(source)
            scheduler_blob = git_blob_sha1(Path(__file__))
            receipt = install(
                module,
                expected_frozen_blob=frozen_blob,
                expected_scheduler_blob=scheduler_blob,
            )
            obj = object.__new__(module.FrozenSelected)
            original_route = [
                {"market": [["HIRE"], ["BUY_LAND"]]},
                {"market": [[], ["BUY_ANIMAL", "GOOSE", 2]]},
            ]
            obj.controller = SimpleNamespace(cur=0, R=[original_route])
            selected = {"market": [[], ["SELL", "CARROT", 3]]}
            before_selected = copy.deepcopy(selected)
            before_route = copy.deepcopy(original_route)
            seen = obj.receipt_profile(
                {"step": 0}, selected, {}, {}, 1, "CARROT",
                {"maxMarketOrdersPerTurn": 1},
            )
            self.assertTrue(receipt["installed"])
            self.assertEqual(seen, [[[]], [["HIRE"]], [[]]])
            self.assertEqual(selected, before_selected)
            self.assertEqual(original_route, before_route)

    def test_zero_config_uses_official_minimum_one_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "frozen_selected.py"
            source.write_text("# fake frozen selected zero\n", encoding="utf-8")
            module = _fake_module(source)
            install(
                module,
                expected_frozen_blob=git_blob_sha1(source),
                expected_scheduler_blob=git_blob_sha1(Path(__file__)),
            )
            obj = object.__new__(module.FrozenSelected)
            obj.controller = SimpleNamespace(
                cur=0, R=[[{"market": [["HIRE"], ["BUY_LAND"]]}]]
            )
            seen = obj.receipt_profile(
                {"step": 0}, {"market": [["HIRE"], ["BUY_LAND"]]},
                {}, {}, 0, "CARROT", {"maxMarketOrdersPerTurn": 0},
            )
            self.assertEqual(seen, [[["HIRE"]], [["HIRE"]]])

    def test_install_is_idempotent_and_rejects_conflicting_source_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "frozen_selected.py"
            source.write_text("# fake frozen selected idempotent\n", encoding="utf-8")
            module = _fake_module(source)
            frozen_blob = git_blob_sha1(source)
            scheduler_blob = git_blob_sha1(Path(__file__))
            first = install(
                module,
                expected_frozen_blob=frozen_blob,
                expected_scheduler_blob=scheduler_blob,
            )
            second = install(
                module,
                expected_frozen_blob=frozen_blob,
                expected_scheduler_blob=scheduler_blob,
            )
            self.assertTrue(first["installed"])
            self.assertTrue(second["idempotent"])
            with self.assertRaisesRegex(RuntimeError, "different source bytes"):
                install(
                    module,
                    expected_frozen_blob="0" * 40,
                    expected_scheduler_blob=scheduler_blob,
                )

    def test_source_drift_fails_before_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "frozen_selected.py"
            source.write_text("# unexpected bytes\n", encoding="utf-8")
            module = _fake_module(source)
            with self.assertRaisesRegex(RuntimeError, "source drift"):
                install(
                    module,
                    expected_frozen_blob="f" * 40,
                    expected_scheduler_blob=git_blob_sha1(Path(__file__)),
                )
            self.assertIs(module.FrozenSelected, _Base)


@unittest.skipUnless((LAB / "frozen_selected.py").is_file(), "repository source unavailable")
class ExactRepositoryWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.import_roots = _install_repository_import_roots()
        import frozen_selected
        import scheduler

        cls.fs = frozen_selected
        cls.scheduler = scheduler
        cls.predecessor = frozen_selected.FrozenSelected

    @staticmethod
    def _physical_state():
        farm = {
            "money": 0,
            "hires_today": 0,
            "unlocked_quadrants": ["NW"],
            "hands": [],
            "tiles": [[None for _ in range(10)] for _ in range(10)],
        }
        shed = {name: 0 for name in [
            "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "EGG", "MILK", "WOOL", "FERTILIZER", "GOOSE", "COW", "SHEEP",
        ]}
        shed["CARROT"] = 3
        private = {"shed": shed, "seeds": {}, "inventories": [{}]}
        return farm, private

    def _profile(self, cls, route):
        scheduler = self.scheduler
        obj = object.__new__(cls)
        obj.controller = SimpleNamespace(cur=0, R=[route])
        farm, private = self._physical_state()

        def projected(*_args, **_kwargs):
            return copy.deepcopy(farm), copy.deepcopy(private)

        # ``receipt_profile`` is inherited from scheduler.SellScheduler. Its
        # helper lookups resolve in scheduler.__dict__, not frozen_selected's
        # module globals. Patch the exact defining globals so this witness cannot
        # silently fall through to a malformed synthetic observation.
        with mock.patch.object(scheduler, "post_units", side_effect=projected), \
             mock.patch.object(scheduler.m, "_apply_unit_action", return_value=None):
            return obj.receipt_profile(
                {"step": 0},
                {"farmer": ["PASS"], "hands": [], "market": []},
                farm,
                private,
                2,
                "CARROT",
                {"shedCapacity": 4, "maxMarketOrdersPerTurn": 1},
            )

    def test_receipt_profile_helpers_resolve_from_defining_scheduler_module(self):
        globals_table = self.predecessor.receipt_profile.__globals__
        self.assertIs(globals_table, self.scheduler.__dict__)
        self.assertIs(globals_table["post_units"], self.scheduler.post_units)
        self.assertIs(globals_table["m"], self.scheduler.m)

    def test_repository_import_closure_uses_declared_source_map(self):
        self.assertIn(LAB.resolve(), self.import_roots)
        import observed_clone

        self.assertTrue(Path(observed_clone.__file__).resolve().is_file())
        self.assertIn(Path(observed_clone.__file__).resolve().parent, self.import_roots)

    def test_inactive_animal_purchase_no_longer_forces_early_liquidation(self):
        route = [
            {"farmer": ["PASS"], "hands": [], "market": []},
            {"farmer": ["PASS"], "hands": [],
             "market": [[], ["BUY_ANIMAL", "GOOSE", 2]]},
            {"farmer": ["PASS"], "hands": [], "market": []},
        ]
        predecessor_feasible = self._profile(self.predecessor, route)
        self.assertFalse(predecessor_feasible(((0, 0), (2, 3))))
        self.assertTrue(predecessor_feasible(((0, 2), (2, 1))))

        receipt = install(self.fs)
        candidate_feasible = self._profile(self.fs.FrozenSelected, route)
        self.assertTrue(receipt["installed"] or receipt["idempotent"])
        self.assertTrue(candidate_feasible(((0, 0), (2, 3))))

    def test_active_prefix_behavior_is_unchanged(self):
        route = [
            {"farmer": ["PASS"], "hands": [], "market": []},
            {"farmer": ["PASS"], "hands": [],
             "market": [["BUY_ANIMAL", "GOOSE", 2], []]},
            {"farmer": ["PASS"], "hands": [], "market": []},
        ]
        predecessor_feasible = self._profile(self.predecessor, route)
        install(self.fs)
        candidate_feasible = self._profile(self.fs.FrozenSelected, route)
        plans = [
            ((0, 0), (2, 3)),
            ((0, 1), (2, 2)),
            ((0, 2), (2, 1)),
            ((0, 3),),
        ]
        self.assertEqual(
            [predecessor_feasible(plan) for plan in plans],
            [candidate_feasible(plan) for plan in plans],
        )

    def test_preserved_engine_ignores_suffix_and_clips_active_purchase_to_capacity(self):
        engine_path = LAB / "reference" / "engine" / "kaggriculture.py"
        spec = importlib.util.spec_from_file_location("_sol_quoin_engine", engine_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        engine = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = engine
        spec.loader.exec_module(engine)

        def state_for(max_orders, rows):
            farms = [engine._new_farm(10, 1000), engine._new_farm(10, 1000)]
            privates = [engine._new_private(), engine._new_private()]
            privates[0]["shed"]["CARROT"] = 3
            market = engine._new_market()
            states = [
                SimpleNamespace(
                    action={"market": rows},
                    observation=SimpleNamespace(private=privates[0]),
                ),
                SimpleNamespace(
                    action={"market": []},
                    observation=SimpleNamespace(private=privates[1]),
                ),
            ]
            states[0].observation.market = market
            states[0].observation.farms = farms
            env = SimpleNamespace(configuration={
                "boardSize": 10,
                "maxMarketOrdersPerTurn": max_orders,
                "farmHandCostMult": 1,
                "shedCapacity": 4,
            })
            return states, env, privates

        states, env, privates = state_for(
            1, [[], ["BUY_ANIMAL", "GOOSE", 2]]
        )
        engine._process_market(states, env)
        self.assertEqual(privates[0]["shed"]["GOOSE"], 0)
        self.assertEqual(sum(privates[0]["shed"].values()), 3)

        states, env, privates = state_for(
            2, [[], ["BUY_ANIMAL", "GOOSE", 2]]
        )
        engine._process_market(states, env)
        self.assertEqual(privates[0]["shed"]["GOOSE"], 1)
        self.assertEqual(sum(privates[0]["shed"].values()), 4)


if __name__ == "__main__":
    unittest.main()
