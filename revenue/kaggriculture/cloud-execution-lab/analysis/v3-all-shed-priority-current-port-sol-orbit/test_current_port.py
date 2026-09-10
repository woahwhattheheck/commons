# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import bind_execution
import materialize
import screen

LAB = Path(__file__).resolve().parents[2]
ARCHIVE = LAB / "exports" / "titan-current.tar.gz"


class CurrentPortContracts(unittest.TestCase):
    def test_exact_canonical_archive_and_manifest(self):
        members, manifest, receipt = materialize.read_archive(ARCHIVE)
        self.assertEqual(receipt["sha256"], materialize.EXPECTED_ARCHIVE_SHA256)
        self.assertEqual(receipt["git_blob_sha1"], materialize.EXPECTED_ARCHIVE_GIT_BLOB)
        self.assertEqual(receipt["runtime_files"], materialize.EXPECTED_RUNTIME_FILES)
        self.assertEqual(manifest["entrypoint"], materialize.EXPECTED_ENTRYPOINT)
        self.assertIn("main.py", members)
        self.assertIn("scheduler.py", members)

    def test_materialization_changes_only_scheduler(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control = root / "control"
            candidate = root / "candidate"
            receipt = materialize.materialize(ARCHIVE, control, candidate)
            self.assertEqual(receipt["ablation"]["changed_files"], ["scheduler.py"])
            self.assertEqual(
                receipt["source"]["entry_sha256"],
                receipt["ablation"]["entry_sha256"],
            )
            self.assertNotEqual(
                receipt["source"]["closure_sha256"],
                receipt["ablation"]["closure_sha256"],
            )
            self.assertEqual(
                materialize.git_blob_sha1(control.joinpath("scheduler.py").read_bytes()),
                materialize.EXPECTED_SCHEDULER_GIT_BLOB,
            )

    def test_priority_preserves_domain_and_quantity(self):
        products = ("MILK", "EGG", "WOOL", "PORK")
        shed = {"MILK": 4, "EGG": 0, "WOOL": 7, "PORK": 2}
        control = materialize.control_targets(products=products, shed=shed)
        candidate = materialize.priority_targets(
            pending={"WOOL": 3, "UNKNOWN": 9},
            baseline_q={"PORK": 1, "WOOL": 2},
            products=products,
            shed=shed,
        )
        self.assertEqual(candidate, control)
        self.assertEqual(list(candidate), ["WOOL", "PORK", "MILK"])

    def test_priority_deduplicates_first_seen_intent(self):
        candidate = materialize.priority_targets(
            pending={"EGG": 1, "MILK": 1},
            baseline_q={"MILK": 2, "EGG": 2},
            products=("MILK", "EGG", "WOOL"),
            shed={"MILK": 3, "EGG": 4, "WOOL": 5},
        )
        self.assertEqual(list(candidate), ["EGG", "MILK", "WOOL"])
        self.assertEqual(candidate, {"EGG": 4, "MILK": 3, "WOOL": 5})

    def test_unsafe_archive_names_fail_closed(self):
        for name in ("../escape", "/absolute", "a\\b", "a/./b", "a//b"):
            with self.subTest(name=name):
                with self.assertRaises(materialize.MaterializeError):
                    materialize._safe_member_parts(name)

    def test_generated_wrapper_compiles_and_binds_current_main(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control = root / "control"
            candidate = root / "candidate"
            receipt = materialize.materialize(ARCHIVE, control, candidate)
            source = bind_execution._wrapper_source(
                label="control",
                root=control,
                expected_closure=receipt["source"]["closure_sha256"],
                git_head="1" * 40,
            )
            compile(source, "control_bound.py", "exec")
            self.assertIn(materialize.EXPECTED_ENTRY_SHA256, source)
            self.assertIn(str(control.resolve()), source)

    @staticmethod
    def _rows(*, changed=True, introduce_loss=False):
        rows = []
        first = True
        for opponent, seed, seat in sorted(screen.EXPECTED_KEYS):
            control_own = 100.0
            control_rival = 50.0
            candidate_own = control_own
            candidate_rival = control_rival
            action_changed = False
            if first and changed:
                candidate_own += 10.0
                action_changed = True
            if first and introduce_loss:
                control_own = 50.0
                control_rival = 50.0
                candidate_own = 49.0
                candidate_rival = 50.0
                action_changed = True
            rows.append(
                {
                    "opponent": opponent,
                    "seed": seed,
                    "seat": seat,
                    "own_delta": candidate_own - control_own,
                    "margin_delta": (
                        candidate_own
                        - candidate_rival
                        - (control_own - control_rival)
                    ),
                    "control_outcome": screen._outcome(control_own, control_rival),
                    "candidate_outcome": screen._outcome(
                        candidate_own, candidate_rival
                    ),
                    "candidate_action_changed": action_changed,
                }
            )
            first = False
        return rows

    def test_admission_accepts_nonnegative_strata_with_real_activation(self):
        result = screen.assess_rows(self._rows())
        self.assertEqual(result["verdict"], "ADMIT")
        self.assertTrue(all(result["gates"].values()))
        self.assertEqual(result["overall"]["candidate_action_changed_cells"], 1)

    def test_admission_rejects_no_action_activation(self):
        result = screen.assess_rows(self._rows(changed=False))
        self.assertEqual(result["verdict"], "REJECT")
        self.assertFalse(result["gates"]["candidate_action_activation"])

    def test_admission_rejects_new_loss(self):
        rows = self._rows(introduce_loss=True)
        # Add broad upside elsewhere so the new-loss gate, not only the mean,
        # is independently exercised.
        for row in rows[1:]:
            row["own_delta"] = 2.0
            row["margin_delta"] = 2.0
        result = screen.assess_rows(rows)
        self.assertEqual(result["verdict"], "REJECT")
        self.assertFalse(result["gates"]["zero_new_losses"])


if __name__ == "__main__":
    unittest.main()
