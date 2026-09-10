# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

import candidate


class CandidateCustodyTests(unittest.TestCase):
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

    def test_canonical_entrypoint_is_callable(self):
        self.assertTrue(callable(candidate.agent))
        self.assertEqual(Path(candidate.CANONICAL_MAIN.__file__).resolve(),
                         (candidate.LAB / "main.py").resolve())


if __name__ == "__main__":
    unittest.main()
