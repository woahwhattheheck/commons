# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

import materialize as lane

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = HERE.parents[1] / "runtime" / "variants" / "v2"
CAPSULE = HERE / "step-639-decision-capsule.json"


def source_path() -> Path:
    return Path(os.environ.get("TITAN_V2_SOURCE", DEFAULT_SOURCE)).resolve()


def load_scheduler(root: Path, label: str):
    for name in ("mechanics", "intact_arlene", "pinned_receipt_math"):
        sys.modules.pop(name, None)
    sys.path.insert(0, str(root))
    try:
        spec = importlib.util.spec_from_file_location(label, root / "scheduler.py")
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot import scheduler from {root}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(root))


def capacity_predicate(capsule: dict):
    decision = capsule["decision"]
    profile = [tuple(row) for row in decision["receipt_profile"]]
    now = int(decision["observation_step"])
    limit = int(decision["capacity_limit"])

    def feasible(plan):
        sold = 0
        orders = dict(plan)
        for step, phase, total in profile:
            if phase == "after":
                sold += int(orders.get(step, 0))
            if step == now and phase == "before":
                continue
            if int(total) - sold > limit:
                return False
        return True

    return feasible


def optimize(module, capsule: dict, feasible):
    d = capsule["decision"]
    return module.optimize_lot(
        item=d["item"],
        quantity=int(d["quantity"]),
        inventory=int(d["market_inventory"]),
        params=d["market_params"],
        shops=d["unlocked_shops"],
        config=d["config"],
        now=int(d["observation_step"]),
        dates=d["dates"],
        reference=tuple(tuple(row) for row in d["reference"]),
        rival_quantity=int(d["rival_quantity"]),
        minimum_now=int(d["minimum_now"]),
        capacity_ok=feasible,
        last=int(d["last"]),
    )


class MechanismTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capsule = json.loads(CAPSULE.read_text(encoding="utf-8"))
        cls.source = load_scheduler(source_path(), "sol_interstice_source_scheduler")
        cls.temporary = tempfile.TemporaryDirectory()
        cls.candidate_root = Path(cls.temporary.name) / "candidate"
        cls.receipt = lane.materialize(source_path(), cls.candidate_root)
        cls.candidate = load_scheduler(
            cls.candidate_root, "sol_interstice_candidate_scheduler"
        )

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_step_639_capsule_kills_predecessor_and_selects_minimum_repair(self):
        feasible = capacity_predicate(self.capsule)
        source_plan, source_info = optimize(self.source, self.capsule, feasible)
        candidate_plan, candidate_info = optimize(self.candidate, self.capsule, feasible)
        expected = self.capsule["expected"]

        self.assertEqual([list(row) for row in source_plan], expected["predecessor_plan"])
        self.assertEqual([list(row) for row in candidate_plan], expected["repair_plan"])
        self.assertEqual(source_info["plans_evaluated"], 170)
        self.assertEqual(candidate_info["plans_evaluated"], 173)
        self.assertEqual(candidate_info["selected_units_sold"], 14)
        self.assertEqual(candidate_info["selected_units_carried"], 10)
        self.assertTrue(source_info["forced_feasibility"])
        self.assertTrue(candidate_info["forced_feasibility"])
        self.assertEqual(source_info["worst_relative_gain"], 0.0)
        self.assertEqual(candidate_info["worst_relative_gain"], 0.0)
        boundaries = json.loads(json.dumps(candidate_info["capacity_boundary_plans"]))
        self.assertEqual(
            boundaries,
            [
                [[639, 0], [641, 14]],
                [[639, 0], [645, 14]],
                [[639, 0], [647, 14]],
            ],
        )

    def test_exact_guard_requires_14_not_raw_overflow_13(self):
        feasible = capacity_predicate(self.capsule)
        self.assertFalse(feasible(((639, 0), (645, 13))))
        self.assertTrue(feasible(((639, 0), (645, 14))))
        self.assertEqual(
            self.capsule["decision"]["uncapped_total_after_drop"]
            - self.capsule["decision"]["config"]["shedCapacity"],
            13,
        )

    def test_arbitrary_nonmonotone_executable_predicate_returns_first_true(self):
        def executable(plan):
            quantity = sum(q for _step, q in plan)
            return 14 <= quantity <= 20

        plan = self.candidate._minimum_partial_future_plan(
            now=639,
            first=0,
            date=645,
            remaining=24,
            capacity_ok=executable,
        )
        self.assertEqual(plan, ((639, 0), (645, 14)))

    def test_no_boundary_candidates_when_reference_is_feasible(self):
        always = lambda _plan: True
        source_plan, source_info = optimize(self.source, self.capsule, always)
        candidate_plan, candidate_info = optimize(self.candidate, self.capsule, always)
        self.assertEqual(candidate_plan, source_plan)
        self.assertEqual(candidate_info["plans_evaluated"], source_info["plans_evaluated"])
        self.assertEqual(candidate_info["capacity_boundary_plans"], [])

    def test_scheduled_tranches_are_consumed_once(self):
        planned = {
            "STRAWBERRY": [(645, 14), (647, 3)],
            "MILK": [(640, 2)],
            "EGG": [(648, 1)],
        }
        due, future = self.candidate._consume_due_plans(planned, 645)
        self.assertEqual(due, {"STRAWBERRY": 14, "MILK": 2, "EGG": 0})
        self.assertEqual(future, {"STRAWBERRY": [(647, 3)], "EGG": [(648, 1)]})
        self.assertEqual(
            planned,
            {
                "STRAWBERRY": [(645, 14), (647, 3)],
                "MILK": [(640, 2)],
                "EGG": [(648, 1)],
            },
        )

    def test_candidate_is_exactly_the_materialized_scheduler(self):
        scheduler = (self.candidate_root / "scheduler.py").read_bytes()
        self.assertEqual(lane.git_blob_sha1(scheduler), lane.EXPECTED_PATCHED_SCHEDULER_BLOB)
        self.assertEqual(lane.sha256(scheduler), lane.EXPECTED_PATCHED_SCHEDULER_SHA256)
        self.assertEqual(
            self.receipt["candidate"]["closure_sha256"],
            "4cc914ec132ffd6986bee072f6952c19cc8119f20e404ab15633af16da4cf7c1",
        )


if __name__ == "__main__":
    unittest.main()
