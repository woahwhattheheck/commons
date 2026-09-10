# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
CANDIDATE_PATH = (HERE / "candidate.py").resolve(strict=True)


def load_candidate(name: str):
    spec = importlib.util.spec_from_file_location(name, CANDIDATE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {CANDIDATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    if Path(module.__file__).resolve() != CANDIDATE_PATH:
        raise RuntimeError(f"wrong candidate loaded: {module.__file__}")
    return module


candidate = load_candidate("_titan_rival_decay_candidate_under_test")


class CandidateCustodyTests(unittest.TestCase):
    def test_exact_sibling_candidate_loaded(self):
        self.assertEqual(Path(candidate.__file__).resolve(), CANDIDATE_PATH)
        self.assertEqual(
            Path(candidate._DECAY_OBSERVER.__file__).resolve(),
            (HERE / "decay_observer.py").resolve(),
        )

    def test_exact_source_identity(self):
        self.assertEqual(candidate.verify_source(), candidate.EXPECTED_GIT_BLOBS)

    def test_tampered_source_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix="titan-decay-drift-") as raw:
            root = Path(raw)
            for relative in candidate.EXPECTED_GIT_BLOBS:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(candidate.LAB / relative, target)
            (root / "scheduler.py").write_bytes(
                (root / "scheduler.py").read_bytes() + b"\n# drift\n"
            )
            with self.assertRaises(candidate.SourceDrift):
                candidate.verify_source(root)

    def test_current_executable_consumer_is_patched(self):
        self.assertEqual(
            candidate.INSTALLED_CLASS._titan_rival_decay_decontamination,
            "titan-v3-rival-decay-decontamination-20260910-01",
        )
        config = json.loads((candidate.LAB / "TITAN-CONFIG.json").read_text())
        runtime = candidate.CANONICAL_MAIN._new_instance(candidate.LAB, config)
        runtime._initialize()
        self.assertIsInstance(runtime.consumer, candidate.INSTALLED_CLASS)
        self.assertEqual(
            runtime.consumer._titan_rival_decay_decontamination,
            "titan-v3-rival-decay-decontamination-20260910-01",
        )

    def test_canonical_entrypoint_is_callable_and_exact(self):
        self.assertTrue(callable(candidate.agent))
        self.assertEqual(
            Path(candidate.CANONICAL_MAIN.__file__).resolve(),
            (candidate.LAB / "main.py").resolve(),
        )
        self.assertIs(candidate.agent.__globals__, candidate.CANONICAL_MAIN.__dict__)

    def test_evaluator_shaped_loads_own_distinct_entrypoint_state(self):
        first = load_candidate("_titan_rival_decay_candidate_first")
        second = load_candidate("_titan_rival_decay_candidate_second")
        self.assertIsNot(first.CANONICAL_MAIN, second.CANONICAL_MAIN)
        self.assertIsNot(first.agent, second.agent)
        self.assertIs(first.agent.__globals__, first.CANONICAL_MAIN.__dict__)
        self.assertIs(second.agent.__globals__, second.CANONICAL_MAIN.__dict__)
        self.assertNotIn(f"{first.__name__}._canonical_main", sys.modules)
        self.assertNotIn(f"{second.__name__}._canonical_main", sys.modules)

        marker = object()
        first.CANONICAL_MAIN._INSTANCE = marker
        try:
            self.assertIs(first.CANONICAL_MAIN._INSTANCE, marker)
            self.assertIsNone(second.CANONICAL_MAIN._INSTANCE)
        finally:
            first.CANONICAL_MAIN._INSTANCE = None


if __name__ == "__main__":
    unittest.main()
