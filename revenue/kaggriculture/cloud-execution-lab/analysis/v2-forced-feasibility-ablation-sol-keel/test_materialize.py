from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
FROZEN_V2 = LAB / "runtime" / "variants" / "v2"

import materialize as subject


class MaterializationContracts(unittest.TestCase):
    def test_exact_frozen_v2_changes_only_scheduler(self):
        source_before = {
            path.relative_to(FROZEN_V2).as_posix(): path.read_bytes()
            for path in FROZEN_V2.rglob("*")
            if path.is_file()
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "candidate"
            receipt = subject.materialize(FROZEN_V2, output)

            self.assertEqual(receipt["operation"], subject.OPERATION)
            self.assertEqual(
                receipt["source"]["scheduler_git_blob_sha1"],
                subject.EXPECTED_V2_SCHEDULER_BLOB,
            )
            self.assertEqual(receipt["ablation"]["changed_files"], ["scheduler.py"])
            self.assertNotEqual(
                receipt["source"]["closure_sha256"],
                receipt["ablation"]["closure_sha256"],
            )
            self.assertEqual(
                receipt["ablation"]["old_occurrences_before"], 1
            )
            self.assertEqual(receipt["ablation"]["old_occurrences_after"], 0)
            self.assertEqual(receipt["ablation"]["new_occurrences_before"], 0)
            self.assertEqual(receipt["ablation"]["new_occurrences_after"], 1)
            self.assertEqual(
                receipt["ablation"]["preserved_v2_markers"],
                {name: True for name in subject.PRESERVED_V2_MARKERS},
            )
            self.assertIn(
                "v2-forced-feasibility-ablation/scheduler.py",
                receipt["ablation"]["unified_diff"],
            )

        source_after = {
            path.relative_to(FROZEN_V2).as_posix(): path.read_bytes()
            for path in FROZEN_V2.rglob("*")
            if path.is_file()
        }
        self.assertEqual(source_after, source_before)

    def test_wrong_frozen_blob_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(subject.MaterializeError):
                subject.materialize(
                    FROZEN_V2,
                    Path(directory) / "candidate",
                    expected_scheduler_blob="0" * 40,
                )

    def test_duplicate_replacement_needle_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            output = root / "candidate"
            shutil.copytree(FROZEN_V2, source)
            scheduler = source / "scheduler.py"
            duplicated = scheduler.read_bytes() + subject.OLD.encode("utf-8")
            scheduler.write_bytes(duplicated)
            with self.assertRaises(subject.MaterializeError):
                subject.materialize(
                    source,
                    output,
                    expected_scheduler_blob=subject.git_blob_sha1(duplicated),
                )

    def test_preserved_v2_features_remain_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "candidate"
            subject.materialize(FROZEN_V2, output)
            source = (output / "scheduler.py").read_text(encoding="utf-8")
            for name, marker in subject.PRESERVED_V2_MARKERS.items():
                with self.subTest(marker=name):
                    self.assertEqual(source.count(marker), 1)
            self.assertNotIn(subject.OLD, source)
            self.assertEqual(source.count(subject.NEW), 1)

    def test_actual_source_priority_inversion_is_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "candidate"
            subject.materialize(FROZEN_V2, output)
            frozen_choice = _selected_product(FROZEN_V2, "v2_frozen_priority")
            repaired_choice = _selected_product(output, "v2_strict_priority")

        self.assertEqual(frozen_choice, "CARROT")
        self.assertEqual(repaired_choice, "MILK")


class FakeController:
    def __init__(self):
        self.cur = 0
        self.R = [
            {"farmer": ["PASS"], "hands": [], "market": []}
            for _ in range(720)
        ]

    def act(self, _observation):
        return {"farmer": ["PASS"], "hands": [], "market": []}


def _load_scheduler(root: Path, module_name: str) -> types.ModuleType:
    scheduler_path = root / "scheduler.py"
    spec = importlib.util.spec_from_file_location(module_name, scheduler_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot import {scheduler_path}")
    module = importlib.util.module_from_spec(spec)
    previous_path = list(sys.path)
    old_mechanics = sys.modules.pop("mechanics", None)
    try:
        sys.path.insert(0, str(root))
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = previous_path
        if old_mechanics is not None:
            sys.modules["mechanics"] = old_mechanics
        else:
            sys.modules.pop("mechanics", None)
    return module


def _selected_product(root: Path, module_name: str) -> str:
    module = _load_scheduler(root, module_name)
    module.parent.Agent = FakeController
    module.parent.DECISIONS = []
    module.absorption = lambda *_args, **_kwargs: 1

    farm = {
        "money": 100,
        "hires_today": 0,
        "unlocked_quadrants": [0],
        "tiles": [],
        "hands": [],
    }
    private = {
        "shed": {"CARROT": 1, "MILK": 1},
        "seeds": {},
        "inventories": [],
    }
    module.post_units = lambda *_args, **_kwargs: (
        copy.deepcopy(farm),
        copy.deepcopy(private),
    )

    def fake_optimize(*, item, **_kwargs):
        if item == "CARROT":
            return (
                ((0, 1),),
                {
                    "item": item,
                    "plan": [(0, 1)],
                    "worst_relative_gain": -5.0,
                    "forced_feasibility": True,
                },
            )
        if item == "MILK":
            return (
                ((0, 1),),
                {
                    "item": item,
                    "plan": [(0, 1)],
                    "worst_relative_gain": 1.0,
                    "forced_feasibility": False,
                },
            )
        raise AssertionError(f"unexpected target: {item}")

    module.optimize_lot = fake_optimize
    policy = module.SellScheduler()
    policy.cash_reserve = lambda *_args, **_kwargs: 0
    policy.receipt_profile = (
        lambda *_args, **_kwargs: (lambda _plan: True)
    )
    policy.rival_supply = lambda *_args, **_kwargs: 0

    observation = {
        "step": 0,
        "player": 0,
        "farms": [{}, {}],
        "private": copy.deepcopy(private),
        "market": {
            "inventory": {"CARROT": 1000, "MILK": 1000},
            "params": None,
        },
        "town": {"unlocked_shops": []},
    }
    action = policy.act(
        observation,
        {
            "episodeSteps": 720,
            "turnsPerDay": 24,
            "shedCapacity": 100,
            "maxMarketOrdersPerTurn": 10,
        },
    )
    sales = [
        row
        for row in action["market"]
        if row and row[0] == "SELL" and int(row[2]) > 0
    ]
    if len(sales) != 1:
        raise AssertionError(f"expected one selected sale, got {sales!r}")
    return str(sales[0][1])


if __name__ == "__main__":
    unittest.main()
