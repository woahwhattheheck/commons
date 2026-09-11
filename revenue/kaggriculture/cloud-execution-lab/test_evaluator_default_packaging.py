# SPDX-License-Identifier: Apache-2.0
"""Regression checks for the canonical evaluator's self-contained default layout."""
from pathlib import Path
import unittest

import build_integrated as build


class EvaluatorDefaultPackagingTests(unittest.TestCase):
    def test_default_evaluator_dependencies_are_packaged(self):
        mapping = build.source_files()
        expected = {
            "checks/reference/evaluator/evaluate.py": "reference/evaluator/evaluate.py",
            "checks/reference/evaluator/loader.py": "reference/evaluator/loader.py",
            "checks/reference/evaluator/official_agent.py": "reference/evaluator/official_agent.py",
            "checks/reference/evaluator/opponents.py": "reference/evaluator/opponents.py",
            "checks/reference/20260907-offline-agent/evaluate.py": "reference/evaluator/loader.py",
            "checks/reference/20260907-offline-agent/main.py": "reference/evaluator/official_agent.py",
        }
        for packaged, source in expected.items():
            with self.subTest(packaged=packaged):
                self.assertEqual(mapping.get(packaged), source)
                self.assertTrue((build.ROOT / source).is_file())

    def test_aliases_match_vendored_bytes(self):
        mapping = build.source_files()
        loader = build.ROOT / mapping["checks/reference/evaluator/loader.py"]
        loader_alias = build.ROOT / mapping["checks/reference/20260907-offline-agent/evaluate.py"]
        agent = build.ROOT / mapping["checks/reference/evaluator/official_agent.py"]
        agent_alias = build.ROOT / mapping["checks/reference/20260907-offline-agent/main.py"]
        self.assertEqual(loader.read_bytes(), loader_alias.read_bytes())
        self.assertEqual(agent.read_bytes(), agent_alias.read_bytes())

    def test_packaged_paths_satisfy_existing_evaluator_defaults(self):
        source = (build.ROOT / "reference/evaluator/evaluate.py").read_text(encoding="utf-8")
        opponents = (build.ROOT / "reference/evaluator/opponents.py").read_text(encoding="utf-8")
        self.assertIn('HERE.parent / "20260907-offline-agent" / "evaluate.py"', source)
        self.assertIn("HERE / 'opponents.py'", source)
        self.assertIn('parent.parent / "20260907-offline-agent" / "main.py"', opponents)
        mapping = build.source_files()
        self.assertIn("checks/reference/evaluator/opponents.py", mapping)
        self.assertIn("checks/reference/20260907-offline-agent/evaluate.py", mapping)
        self.assertIn("checks/reference/20260907-offline-agent/main.py", mapping)


if __name__ == "__main__":
    unittest.main()
