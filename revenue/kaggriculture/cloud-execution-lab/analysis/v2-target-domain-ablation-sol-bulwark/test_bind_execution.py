# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import bind_execution
from execution_test_support import HEAD, make_fixture


_IMPORT_SCRIPT = r"""
import importlib.util
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("_bound_test_module", path)
if spec is None or spec.loader is None:
    raise RuntimeError(path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
print(json.dumps(module.agent({}, {}), sort_keys=True))
"""


def run_wrapper(path: Path) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-B", "-c", _IMPORT_SCRIPT, str(path)],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )


class ExecutionBindingTests(unittest.TestCase):
    def test_distinct_wrappers_execute_their_bound_closures(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            binding = fixture["binding"]

            self.assertNotEqual(
                binding["arms"]["control"]["closure_sha256"],
                binding["arms"]["candidate"]["closure_sha256"],
            )
            self.assertNotEqual(
                binding["arms"]["control"]["wrapper"]["sha256"],
                binding["arms"]["candidate"]["wrapper"]["sha256"],
            )
            control = run_wrapper(fixture["control_wrapper"])
            candidate = run_wrapper(fixture["candidate_wrapper"])
            self.assertEqual(control.returncode, 0, control.stderr)
            self.assertEqual(candidate.returncode, 0, candidate.stderr)
            self.assertEqual(json.loads(control.stdout), {"arm": "control"})
            self.assertEqual(json.loads(candidate.stdout), {"arm": "candidate"})

    def test_wrapper_rejects_tree_mutation_after_binding(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            with (fixture["candidate_root"] / "scheduler.py").open(
                "a",
                encoding="utf-8",
            ) as handle:
                handle.write("# drift\n")

            result = run_wrapper(fixture["candidate_wrapper"])
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("bound closure mismatch", result.stderr)

    def test_builder_rejects_tree_drift_before_wrapper_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = make_fixture(Path(temporary))
            shutil.rmtree(fixture["output_dir"])
            with (fixture["candidate_root"] / "scheduler.py").open(
                "a",
                encoding="utf-8",
            ) as handle:
                handle.write("# drift\n")

            with self.assertRaisesRegex(
                bind_execution.BindingError,
                "candidate root does not match",
            ):
                bind_execution.build_binding(
                    control_root=fixture["control_root"],
                    candidate_root=fixture["candidate_root"],
                    materialization_receipt=fixture["receipt"],
                    engine_dir=fixture["engine_dir"],
                    loader=fixture["loader"],
                    evaluator=fixture["evaluator"],
                    opponents=fixture["opponents"],
                    output_dir=fixture["output_dir"],
                    git_head=HEAD,
                )


if __name__ == "__main__":
    unittest.main()
