# SPDX-License-Identifier: Apache-2.0
"""Evaluator-shaped repeated-load contracts for the KESTREL carrier."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
ENTRYPOINT = HERE / "candidate_main.py"


def _load_as_pinned_evaluator(name: str):
    """Execute one fresh top-level module without publishing it in sys.modules.

    ``reference/evaluator/loader.py::load_agent`` creates a unique module name,
    executes the candidate, and returns its ``agent`` without registering the
    top-level module.  Reproduce that shape exactly enough to expose child-module
    aliasing while retaining the repository's real candidate and dependencies.
    """
    original_path = list(sys.path)
    here = HERE.resolve()
    sys.path[:] = [
        value for value in sys.path
        if Path(value or ".").resolve() != here
    ]
    try:
        spec = importlib.util.spec_from_file_location(name, ENTRYPOINT)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load {ENTRYPOINT}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = original_path


class KestrelEvaluatorLoadIsolationTests(unittest.TestCase):
    def test_two_loads_own_distinct_entrypoint_state_and_factory(self):
        first = _load_as_pinned_evaluator("candidate_sol_lattice_probe_one")
        second = _load_as_pinned_evaluator("candidate_sol_lattice_probe_two")

        self.assertIsNot(first._CANONICAL, second._CANONICAL)
        self.assertIsNot(first.agent, second.agent)
        self.assertIs(
            first.agent.__globals__,
            first._CANONICAL.__dict__,
        )
        self.assertIs(
            second.agent.__globals__,
            second._CANONICAL.__dict__,
        )
        self.assertIs(first._CANONICAL._new_instance, first._new_instance)
        self.assertIs(second._CANONICAL._new_instance, second._new_instance)

        first_marker = object()
        second_marker = object()
        first._CANONICAL._INSTANCE = first_marker
        second._CANONICAL._INSTANCE = second_marker
        self.assertIs(first._CANONICAL._INSTANCE, first_marker)
        self.assertIs(second._CANONICAL._INSTANCE, second_marker)

        import titan_runtime

        predecessor = first._CANDIDATE_RUNTIME.KestrelTitanAgent.__mro__[1]
        self.assertIs(titan_runtime.TitanAgent, predecessor)
        self.assertIs(
            second._CANDIDATE_RUNTIME.KestrelTitanAgent.__mro__[1],
            predecessor,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
