"""Focused contracts for FLORA KAG-PRODUCTION."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("kag_production_build", HERE / "build.py")
assert SPEC and SPEC.loader
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)


class ProductionTests(unittest.TestCase):
    def test_exact_parent_contract(self):
        self.assertEqual(hashlib.sha256(build.PARENT.read_bytes()).hexdigest(), build.PARENT_SHA256)

    def test_deterministic_standalone_generation(self):
        source = build.PARENT.read_text()
        one, two = build.build(source), build.build(source)
        self.assertEqual(one, two)
        tree = ast.parse(one)
        callables = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
        self.assertEqual(callables[-1], "agent")
        self.assertNotIn("_base_agent", callables)
        self.assertIn("FERTILIZE", one)
        self.assertIn("BUY_LAND", one)
        self.assertIn('"STRAWBERRY"', one)

    def test_rejects_parent_drift(self):
        with self.assertRaises(ValueError):
            build.build(build.PARENT.read_text() + "\n")

    def test_generated_candidate_is_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "candidate.py"
            digest = build.generate(output)
            self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
