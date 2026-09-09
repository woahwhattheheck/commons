# SPDX-License-Identifier: Apache-2.0
"""Prove evaluator-shaped loading and candidate-local import fail-closure."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
MODULE_NAMES = (
    "_titan_granary_entrypoint_test",
    "_titan_granary_parent",
    "_titan_granary_runtime",
    "_titan_granary_aggregate",
)


class EntrypointLoadTests(unittest.TestCase):
    def _exercise(self, *, broken_runtime=False):
        previous_modules = {name: sys.modules.get(name) for name in MODULE_NAMES}
        original_path = list(sys.path)
        try:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "cloud-execution-lab"
                candidate = root / "candidates" / "v3-aggregate-seed-budget"
                candidate.mkdir(parents=True)
                shutil.copy2(HERE / "main.py", candidate / "main.py")
                shutil.copy2(HERE / "aggregate_seed_budget.py", candidate / "aggregate_seed_budget.py")
                if broken_runtime:
                    (candidate / "candidate_runtime.py").write_text(
                        "raise RuntimeError('broken candidate runtime')\n", encoding="utf-8")
                else:
                    shutil.copy2(HERE / "candidate_runtime.py", candidate / "candidate_runtime.py")

                parent = (
                    "CALLS = 0\n"
                    "class Features:\n"
                    "    budget_seconds = 1.0\n"
                    "    reserve_seconds = 0.01\n"
                    "class Instance:\n"
                    "    features = Features()\n"
                    "    diagnostics = {}\n"
                    "_INSTANCE = Instance()\n"
                    "def agent(observation, configuration=None):\n"
                    "    global CALLS\n"
                    "    CALLS += 1\n"
                    "    return {'farmer':['PASS'],'hands':[],'market':[]}\n"
                )
                (root / "main.py").write_text(parent, encoding="utf-8")

                self.assertNotIn(str(candidate), sys.path)
                spec = importlib.util.spec_from_file_location(
                    "_titan_granary_entrypoint_test", candidate / "main.py")
                self.assertIsNotNone(spec)
                self.assertIsNotNone(spec.loader)
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)
                result = module.agent({"step": 0, "player": 0}, {})
                self.assertEqual(result, {"farmer": ["PASS"], "hands": [], "market": []})
                self.assertEqual(module._PARENT.CALLS, 1)
                self.assertNotIn(str(candidate), sys.path)
                return module
        finally:
            sys.path[:] = original_path
            for name, value in previous_modules.items():
                if value is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = value

    def test_path_bound_siblings_and_single_parent_call(self):
        module = self._exercise()
        # The canonical test parent does not publish titan_runtime, so a loaded
        # candidate reaches the explicit deadline fail-closed boundary.
        self.assertEqual(
            module._PARENT._INSTANCE.diagnostics["aggregate_seed_budget"]["reason"],
            "deadline_guard_unavailable",
        )

    def test_candidate_local_import_failure_returns_parent_bytes(self):
        module = self._exercise(broken_runtime=True)
        report = module._PARENT._INSTANCE.diagnostics["aggregate_seed_budget"]
        self.assertEqual(report["reason"], "candidate_runtime_import_failed")
        self.assertEqual(report["error"], "RuntimeError")


if __name__ == "__main__":
    unittest.main()
