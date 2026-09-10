# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

import candidate_patch

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]


class CandidateLoaderContracts(unittest.TestCase):
    def test_repository_entrypoint_loads_exact_mapped_dependency(self):
        sys.modules.pop("observed_clone", None)
        sys.modules.pop("titan_v3_multi_lot_portfolio_scheduler", None)
        path = HERE / "candidate.py"
        name = "multi_lot_candidate_loader_contract"
        spec = importlib.util.spec_from_file_location(name, path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
            self.assertTrue(callable(module.agent))
            self.assertTrue(callable(module.SellScheduler))
            observed = sys.modules.get("observed_clone")
            self.assertIsNotNone(observed)
            origin = Path(observed.__file__).resolve()
            expected = (LAB.parent / "cloud-runtime-pulse" / "observed_clone.py").resolve()
            self.assertEqual(origin, expected)
            self.assertEqual(
                candidate_patch.git_blob_sha(origin.read_bytes()),
                module.EXPECTED_OBSERVED_CLONE_GIT_BLOB,
            )
        finally:
            sys.modules.pop(name, None)


if __name__ == "__main__":
    unittest.main()
