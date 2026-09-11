from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
EVALUATOR = HERE / "reference" / "evaluator" / "evaluate.py"
LEGACY = HERE / "reference" / "20260907-offline-agent"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PackagedEvaluatorDefaultsTest(unittest.TestCase):
    def test_stock_evaluator_default_loader_is_present_and_pinned(self):
        evaluator = load(EVALUATOR, "titan_v31_stock_evaluator")
        self.assertEqual(evaluator.LOADER, LEGACY / "evaluate.py")
        compat = load(evaluator.LOADER, "titan_v31_compat_loader")
        packaged = load(HERE / "reference" / "evaluator" / "loader.py", "titan_v31_loader")
        self.assertEqual(compat.ENGINE_REF, evaluator.ENGINE_REF)
        self.assertEqual(compat.ENGINE_REF, packaged.ENGINE_REF)
        self.assertIs(compat.get_engine, compat._module.get_engine)

    def test_stock_evaluator_default_candidate_delegates_to_top_level_agent(self):
        evaluator = load(EVALUATOR, "titan_v31_stock_evaluator_candidate")
        candidate = evaluator.LOADER.with_name("main.py")
        self.assertEqual(candidate, LEGACY / "main.py")
        compat = load(candidate, "titan_v31_compat_candidate")
        self.assertTrue(callable(compat.agent))
        self.assertEqual(compat.TARGET, HERE.parent / "main.py")

    def test_stock_evaluator_bytes_are_unchanged_by_this_repair(self):
        import hashlib
        self.assertEqual(
            hashlib.sha256(EVALUATOR.read_bytes()).hexdigest(),
            "e30b3108e0027477ab7ddbc057892a241c41a1f2b38f72caf267477877c4333c",
        )


if __name__ == "__main__":
    unittest.main()
