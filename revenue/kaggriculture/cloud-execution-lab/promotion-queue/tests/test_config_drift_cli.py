# SPDX-License-Identifier: Apache-2.0
"""CLI predecessor killers for drifted or malformed run configuration."""
from __future__ import annotations

import json
import unittest


class ConfigDriftCliTests(unittest.TestCase):
    def setUp(self):
        # Reuse the contract-shaped gate fixture without making its TestCase an
        # imported module attribute (which would cause duplicate discovery).
        from test_e2e_mocked import MockedEndToEndTests

        self.harness = MockedEndToEndTests(methodName="runTest")
        self.harness.setUp()

    def tearDown(self):
        self.harness.tearDown()

    def _blob_names(self) -> set[str]:
        root = self.harness.state / "pin-store" / "blobs"
        if not root.exists():
            return set()
        return {path.name for path in root.iterdir() if path.is_file()}

    def test_config_byte_drift_fails_before_gate_without_storing_new_blob(self):
        submission = self.harness._submit(
            "config-drift",
            own=110.0,
            policy_delta=5.0,
        )
        blobs_before = self._blob_names()

        # Preserve JSON semantics while changing the exact submitted bytes.
        config = json.loads(self.harness.config.read_text(encoding="utf-8"))
        self.harness.config.write_text(
            json.dumps(config, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        process = self.harness._run("--id", submission)
        self.assertNotEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertIn("predecessor config drift", process.stdout)

        # Rejection is observable in the queue, but no gate workspace, receipt,
        # or untrusted drifted config blob is admitted into state.
        entry = json.loads(
            self.harness._cli("status", submission).stdout
        )
        self.assertEqual(entry["status"], "failed")
        self.assertIsNone(entry["last_receipt"])
        self.assertEqual(self._blob_names(), blobs_before)
        self.assertFalse(
            (self.harness.state / "attempts" / submission).exists()
        )
        receipts = self.harness.state / "receipts"
        self.assertFalse(
            receipts.exists() and any(receipts.iterdir())
        )

    def test_malformed_config_is_bounded_before_queue_transition(self):
        submission = self.harness._submit(
            "malformed-config",
            own=110.0,
            policy_delta=5.0,
        )
        blobs_before = self._blob_names()
        self.harness.config.write_text("[]", encoding="utf-8")

        process = self.harness._run("--id", submission)
        self.assertEqual(process.returncode, 2, process.stdout + process.stderr)
        self.assertIn("FAILED run configuration", process.stdout)
        self.assertNotIn("Traceback", process.stdout + process.stderr)

        entry = json.loads(self.harness._cli("status", submission).stdout)
        self.assertEqual(entry["status"], "pending")
        self.assertEqual(entry["attempts"], [])
        self.assertIsNone(entry["last_receipt"])
        self.assertEqual(self._blob_names(), blobs_before)
        self.assertFalse(
            (self.harness.state / "attempts" / submission).exists()
        )


if __name__ == "__main__":
    unittest.main()
