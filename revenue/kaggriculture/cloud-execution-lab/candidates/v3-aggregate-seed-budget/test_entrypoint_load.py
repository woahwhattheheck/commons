# SPDX-License-Identifier: Apache-2.0
"""Prove the candidate loads when its directory is absent from sys.path."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


class EntrypointLoadTests(unittest.TestCase):
    def test_path_bound_siblings_and_single_parent_call(self):
        module_names = (
            "_titan_granary_entrypoint_test",
            "_titan_granary_parent",
            "_titan_granary_runtime",
            "_titan_granary_aggregate",
        )
        previous = {name: sys.modules.get(name) for name in module_names}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "cloud-execution-lab"
            candidate = root / "candidates" / "v3-aggregate-seed-budget"
            candidate.mkdir(parents=True)
            for name in ("main.py", "candidate_runtime.py", "aggregate_seed_budget.py"):
                shutil.copy2(HERE / name, candidate / name)
            (root / "main.py").write_text(
                "CALLS = 0\n"
                "_INSTANCE = None\n"
                "def agent(observation, configuration=None):\n"
                "    global CALLS\n"
                "    CALLS += 1\n"
                "    return {'farmer':['PASS'],'hands':[],'market':[]}\n",
                encoding="utf-8",
            )
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
            if str(root) in sys.path:
                sys.path.remove(str(root))
        for name, value in previous.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


if __name__ == "__main__":
    unittest.main()
