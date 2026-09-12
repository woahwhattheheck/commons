# SPDX-License-Identifier: Apache-2.0
"""Contracts for the V2 all-shed intent-priority one-factor arm."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest

import materialize as base
import materialize_priority as priority


HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
FROZEN_V2 = LAB / "runtime" / "variants" / "v2"
PRODUCTS = (
    "CARROT",
    "TOMATO",
    "STRAWBERRY",
    "MELON",
    "EGG",
    "MILK",
    "WOOL",
)


class PriorityMapTests(unittest.TestCase):
    def test_domain_and_quantities_are_byte_semantics_equivalent(self) -> None:
        shed = {
            "CARROT": 0,
            "TOMATO": 7,
            "STRAWBERRY": 2,
            "MELON": 9,
            "EGG": 4,
            "MILK": 3,
            "WOOL": 8,
            "WHEAT": 99,
            "FERTILIZER": 99,
        }
        pending = {"EGG": 900, "UNKNOWN": 1, "TOMATO": 2}
        baseline = {"MILK": 3, "EGG": 4, "WHEAT": 99}

        control = priority.control_targets(
            products=PRODUCTS,
            shed=shed,
        )
        candidate = priority.priority_targets(
            pending=pending,
            baseline_q=baseline,
            products=PRODUCTS,
            shed=shed,
        )

        self.assertEqual(candidate, control)
        self.assertEqual(
            list(candidate),
            ["EGG", "TOMATO", "MILK", "STRAWBERRY", "MELON", "WOOL"],
        )
        self.assertEqual(sum(candidate.values()), sum(control.values()))

    def test_duplicate_intent_keeps_earliest_pending_position(self) -> None:
        candidate = priority.priority_targets(
            pending={"WOOL": 1, "MILK": 1},
            baseline_q={"MILK": 99, "WOOL": 99, "EGG": 1},
            products=PRODUCTS,
            shed={product: 1 for product in PRODUCTS},
        )
        self.assertEqual(
            list(candidate),
            [
                "WOOL",
                "MILK",
                "EGG",
                "CARROT",
                "TOMATO",
                "STRAWBERRY",
                "MELON",
            ],
        )

    def test_no_intent_is_exact_products_order(self) -> None:
        shed = {product: index + 1 for index, product in enumerate(PRODUCTS)}
        candidate = priority.priority_targets(
            pending={},
            baseline_q={},
            products=PRODUCTS,
            shed=shed,
        )
        self.assertEqual(list(candidate), list(PRODUCTS))
        self.assertEqual(
            candidate,
            priority.control_targets(products=PRODUCTS, shed=shed),
        )

    def test_stale_and_operating_keys_cannot_expand_target_domain(self) -> None:
        candidate = priority.priority_targets(
            pending={"WHEAT": 1, "STALE": 1},
            baseline_q={"FERTILIZER": 1, "UNKNOWN": 1},
            products=PRODUCTS,
            shed={
                "WHEAT": 50,
                "FERTILIZER": 50,
                "STALE": 50,
                "UNKNOWN": 50,
                "MILK": 2,
            },
        )
        self.assertEqual(candidate, {"MILK": 2})

    def test_zero_or_negative_shed_items_remain_absent(self) -> None:
        candidate = priority.priority_targets(
            pending={"EGG": 1, "MILK": 1},
            baseline_q={"WOOL": 1},
            products=PRODUCTS,
            shed={"EGG": 0, "MILK": -4, "WOOL": 3},
        )
        self.assertEqual(candidate, {"WOOL": 3})


class ExactMaterializationTests(unittest.TestCase):
    def test_exact_frozen_v2_changes_only_scheduler(self) -> None:
        before = base.inventory(FROZEN_V2)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "candidate"
            receipt = priority.materialize(FROZEN_V2, output)

            self.assertEqual(receipt["experiment"], priority.EXPERIMENT)
            self.assertEqual(
                receipt["source"]["scheduler_git_blob_sha1"],
                base.EXPECTED_V2_SCHEDULER_BLOB,
            )
            self.assertEqual(
                receipt["ablation"]["changed_files"],
                ["scheduler.py"],
            )
            self.assertEqual(
                receipt["ablation"]["old_occurrences_before"],
                1,
            )
            self.assertEqual(
                receipt["ablation"]["old_occurrences_after"],
                0,
            )
            self.assertEqual(
                receipt["ablation"]["new_occurrences_before"],
                0,
            )
            self.assertEqual(
                receipt["ablation"]["new_occurrences_after"],
                1,
            )

            after = base.inventory(output)
            self.assertEqual(set(after), set(before))
            changed = [
                name
                for name in sorted(before)
                if before[name]["sha256"] != after[name]["sha256"]
            ]
            self.assertEqual(changed, ["scheduler.py"])
            patched = (output / "scheduler.py").read_text(encoding="utf-8")
            self.assertEqual(patched.count(priority.OLD), 0)
            self.assertEqual(patched.count(priority.NEW), 1)
            compile(patched, str(output / "scheduler.py"), "exec")

        self.assertEqual(base.inventory(FROZEN_V2), before)

    def test_source_blob_drift_fails_before_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "candidate"
            shutil.copytree(FROZEN_V2, source)
            with (source / "scheduler.py").open(
                "a",
                encoding="utf-8",
                newline="\n",
            ) as handle:
                handle.write("\n# drift\n")

            with self.assertRaisesRegex(
                base.MaterializeError,
                "scheduler blob mismatch",
            ):
                priority.materialize(source, output)
            self.assertFalse(output.exists())

    def test_expression_cardinality_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "candidate"
            shutil.copytree(FROZEN_V2, source)
            scheduler = source / "scheduler.py"
            data = scheduler.read_bytes().replace(
                priority.OLD.encode("utf-8"),
                b"        targets={}\n",
                1,
            )
            scheduler.write_bytes(data)
            expected = base.git_blob_sha1(data)

            with self.assertRaisesRegex(
                base.MaterializeError,
                "exactly one frozen V2 target expression",
            ):
                priority.materialize(
                    source,
                    output,
                    expected_scheduler_blob=expected,
                )
            self.assertFalse(output.exists())

    def test_output_inside_source_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            base.MaterializeError,
            "nested inside source",
        ):
            priority.materialize(
                FROZEN_V2,
                FROZEN_V2 / "_forbidden_priority_candidate",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
