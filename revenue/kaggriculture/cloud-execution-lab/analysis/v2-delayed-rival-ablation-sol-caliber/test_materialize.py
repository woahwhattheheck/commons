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
FROZEN_V1 = LAB / "runtime" / "variants" / "v1"
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
            self.assertEqual(
                receipt["ablation"]["kind"],
                "delayed_rival_stress_scenarios",
            )
            self.assertEqual(
                receipt["ablation"]["removed_scenario_names"],
                [
                    "observed_next_turn",
                    "observed_before_delayed_batch",
                ],
            )
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
            self.assertIn(
                "v2-delayed-rival-ablation/scheduler.py",
                receipt["ablation"]["unified_diff"],
            )

        source_after = {
            path.relative_to(FROZEN_V2).as_posix(): path.read_bytes()
            for path in FROZEN_V2.rglob("*")
            if path.is_file()
        }
        self.assertEqual(source_after, source_before)

    def test_ablation_restores_exact_v1_scenario_set_only(self):
        v1 = (FROZEN_V1 / "scheduler.py").read_text(encoding="utf-8")
        v2 = (FROZEN_V2 / "scheduler.py").read_text(encoding="utf-8")
        self.assertEqual(v1.count(subject.NEW), 1)
        self.assertNotIn(subject.OLD, v1)
        self.assertEqual(v2.count(subject.OLD), 1)

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

    def test_actual_market_path_exposes_delayed_scenario_veto(self):
        """Execute both exact schedulers; do not duplicate optimizer logic."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "candidate"
            subject.materialize(FROZEN_V2, output)
            frozen_plan, frozen_report = _optimize(
                FROZEN_V2,
                "v2_frozen_delayed_rival",
            )
            ablated_plan, ablated_report = _optimize(
                output,
                "v2_ablated_delayed_rival",
            )

        reference = ((542, 18), (550, 2))
        self.assertEqual(frozen_plan, reference)
        self.assertEqual(
            list(frozen_report["scenarios"]),
            [
                "no_rival",
                "observed_paired",
                "observed_later_order",
                "observed_next_turn",
                "observed_before_delayed_batch",
            ],
        )
        self.assertEqual(frozen_report["worst_relative_gain"], 0.0)

        self.assertEqual(ablated_plan, ((542, 13),))
        self.assertEqual(
            list(ablated_report["scenarios"]),
            [
                "no_rival",
                "observed_paired",
                "observed_later_order",
            ],
        )
        self.assertEqual(ablated_report["worst_relative_gain"], 1.0)
        gains = [
            scenario["relative_value"] - scenario["reference_relative_value"]
            for scenario in ablated_report["scenarios"].values()
        ]
        self.assertEqual(gains, [4.0, 1.0, 1.0])
        self.assertTrue(all(gain > 0 for gain in gains))


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
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = previous_path
        sys.modules.pop("mechanics", None)
        if old_mechanics is not None:
            sys.modules["mechanics"] = old_mechanics
    return module


def _optimize(root: Path, module_name: str):
    module = _load_scheduler(root, module_name)
    return module.optimize_lot(
        item="CARROT",
        quantity=20,
        inventory=10055,
        params=module.m.MARKET_PARAMS,
        shops=["PET_CAFE"],
        config={
            "townShopSellInterval": 4,
            "townCenterSellInterval": 24,
        },
        now=542,
        dates=[542, 546, 550],
        reference=((542, 18), (550, 2)),
        rival_quantity=3,
        minimum_now=0,
        capacity_ok=None,
        last=718,
    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
