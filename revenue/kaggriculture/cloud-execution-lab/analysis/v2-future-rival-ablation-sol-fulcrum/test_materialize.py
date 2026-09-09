# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import materialize as target

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / "runtime" / "variants" / "v2"
HEAD = "1" * 40


class MaterializeTests(unittest.TestCase):
    def test_frozen_source_and_scenario_identity(self):
        report = target.verify_frozen_source(SOURCE)
        self.assertEqual(target.SCHEDULER_GIT_BLOB, report["scheduler_git_blob"])
        source = (SOURCE / "scheduler.py").read_text(encoding="utf-8")
        self.assertEqual(target.V2_SCENARIOS, target.scenario_names(source))

    def test_control_and_ablation_are_exactly_one_factor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control = target.materialize(
                SOURCE, root / "control", "control", root / "control.json", HEAD
            )
            ablation = target.materialize(
                SOURCE, root / "ablation", "ablation", root / "ablation.json", HEAD
            )
            self.assertEqual([], control["materialized"]["changed_paths"])
            self.assertEqual(["scheduler.py"], ablation["materialized"]["changed_paths"])
            self.assertEqual(
                control["source"]["runtime_closure_sha256"],
                control["materialized"]["runtime_closure_sha256"],
            )
            self.assertNotEqual(
                control["materialized"]["runtime_closure_sha256"],
                ablation["materialized"]["runtime_closure_sha256"],
            )
            self.assertEqual(
                list(target.ABLATION_SCENARIOS),
                ablation["materialized"]["scenario_names"],
            )
            self.assertIn("observed_next_turn", ablation["patch"]["unified_diff"])
            self.assertIn("observed_before_delayed_batch", ablation["patch"]["unified_diff"])

    def test_generated_entry_binds_runtime_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target.materialize(
                SOURCE, root / "arm", "ablation", root / "receipt.json", HEAD
            )
            entry = root / "arm" / "entry.py"
            code = (
                "import importlib.util; "
                f"p={str(entry)!r}; "
                "s=importlib.util.spec_from_file_location('fulcrum_entry',p); "
                "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
                "assert callable(m.agent)"
            )
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            good = subprocess.run(
                [sys.executable, "-B", "-c", code],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertEqual(0, good.returncode, good.stderr)
            scheduler = root / "arm" / "runtime" / "scheduler.py"
            scheduler.write_bytes(scheduler.read_bytes() + b"\n")
            bad = subprocess.run(
                [sys.executable, "-B", "-c", code],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            self.assertNotEqual(0, bad.returncode)
            self.assertIn("inventory does not match", bad.stderr)

    def test_patch_rejects_missing_or_duplicate_preimage(self):
        source = (SOURCE / "scheduler.py").read_text(encoding="utf-8")
        with self.assertRaisesRegex(target.MaterializeError, "found 0"):
            target.patch_scheduler(source.replace(target.FUTURE_SCENARIO_BLOCK, ""))
        with self.assertRaisesRegex(target.MaterializeError, "found 2"):
            target.patch_scheduler(source + target.FUTURE_SCENARIO_BLOCK)

    def test_output_must_be_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "occupied"
            output.mkdir()
            (output / "peer.txt").write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(target.MaterializeError, "output must"):
                target.materialize(SOURCE, output, "control", root / "r.json", HEAD)
            self.assertEqual("preserve", (output / "peer.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
