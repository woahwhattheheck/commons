from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

import action_cardinality_gate as gate
import gate_common


class BuildEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).parent
        cls.manifest = json.loads(
            (cls.root / "BUILD-EVIDENCE.json").read_text(encoding="utf-8")
        )

    def test_manifest_seal(self) -> None:
        self.assertEqual(
            gate.verify_receipt(self.manifest),
            (True, "receipt hash verified"),
        )

    def test_every_declared_artifact_matches_published_bytes(self) -> None:
        seen: set[str] = set()
        for artifact in self.manifest["artifacts"]:
            relative = artifact["path"]
            self.assertNotIn(relative, seen)
            seen.add(relative)
            path = self.root / relative
            payload = path.read_bytes()
            self.assertEqual(len(payload), artifact["bytes"], relative)
            self.assertEqual(hashlib.sha256(payload).hexdigest(), artifact["sha256"], relative)
        self.assertEqual(
            seen,
            {
                "README.md",
                "OBSERVED-107140666.json",
                "action_cardinality_gate.py",
                "gate_common.py",
                "gate_core.py",
                "gate_receipt.py",
                "run_tests.sh",
                "test_support.py",
                "test_analyze_replay.py",
                "test_run_gate.py",
                "test_observed_receipt.py",
                "test_build_evidence.py",
            },
        )

    def test_observed_receipt_binds_exact_gate_bytes(self) -> None:
        observed = json.loads(
            (self.root / "OBSERVED-107140666.json").read_text(encoding="utf-8")
        )
        self.assertEqual(observed["tool_sha256"], gate_common._tool_sha256())
        self.assertEqual(
            self.manifest["submitted_replay"]["receipt_sha256"],
            observed["receipt_sha256"],
        )

    def test_scope_is_additive_and_path_bounded(self) -> None:
        prefix = self.manifest["scope"]["owned_prefix"]
        changed = self.manifest["scope"]["changed_paths"]
        self.assertEqual(len(changed), len(set(changed)))
        self.assertTrue(all(path.startswith(prefix + "/") for path in changed))
        self.assertEqual(
            {path.removeprefix(prefix + "/") for path in changed},
            {artifact["path"] for artifact in self.manifest["artifacts"]}
            | {"BUILD-EVIDENCE.json"},
        )


if __name__ == "__main__":
    unittest.main()
