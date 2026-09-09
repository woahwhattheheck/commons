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
STRICT_PATH = (
    HERE.parent
    / "v2-forced-feasibility-ablation-sol-keel"
    / "materialize.py"
)
EXPECTED_STRICT_BLOB = "06515514ec864776f29571d63d3f343376e5865b"

import materialize as subject


class MaterializationContracts(unittest.TestCase):
    def test_exact_frozen_v2_changes_only_scheduler(self):
        source_before = _files(FROZEN_V2)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "candidate"
            receipt = subject.materialize(FROZEN_V2, output)
            self.assertEqual(receipt["operation"], subject.OPERATION)
            self.assertEqual(
                receipt["source"]["scheduler_git_blob_sha1"],
                subject.EXPECTED_V2_SCHEDULER_BLOB,
            )
            self.assertEqual(receipt["ablation"]["changed_files"], ["scheduler.py"])
            self.assertEqual(
                receipt["ablation"]["kind"], subject.COMPATIBLE_KIND
            )
            self.assertEqual(receipt["ablation"]["variant"], subject.VARIANT)
            self.assertNotEqual(
                receipt["source"]["closure_sha256"],
                receipt["ablation"]["closure_sha256"],
            )
            self.assertEqual(receipt["ablation"]["old_occurrences_before"], 1)
            self.assertEqual(receipt["ablation"]["old_occurrences_after"], 0)
            self.assertEqual(receipt["ablation"]["new_occurrences_before"], 0)
            self.assertEqual(receipt["ablation"]["new_occurrences_after"], 1)
            self.assertEqual(
                receipt["ablation"]["preserved_v2_markers"],
                {name: True for name in subject.PRESERVED_V2_MARKERS},
            )
            self.assertEqual(
                receipt["ablation"]["policy"]["rank"],
                ["positive_gain", "worst_relative_gain"],
            )
            self.assertIn(
                "v2-profit-first-forced-fallback/scheduler.py",
                receipt["ablation"]["unified_diff"],
            )
            self.assertEqual(_files(output).keys(), source_before.keys())
            for path, data in source_before.items():
                if path == "scheduler.py":
                    self.assertNotEqual(_files(output)[path], data)
                else:
                    self.assertEqual(_files(output)[path], data)
        self.assertEqual(_files(FROZEN_V2), source_before)

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

    def test_preserved_v2_features_and_forced_admission_remain_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "candidate"
            subject.materialize(FROZEN_V2, output)
            source = (output / "scheduler.py").read_text(encoding="utf-8")
            for name, marker in subject.PRESERVED_V2_MARKERS.items():
                with self.subTest(marker=name):
                    self.assertEqual(source.count(marker), 1)
            self.assertNotIn(subject.OLD, source)
            self.assertEqual(source.count(subject.NEW), 1)
            self.assertIn(
                "eligible=info['worst_relative_gain']>0 or "
                "info.get('forced_feasibility',False)",
                source,
            )

    def test_mixed_case_repairs_priority_without_deleting_fallback(self):
        choices = {
            "CARROT": (-5.0, True),
            "MILK": (1.0, False),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            strict = root / "strict"
            profit = root / "profit"
            _strict_materializer().materialize(FROZEN_V2, strict)
            subject.materialize(FROZEN_V2, profit)
            frozen_choice = _selected_product(
                FROZEN_V2, "forge_v2_frozen_mixed", choices
            )
            strict_choice = _selected_product(
                strict, "forge_v2_strict_mixed", choices
            )
            profit_choice = _selected_product(
                profit, "forge_v2_profit_mixed", choices
            )

        self.assertEqual(frozen_choice, "CARROT")
        self.assertEqual(strict_choice, "MILK")
        self.assertEqual(profit_choice, "MILK")

    def test_all_forced_case_retains_last_resort_feasible_repair(self):
        choices = {"CARROT": (-5.0, True)}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            strict = root / "strict"
            profit = root / "profit"
            _strict_materializer().materialize(FROZEN_V2, strict)
            subject.materialize(FROZEN_V2, profit)
            frozen_choice = _selected_product(
                FROZEN_V2, "forge_v2_frozen_forced_only", choices
            )
            strict_choice = _selected_product(
                strict, "forge_v2_strict_forced_only", choices
            )
            profit_choice = _selected_product(
                profit, "forge_v2_profit_forced_only", choices
            )

        self.assertEqual(frozen_choice, "CARROT")
        self.assertIsNone(strict_choice)
        self.assertEqual(profit_choice, "CARROT")

    def test_highest_value_forced_plan_wins_when_no_positive_exists(self):
        choices = {
            "CARROT": (-5.0, True),
            "MILK": (-1.0, True),
        }
        with tempfile.TemporaryDirectory() as directory:
            profit = Path(directory) / "profit"
            subject.materialize(FROZEN_V2, profit)
            choice = _selected_product(
                profit, "forge_v2_profit_best_forced", choices
            )
        self.assertEqual(choice, "MILK")

    def test_positive_forced_plan_ranks_by_value_not_flag(self):
        choices = {
            "CARROT": (2.0, True),
            "MILK": (1.0, False),
        }
        with tempfile.TemporaryDirectory() as directory:
            profit = Path(directory) / "profit"
            subject.materialize(FROZEN_V2, profit)
            choice = _selected_product(
                profit, "forge_v2_profit_positive_forced", choices
            )
        self.assertEqual(choice, "CARROT")


class FakeController:
    def __init__(self):
        self.cur = 0
        self.R = [[
            {"farmer": ["PASS"], "hands": [], "market": []}
            for _ in range(720)
        ]]

    def act(self, _observation):
        return {"farmer": ["PASS"], "hands": [], "market": []}


def _files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _strict_materializer() -> types.ModuleType:
    data = STRICT_PATH.read_bytes()
    actual = subject.git_blob_sha1(data)
    if actual != EXPECTED_STRICT_BLOB:
        raise AssertionError(
            f"strict materializer drift: expected {EXPECTED_STRICT_BLOB}, got {actual}"
        )
    spec = importlib.util.spec_from_file_location(
        "_sol_forge_exact_strict_materializer", STRICT_PATH
    )
    if spec is None or spec.loader is None:
        raise AssertionError("cannot import strict materializer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def _selected_product(
    root: Path,
    module_name: str,
    choices: dict[str, tuple[float, bool]],
) -> str | None:
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
        "shed": {item: 1 for item in choices},
        "seeds": {},
        "inventories": [],
    }
    module.post_units = lambda *_args, **_kwargs: (
        copy.deepcopy(farm),
        copy.deepcopy(private),
    )

    def fake_optimize(*, item, **_kwargs):
        gain, forced = choices[item]
        return (
            ((0, 1),),
            {
                "item": item,
                "plan": [(0, 1)],
                "worst_relative_gain": gain,
                "forced_feasibility": forced,
                "feasible": True,
                "reference_feasible": not forced,
            },
        )

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
            "inventory": {item: 1000 for item in choices},
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
    if len(sales) > 1:
        raise AssertionError(f"expected at most one selected sale, got {sales!r}")
    return None if not sales else str(sales[0][1])


if __name__ == "__main__":
    unittest.main()
