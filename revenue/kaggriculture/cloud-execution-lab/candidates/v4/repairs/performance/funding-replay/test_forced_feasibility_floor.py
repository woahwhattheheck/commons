# SPDX-License-Identifier: Apache-2.0
"""Focused current-ABI contracts for the TITAN #12096 economic floor."""
from __future__ import annotations

import ast
import copy
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[4]

sys.path.insert(0, str(HERE))
import apply_forced_feasibility_floor as floor  # noqa: E402


def _exec_function(source: str, name: str, namespace: dict):
    tree = ast.parse(source)
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(nodes) != 1:
        raise AssertionError(f"expected one {name}, found {len(nodes)}")
    module = ast.Module(body=[copy.deepcopy(nodes[0])], type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, f"<{name}>", "exec"), namespace)
    return namespace[name]


class FakePath:
    def __init__(self, candidate_score):
        self.candidate_score = candidate_score

    def score(self, plan, quantity, rival, alignment, terminal=False):
        if tuple(plan) == ((0, 0),):
            return (10.0, 10.0, 0.0, 0)
        return self.candidate_score


def _run_scheduler_optimize(source: str, candidate_score):
    ns = {"MarketPath": lambda *args, **kwargs: FakePath(candidate_score)}
    optimize = _exec_function(source, "optimize_lot", ns)
    return optimize(
        item="CARROT",
        quantity=1,
        inventory=100,
        params={},
        shops=[],
        config={},
        now=0,
        dates=[0],
        reference=((0, 0),),
        rival_quantity=0,
        minimum_now=0,
        capacity_ok=lambda plan: tuple(plan) != ((0, 0),),
        last=718,
    )


def _run_selected_optimize(source: str, candidate_score):
    ns = {
        "shared_market_path": lambda *args, **kwargs: FakePath(candidate_score),
        "_acceptance_rule": lambda config: "strict",
        "_scenario_weights": lambda names, config: {name: 1.0 / len(names) for name in names},
        "_weighted_gain": lambda deltas, names, weights: sum(
            float(delta) * float(weights[name]) for name, delta in zip(names, deltas)
        ),
    }
    optimize = _exec_function(source, "optimize_lot", ns)
    return optimize(
        item="CARROT",
        quantity=1,
        inventory=100,
        params={},
        shops=[],
        config={},
        now=0,
        dates=[0],
        reference=((0, 0),),
        rival_quantity=0,
        minimum_now=0,
        capacity_ok=lambda plan: tuple(plan) != ((0, 0),),
        last=718,
    )


class ForcedFeasibilityEconomicFloor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = {
            "scheduler": LAB / "scheduler.py",
            "selected_sell_core": LAB / "selected_sell_core.py",
            "frozen_selected": LAB / "frozen_selected.py",
        }
        cls.raw = {name: path.read_bytes() for name, path in cls.paths.items()}
        for name, raw in cls.raw.items():
            observed = floor.git_blob(raw)
            expected = floor.EXPECTED_BLOBS[name]
            if observed != expected:
                raise AssertionError(f"{name} source drift: {observed} != {expected}")
        cls.source = {name: raw.decode("utf-8") for name, raw in cls.raw.items()}
        cls.repaired = {
            "scheduler": floor.transform_scheduler(cls.source["scheduler"]),
            "selected_sell_core": floor.transform_selected_sell_core(cls.source["selected_sell_core"]),
            "frozen_selected": floor.transform_frozen_selected(cls.source["frozen_selected"]),
        }

    def test_current_source_generation_is_exact_and_source_only(self):
        self.assertEqual(
            floor.RECONSTRUCTED_SCHEDULER_EDGE,
            {
                "funding_capacity_output": "eb289f87adebb7dc7e90046bfbec31a307cb5aaa",
                "scoped_construction_output": "b29d1e9887f517506c5b3d858baa9bda5848e73f",
            },
        )
        for name in self.source:
            self.assertNotEqual(self.repaired[name], self.source[name])
            compile(self.repaired[name], name, "exec")
            self.assertEqual(self.paths[name].read_bytes(), self.raw[name])

    def test_forced_negative_relative_candidate_is_rejected_on_both_optimizers(self):
        for name, runner in (
            ("scheduler", _run_scheduler_optimize),
            ("selected_sell_core", _run_selected_optimize),
        ):
            _plan, info = runner(self.repaired[name], (9.0, 9.0, 0.0, 0))
            self.assertFalse(info["feasible"], name)
            self.assertFalse(info["forced_feasibility"], name)
            self.assertTrue(info["physical_feasible_found"], name)
            self.assertGreater(info["economic_floor_rejections"], 0, name)

    def test_forced_negative_own_candidate_is_rejected_even_at_relative_zero(self):
        for name, runner in (
            ("scheduler", _run_scheduler_optimize),
            ("selected_sell_core", _run_selected_optimize),
        ):
            _plan, info = runner(self.repaired[name], (10.0, 9.0, -1.0, 0))
            self.assertFalse(info["feasible"], name)
            self.assertFalse(info["forced_feasibility"], name)
            self.assertEqual(info["worst_relative_gain"], 0.0, name)
            self.assertGreater(info["economic_floor_rejections"], 0, name)

    def test_value_neutral_forced_rescue_is_admitted(self):
        for name, runner in (
            ("scheduler", _run_scheduler_optimize),
            ("selected_sell_core", _run_selected_optimize),
        ):
            plan, info = runner(self.repaired[name], (10.0, 10.0, 0.0, 0))
            self.assertEqual(tuple(plan), ((0, 1),), name)
            self.assertTrue(info["feasible"], name)
            self.assertTrue(info["forced_feasibility"], name)
            self.assertEqual(info["worst_relative_gain"], 0.0, name)
            self.assertEqual(info["worst_own_gain"], 0.0, name)

    def test_forced_boolean_cannot_outrank_positive_ordinary_gain(self):
        ranker = _exec_function(self.repaired["frozen_selected"], "seller_choice_rank", {})
        forced_zero = {
            "forced_feasibility": True,
            "worst_relative_gain": 0.0,
            "worst_own_gain": 0.0,
        }
        ordinary_positive = {
            "forced_feasibility": False,
            "accepted": True,
            "worst_relative_gain": 0.25,
            "acceptance_score": 0.25,
        }
        forced_bad_relative = {
            "forced_feasibility": True,
            "worst_relative_gain": -0.01,
            "worst_own_gain": 1.0,
        }
        forced_bad_own = {
            "forced_feasibility": True,
            "worst_relative_gain": 0.0,
            "worst_own_gain": -0.01,
        }
        self.assertTrue(ranker(forced_zero)[0])
        self.assertTrue(ranker(ordinary_positive)[0])
        self.assertGreater(ranker(ordinary_positive)[1], ranker(forced_zero)[1])
        self.assertFalse(ranker(forced_bad_relative)[0])
        self.assertFalse(ranker(forced_bad_own)[0])

    def test_materializer_rejects_source_drift_and_existing_output(self):
        with tempfile.TemporaryDirectory(prefix="v4-floor-test-") as tmp:
            root = Path(tmp)
            bad = root / "scheduler.py"
            bad.write_bytes(self.raw["scheduler"] + b"\n# drift\n")
            out = root / "out.py"
            with self.assertRaisesRegex(ValueError, "source Git blob drifted"):
                floor.materialize("scheduler", bad, out)
            self.assertFalse(out.exists())

            good = root / "good.py"
            good.write_bytes(self.raw["scheduler"])
            out.write_text("occupied", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                floor.materialize("scheduler", good, out)


if __name__ == "__main__":
    unittest.main()
