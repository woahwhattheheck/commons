# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

import materialize


SOURCE_TEMPLATE = """PRODUCTS = ('MILK', 'EGG')

class Quote:
    def single(self, inv, remaining):
        return (remaining * 10, inv)

    def carry_value(self, inv, remaining, terminal):
        carry=0.0
        if remaining and not terminal:
{carry}        return carry

def mapped_rival(rival, step, now):
    for step in (step,):
{rival}            return r

def scenarios_for(now, end, rival_quantity):
{base}{delayed}    return scenarios

def feasibility(reference, capacity_ok, now, minimum_now, key, best_key):
{reference_feasible}    found_feasible=reference_feasible
    for _ in (0,):
{forced_if}            found_feasible=True
    return found_feasible

def report_line(best_key, found_feasible, reference_feasible):
    return {{
{forced_report}    }}

def targets_for(shed):
    if True:
{targets}    return targets
"""


class MaterializeTests(unittest.TestCase):
    def source_tree(
        self,
        root: Path,
        *,
        delayed_copies: int = 1,
        carry: str | None = None,
    ) -> Path:
        source = root / "v2"
        (source / "reference" / "decision").mkdir(parents=True)
        scheduler = SOURCE_TEMPLATE.format(
            carry=carry if carry is not None else materialize.CARRY_SENTINEL,
            rival=materialize.RIVAL_MAPPING_SENTINEL,
            base=materialize.BASE_SCENARIOS,
            delayed=materialize.OLD * delayed_copies,
            reference_feasible=materialize.FORCED_SENTINELS[0],
            forced_if=materialize.FORCED_SENTINELS[1],
            forced_report=materialize.FORCED_SENTINELS[2],
            targets=materialize.TARGET_SENTINEL,
        )
        (source / "scheduler.py").write_text(scheduler, encoding="utf-8")
        (source / "candidate.py").write_text(
            "from scheduler import scenarios_for\n", encoding="utf-8"
        )
        (source / "reference" / "decision" / "receipt.txt").write_text(
            "unchanged\n", encoding="utf-8"
        )
        return source

    def test_one_factor_materialization_and_semantics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.source_tree(root)
            original = (source / "scheduler.py").read_bytes()
            output = root / "candidate"
            receipt = materialize.materialize(
                source,
                output,
                expected_scheduler_blob=materialize.git_blob_sha1(original),
            )
            self.assertEqual(receipt["ablation"]["changed_files"], ["scheduler.py"])
            self.assertEqual(
                receipt["ablation"]["removed_scenarios"],
                ["observed_next_turn", "observed_before_delayed_batch"],
            )
            self.assertTrue(all(receipt["ablation"]["retained_invariants"].values()))
            self.assertEqual((source / "scheduler.py").read_bytes(), original)
            self.assertEqual(
                (source / "candidate.py").read_bytes(),
                (output / "candidate.py").read_bytes(),
            )
            self.assertEqual(
                (source / "reference" / "decision" / "receipt.txt").read_bytes(),
                (output / "reference" / "decision" / "receipt.txt").read_bytes(),
            )
            spec = importlib.util.spec_from_file_location(
                "patched_scheduler", output / "scheduler.py"
            )
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
            self.assertEqual(
                [name for name, *_ in module.scenarios_for(5, 20, 7)],
                ["no_rival", "observed_paired", "observed_later_order"],
            )
            self.assertEqual(module.targets_for({"MILK": 4, "EGG": 0}), {"MILK": 4})

    def test_duplicate_bundle_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.source_tree(root, delayed_copies=2)
            expected = materialize.git_blob_sha1(
                (source / "scheduler.py").read_bytes()
            )
            with self.assertRaisesRegex(
                materialize.MaterializeError, "cardinality mismatch"
            ):
                materialize.materialize(
                    source, root / "candidate", expected_scheduler_blob=expected
                )

    def test_partial_bundle_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.source_tree(root)
            path = source / "scheduler.py"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "    if end>now+2:\n"
                    "        scenarios.append(('observed_before_delayed_batch',"
                    "((end-1,rival_quantity),),'paired'))\n",
                    "",
                ),
                encoding="utf-8",
            )
            expected = materialize.git_blob_sha1(path.read_bytes())
            with self.assertRaisesRegex(
                materialize.MaterializeError, "delayed-rival scenario bundle"
            ):
                materialize.materialize(
                    source, root / "candidate", expected_scheduler_blob=expected
                )

    def test_v1_carry_mutant_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.source_tree(
                root,
                carry="            carry=.95*self.single(inv,remaining)[0]\n",
            )
            expected = materialize.git_blob_sha1(
                (source / "scheduler.py").read_bytes()
            )
            with self.assertRaisesRegex(
                materialize.MaterializeError, "continuation value"
            ):
                materialize.materialize(
                    source, root / "candidate", expected_scheduler_blob=expected
                )

    def test_wrong_blob_fails_before_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.source_tree(root)
            output = root / "candidate"
            with self.assertRaisesRegex(
                materialize.MaterializeError, "blob mismatch"
            ):
                materialize.materialize(
                    source, output, expected_scheduler_blob="0" * 40
                )
            self.assertFalse(output.exists())

    def test_non_regular_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.source_tree(root)
            try:
                (source / "alias").symlink_to(source / "candidate.py")
            except (OSError, NotImplementedError):
                self.skipTest("symlinks are unavailable")
            with self.assertRaisesRegex(
                materialize.MaterializeError, "non-regular"
            ):
                materialize.materialize(
                    source,
                    root / "candidate",
                    expected_scheduler_blob=materialize.git_blob_sha1(
                        (source / "scheduler.py").read_bytes()
                    ),
                )


if __name__ == "__main__":
    unittest.main()
