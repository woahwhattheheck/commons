# SPDX-License-Identifier: Apache-2.0
"""Predecessor killers for submission-time engine/runner identity closure."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pq.executable_pins import (  # noqa: E402
    ExecutablePinError,
    REQUIRED_SUBMISSION_INPUTS,
    bind_submission_config,
    load_submission_config,
    pin_submission,
    require_config_pin,
    submission_inputs,
)
from pq.pinning import PinStore, sha256_file  # noqa: E402


class ExecutablePinTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.pins = PinStore(self.root / "pin-store")

        self.candidate_artifact = self.root / "candidate.bin"
        self.candidate_artifact.write_bytes(b"candidate-v1")
        self.candidate_games = self.root / "candidate.GAMES.jsonl"
        self.candidate_games.write_text("{}\n")
        self.policy = self.root / "policy.json"
        self.policy.write_text(json.dumps({"policy": "strict"}))

        self.engine = self.root / "engine.json"
        self.engine.write_text(json.dumps({"engine": "official-v1"}))
        self.runner = self.root / "runner.json"
        self.runner.write_text(json.dumps({"runner": "paired-v1"}))
        self.baseline_games = self.root / "baseline.GAMES.jsonl"
        self.baseline_games.write_text("{}\n")
        self.baseline_artifact = self.root / "baseline.bin"
        self.baseline_artifact.write_bytes(b"baseline-v1")

        self.config = self.root / "predecessors.json"
        self._write_config()

    def tearDown(self):
        self.td.cleanup()

    def _write_config(self, *, engine_commit=None, runner_commit=None):
        doc = {
            "schema_version": 1,
            "policy_version": "promotion-policy/v1",
            "engine": {
                "commit": engine_commit or "a" * 40,
                "identity_file": str(self.engine),
            },
            "runner": {
                "commit": runner_commit or "b" * 40,
                "identity_file": str(self.runner),
            },
            "slots": {
                "control": {
                    "name": "frozen-control",
                    "games": str(self.baseline_games),
                    "artifact_file": str(self.baseline_artifact),
                }
            },
        }
        self.config.write_text(json.dumps(doc, sort_keys=True))

    def _inputs(self):
        return submission_inputs(
            candidate_artifact=self.candidate_artifact,
            candidate_games=self.candidate_games,
            policy=self.policy,
            predecessor_config=self.config,
        )

    def _manifest(self):
        return self.pins.pin(self._inputs())

    def _pin_submission(self):
        return pin_submission(
            self.pins,
            candidate_artifact=self.candidate_artifact,
            candidate_games=self.candidate_games,
            policy=self.policy,
            predecessor_config=self.config,
            note="test submission",
        )

    def _config_value(self):
        return load_submission_config(self.config)

    def test_complete_manifest_contains_executable_closure(self):
        manifest = self._manifest()
        self.assertEqual(
            set(manifest["inputs"]),
            set(REQUIRED_SUBMISSION_INPUTS),
        )
        self.assertEqual(
            manifest["inputs"]["engine_identity"]["sha256"],
            sha256_file(self.engine),
        )
        self.assertEqual(
            manifest["inputs"]["runner_identity"]["sha256"],
            sha256_file(self.runner),
        )
        self.assertEqual(
            manifest["inputs"]["predecessor_config"]["sha256"],
            sha256_file(self.config),
        )

    def test_pin_submission_returns_stored_verified_manifest(self):
        manifest = self._pin_submission()
        self.assertEqual(manifest, self.pins.get_pin(manifest["pin_id"]))
        self.assertEqual(set(manifest["inputs"]), set(REQUIRED_SUBMISSION_INPUTS))
        self.assertEqual(self.pins.verify_pin(manifest["pin_id"]), (True, []))
        bound = bind_submission_config(
            self.pins,
            manifest,
            self._config_value(),
        )
        self.assertEqual(
            Path(bound["engine"]["identity_file"]),
            self.pins.blob_path(manifest["inputs"]["engine_identity"]["sha256"]),
        )

    def test_engine_byte_change_changes_submission_identity(self):
        first = self._manifest()
        self.engine.write_text(json.dumps({"engine": "official-v2"}))
        second = self._manifest()
        self.assertNotEqual(first["input_digest"], second["input_digest"])
        self.assertNotEqual(first["pin_id"], second["pin_id"])

    def test_runner_byte_change_changes_submission_identity(self):
        first = self._manifest()
        self.runner.write_text(json.dumps({"runner": "paired-v2"}))
        second = self._manifest()
        self.assertNotEqual(first["input_digest"], second["input_digest"])
        self.assertNotEqual(first["pin_id"], second["pin_id"])

    def test_declared_commit_change_changes_submission_identity(self):
        first = self._manifest()
        self._write_config(engine_commit="c" * 40)
        second = self._manifest()
        self.assertNotEqual(first["input_digest"], second["input_digest"])

    def test_bound_config_uses_content_addressed_identity_blobs(self):
        manifest = self._manifest()
        bound = bind_submission_config(
            self.pins,
            manifest,
            self._config_value(),
        )
        for role, input_name in (
            ("engine", "engine_identity"),
            ("runner", "runner_identity"),
        ):
            expected = manifest["inputs"][input_name]["sha256"]
            bound_path = Path(bound[role]["identity_file"])
            self.assertEqual(bound_path, self.pins.blob_path(expected))
            self.assertEqual(sha256_file(bound_path), expected)

    def test_live_engine_swap_after_submit_is_rejected(self):
        manifest = self._manifest()
        config = self._config_value()
        self.engine.write_text(json.dumps({"engine": "attacker-swap"}))
        with self.assertRaisesRegex(ExecutablePinError, "engine identity drift"):
            bind_submission_config(self.pins, manifest, config)

    def test_live_runner_swap_after_submit_is_rejected(self):
        manifest = self._manifest()
        config = self._config_value()
        self.runner.write_text(json.dumps({"runner": "attacker-swap"}))
        with self.assertRaisesRegex(ExecutablePinError, "runner identity drift"):
            bind_submission_config(self.pins, manifest, config)

    def test_semantic_config_swap_after_submit_is_rejected(self):
        manifest = self._manifest()
        changed = copy.deepcopy(self._config_value())
        changed["engine"]["commit"] = "c" * 40
        with self.assertRaisesRegex(ExecutablePinError, "semantics differ"):
            bind_submission_config(self.pins, manifest, changed)

    def test_run_config_byte_drift_is_rejected_even_when_json_is_equivalent(self):
        manifest = self._manifest()
        expected = manifest["inputs"]["predecessor_config"]["sha256"]
        equivalent = json.loads(self.config.read_text())
        self.config.write_text(json.dumps(equivalent, indent=2, sort_keys=True) + "\n")
        observed = sha256_file(self.config)
        self.assertNotEqual(expected, observed)
        with self.assertRaisesRegex(ExecutablePinError, "config drift"):
            require_config_pin(manifest, observed)

    def test_exact_run_config_pin_is_accepted(self):
        manifest = self._manifest()
        expected = manifest["inputs"]["predecessor_config"]["sha256"]
        self.assertEqual(require_config_pin(manifest, expected), expected)

    def test_legacy_candidate_only_pin_is_rejected(self):
        manifest = self.pins.pin(
            {
                "candidate_artifact": self.candidate_artifact,
                "candidate_games": self.candidate_games,
                "policy": self.policy,
            }
        )
        with self.assertRaisesRegex(ExecutablePinError, "lacks executable closure"):
            bind_submission_config(self.pins, manifest, self._config_value())

    def test_tampered_pinned_engine_blob_is_rejected(self):
        manifest = self._manifest()
        digest = manifest["inputs"]["engine_identity"]["sha256"]
        self.pins.blob_path(digest).write_bytes(b"tampered")
        with self.assertRaisesRegex(ExecutablePinError, "verification failed"):
            bind_submission_config(self.pins, manifest, self._config_value())

    def test_missing_identity_file_fails_before_enqueue(self):
        self.engine.unlink()
        with self.assertRaisesRegex(ExecutablePinError, "identity_file missing"):
            self._inputs()

    def test_malformed_identity_field_fails_before_enqueue(self):
        doc = json.loads(self.config.read_text())
        doc["runner"]["identity_file"] = ""
        self.config.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ExecutablePinError, "nonempty string"):
            self._inputs()

    def test_top_level_array_config_is_rejected(self):
        self.config.write_text("[]")
        with self.assertRaisesRegex(ExecutablePinError, "expected object"):
            self._inputs()

    def test_duplicate_json_key_is_rejected(self):
        valid = self.config.read_text()
        self.config.write_text('{"schema_version":1,' + valid[1:])
        with self.assertRaisesRegex(ExecutablePinError, "duplicate JSON key"):
            self._inputs()

    def test_nonfinite_json_value_is_rejected(self):
        doc = json.loads(self.config.read_text())
        doc["unexpected_nonfinite"] = float("nan")
        self.config.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ExecutablePinError, "non-finite JSON value"):
            self._inputs()

    def test_nonhexadecimal_declared_commit_is_rejected(self):
        self._write_config(engine_commit="g" * 40)
        with self.assertRaisesRegex(ExecutablePinError, "is not hexadecimal"):
            self._inputs()

    def test_crossed_config_and_engine_snapshot_is_not_returned(self):
        replacement = self.root / "engine-v2.json"
        replacement.write_text(json.dumps({"engine": "official-v2"}))
        original_pin = self.pins.pin

        def cross_snapshot(inputs, *, note=""):
            # submission_inputs already resolved engine-v1. Mutate the config
            # before PinStore reads it so one tentative manifest crosses the
            # old engine with a config naming engine-v2.
            doc = json.loads(self.config.read_text())
            doc["engine"]["identity_file"] = str(replacement)
            self.config.write_text(json.dumps(doc, sort_keys=True))
            return original_pin(inputs, note=note)

        with patch.object(self.pins, "pin", side_effect=cross_snapshot):
            with self.assertRaisesRegex(ExecutablePinError, "engine identity drift"):
                self._pin_submission()

    def test_identity_disappearance_during_rehash_is_bounded(self):
        manifest = self._manifest()
        config = self._config_value()
        real_hash = sha256_file

        def disappear(path):
            if Path(path) == self.engine:
                raise FileNotFoundError("simulated identity disappearance")
            return real_hash(Path(path))

        with patch("pq.executable_pins.sha256_file", side_effect=disappear):
            with self.assertRaisesRegex(ExecutablePinError, "cannot be hashed"):
                bind_submission_config(self.pins, manifest, config)

    def test_blob_verification_io_race_is_bounded(self):
        manifest = self._manifest()
        with patch.object(
            self.pins,
            "verify_blob",
            side_effect=OSError("simulated blob read failure"),
        ):
            with self.assertRaisesRegex(ExecutablePinError, "blob cannot be verified"):
                bind_submission_config(self.pins, manifest, self._config_value())


if __name__ == "__main__":
    unittest.main()
