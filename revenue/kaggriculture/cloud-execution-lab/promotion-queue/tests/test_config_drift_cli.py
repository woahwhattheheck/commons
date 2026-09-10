# SPDX-License-Identifier: Apache-2.0
"""CLI predecessor killers for drifted or malformed submitted inputs."""
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

    def _receipt_names(self) -> set[str]:
        root = self.harness.state / "receipts"
        if not root.exists():
            return set()
        return {path.name for path in root.iterdir() if path.is_file()}

    def _attempt_paths(self, submission: str) -> set[str]:
        root = self.harness.state / "attempts" / submission
        if not root.exists():
            return set()
        return {
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
        }

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
        self.assertEqual(self._attempt_paths(submission), set())
        self.assertEqual(self._receipt_names(), set())

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
        self.assertEqual(self._attempt_paths(submission), set())
        self.assertEqual(self._receipt_names(), set())

    def test_post_submit_predecessor_panel_swap_fails_before_gate(self):
        submission = self.harness._submit(
            "panel-swap",
            own=110.0,
            policy_delta=5.0,
        )
        blobs_before = self._blob_names()
        self.harness.control_games.write_text(
            '{"opponent":"attacker","seed":0,"candidate_seat":0,'
            '"status":"complete","scores":[0,0]}\n',
            encoding="utf-8",
        )

        process = self.harness._run("--id", submission)
        self.assertNotEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertIn("slot 'frozen_control' games drift", process.stdout)
        self.assertNotIn("Traceback", process.stdout + process.stderr)

        entry = json.loads(self.harness._cli("status", submission).stdout)
        self.assertEqual(entry["status"], "failed")
        self.assertIsNone(entry["last_receipt"])
        self.assertEqual(self._blob_names(), blobs_before)
        self.assertEqual(self._attempt_paths(submission), set())
        self.assertEqual(self._receipt_names(), set())
        self.assertIn("games drift", entry["attempts"][-1]["error"])

    def test_post_submit_predecessor_artifact_swap_fails_before_gate(self):
        submission = self.harness._submit(
            "artifact-swap",
            own=110.0,
            policy_delta=5.0,
        )
        blobs_before = self._blob_names()
        self.harness.control_artifact.write_bytes(b"replaced-control")

        process = self.harness._run("--id", submission)
        self.assertNotEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertIn(
            "slot 'frozen_control' artifact_file drift",
            process.stdout,
        )
        self.assertNotIn("Traceback", process.stdout + process.stderr)

        entry = json.loads(self.harness._cli("status", submission).stdout)
        self.assertEqual(entry["status"], "failed")
        self.assertIsNone(entry["last_receipt"])
        self.assertEqual(self._blob_names(), blobs_before)
        self.assertEqual(self._attempt_paths(submission), set())
        self.assertEqual(self._receipt_names(), set())
        self.assertIn("artifact_file drift", entry["attempts"][-1]["error"])

    def test_successful_queue_id_refuses_drifted_panel_rerun(self):
        submission = self.harness._submit(
            "rerun-panel-drift",
            own=110.0,
            policy_delta=5.0,
        )
        first = self.harness._run("--id", submission)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertIn("PROMOTE", first.stdout)

        passed = json.loads(self.harness._cli("status", submission).stdout)
        first_receipt = passed["last_receipt"]
        self.assertIsNotNone(first_receipt)
        receipts_before = self._receipt_names()
        attempts_before = self._attempt_paths(submission)
        blobs_before = self._blob_names()

        requeue = self.harness._cli("rerun", submission)
        self.assertEqual(requeue.returncode, 0, requeue.stdout + requeue.stderr)
        self.harness.control_games.write_text(
            '{"opponent":"attacker","seed":0,"candidate_seat":0,'
            '"status":"complete","scores":[1000000,0]}\n',
            encoding="utf-8",
        )
        second = self.harness._run("--id", submission)
        self.assertNotEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn("slot 'frozen_control' games drift", second.stdout)

        failed = json.loads(self.harness._cli("status", submission).stdout)
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["last_receipt"], first_receipt)
        self.assertEqual(self._receipt_names(), receipts_before)
        self.assertEqual(self._attempt_paths(submission), attempts_before)
        self.assertEqual(self._blob_names(), blobs_before)
        self.assertEqual(len(failed["attempts"]), 3)
        self.assertEqual(failed["attempts"][-1]["kind"], "run")
        self.assertIn("games drift", failed["attempts"][-1]["error"])


if __name__ == "__main__":
    unittest.main()
