# SPDX-License-Identifier: Apache-2.0
"""Predecessor killers for submission-time queue-input identity closure."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pq.executable_pins import (  # noqa: E402
    BASE_SUBMISSION_INPUTS,
    ExecutablePinError,
    bind_submission_config,
    expected_submission_input_names,
    load_submission_config,
    pin_submission,
    require_config_pin,
    slot_input_name,
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

    def _write_config(
        self,
        *,
        engine_commit=None,
        runner_commit=None,
        slot_key="control",
        games=None,
        artifact=None,
    ):
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
                slot_key: {
                    "name": "frozen-control",
                    "games": str(games or self.baseline_games),
                    "artifact_file": str(artifact or self.baseline_artifact),
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

    def _expected_names(self):
        return set(expected_submission_input_names(self._config_value()))

    def test_complete_manifest_contains_declared_input_closure(self):
        manifest = self._manifest()
        self.assertEqual(set(manifest["inputs"]), self._expected_names())
        self.assertEqual(len(manifest["inputs"]), 8)
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
        self.assertEqual(
            manifest["inputs"][slot_input_name("control", "games")]["sha256"],
            sha256_file(self.baseline_games),
        )
        self.assertEqual(
            manifest["inputs"][slot_input_name("control", "artifact_file")]["sha256"],
            sha256_file(self.baseline_artifact),
        )

    def test_pin_submission_returns_stored_verified_manifest(self):
        manifest = self._pin_submission()
        self.assertEqual(manifest, self.pins.get_pin(manifest["pin_id"]))
        self.assertEqual(set(manifest["inputs"]), self._expected_names())
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

    def test_predecessor_games_change_changes_submission_identity(self):
        first = self._manifest()
        self.baseline_games.write_text('{"panel":"replacement"}\n')
        second = self._manifest()
        self.assertNotEqual(first["input_digest"], second["input_digest"])
        self.assertNotEqual(first["pin_id"], second["pin_id"])

    def test_predecessor_artifact_change_changes_submission_identity(self):
        first = self._manifest()
        self.baseline_artifact.write_bytes(b"baseline-v2")
        second = self._manifest()
        self.assertNotEqual(first["input_digest"], second["input_digest"])
        self.assertNotEqual(first["pin_id"], second["pin_id"])

    def test_declared_commit_change_changes_submission_identity(self):
        first = self._manifest()
        self._write_config(engine_commit="c" * 40)
        second = self._manifest()
        self.assertNotEqual(first["input_digest"], second["input_digest"])

    def test_slot_path_retarget_changes_submission_identity(self):
        first = self._manifest()
        replacement = self.root / "replacement.GAMES.jsonl"
        replacement.write_bytes(self.baseline_games.read_bytes())
        self._write_config(games=replacement)
        second = self._manifest()
        # Even byte-identical panel content gets a new identity because the
        # exact predecessor config path is itself submitted.
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

    def test_bound_config_uses_content_addressed_slot_files(self):
        manifest = self._manifest()
        bound = bind_submission_config(
            self.pins,
            manifest,
            self._config_value(),
        )
        for field in ("games", "artifact_file"):
            input_name = slot_input_name("control", field)
            expected = manifest["inputs"][input_name]["sha256"]
            bound_path = Path(bound["slots"]["control"][field])
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

    def test_live_predecessor_games_swap_after_submit_is_rejected(self):
        manifest = self._manifest()
        config = self._config_value()
        self.baseline_games.write_text('{"panel":"attacker-swap"}\n')
        with self.assertRaisesRegex(ExecutablePinError, "slot 'control' games drift"):
            bind_submission_config(self.pins, manifest, config)

    def test_live_predecessor_artifact_swap_after_submit_is_rejected(self):
        manifest = self._manifest()
        config = self._config_value()
        self.baseline_artifact.write_bytes(b"attacker-swap")
        with self.assertRaisesRegex(
            ExecutablePinError,
            "slot 'control' artifact_file drift",
        ):
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
        with self.assertRaisesRegex(ExecutablePinError, "lacks base input closure"):
            bind_submission_config(self.pins, manifest, self._config_value())

    def test_legacy_six_input_pin_without_slot_files_is_rejected(self):
        all_inputs = self._inputs()
        manifest = self.pins.pin(
            {name: all_inputs[name] for name in BASE_SUBMISSION_INPUTS}
        )
        with self.assertRaisesRegex(ExecutablePinError, "input cardinality differs"):
            bind_submission_config(self.pins, manifest, self._config_value())

    def test_extra_detached_manifest_input_is_rejected(self):
        extra = self.root / "extra.bin"
        extra.write_bytes(b"detached")
        inputs = self._inputs()
        inputs["detached_extra"] = extra
        manifest = self.pins.pin(inputs)
        with self.assertRaisesRegex(ExecutablePinError, "input cardinality differs"):
            bind_submission_config(self.pins, manifest, self._config_value())

    def test_tampered_pinned_engine_blob_is_rejected(self):
        manifest = self._manifest()
        digest = manifest["inputs"]["engine_identity"]["sha256"]
        self.pins.blob_path(digest).write_bytes(b"tampered")
        with self.assertRaisesRegex(ExecutablePinError, "verification failed"):
            bind_submission_config(self.pins, manifest, self._config_value())

    def test_tampered_pinned_predecessor_panel_is_rejected(self):
        manifest = self._manifest()
        digest = manifest["inputs"][slot_input_name("control", "games")]["sha256"]
        self.pins.blob_path(digest).write_bytes(b"tampered")
        with self.assertRaisesRegex(ExecutablePinError, "verification failed"):
            bind_submission_config(self.pins, manifest, self._config_value())

    def test_missing_identity_file_fails_before_enqueue(self):
        self.engine.unlink()
        with self.assertRaisesRegex(ExecutablePinError, "identity_file missing"):
            self._inputs()

    def test_missing_slot_file_fails_before_enqueue(self):
        self.baseline_games.unlink()
        with self.assertRaisesRegex(ExecutablePinError, "slot 'control'.games missing"):
            self._inputs()

    def test_malformed_identity_field_fails_before_enqueue(self):
        doc = json.loads(self.config.read_text())
        doc["runner"]["identity_file"] = ""
        self.config.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ExecutablePinError, "nonempty string"):
            self._inputs()

    def test_malformed_slot_field_fails_before_enqueue(self):
        doc = json.loads(self.config.read_text())
        doc["slots"]["control"]["artifact_file"] = ""
        self.config.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ExecutablePinError, "artifact_file.*nonempty string"):
            self._inputs()

    def test_slot_input_names_are_collision_free_for_path_like_unicode_keys(self):
        first = slot_input_name("control/β:one", "games")
        second = slot_input_name("control?β:one", "games")
        self.assertNotEqual(first, second)
        self.assertNotIn("/", first)
        self.assertNotIn(":", first)
        self._write_config(slot_key="control/β:one")
        inputs = self._inputs()
        self.assertIn(first, inputs)
        self.assertEqual(len(inputs), len(set(inputs)))

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

    def test_crossed_config_and_slot_snapshot_is_not_returned(self):
        replacement = self.root / "baseline-v2.GAMES.jsonl"
        replacement.write_text('{"panel":"v2"}\n')
        original_pin = self.pins.pin

        def cross_snapshot(inputs, *, note=""):
            doc = json.loads(self.config.read_text())
            doc["slots"]["control"]["games"] = str(replacement)
            self.config.write_text(json.dumps(doc, sort_keys=True))
            return original_pin(inputs, note=note)

        with patch.object(self.pins, "pin", side_effect=cross_snapshot):
            with self.assertRaisesRegex(ExecutablePinError, "slot 'control' games drift"):
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

    def test_slot_disappearance_during_rehash_is_bounded(self):
        manifest = self._manifest()
        config = self._config_value()
        real_hash = sha256_file

        def disappear(path):
            if Path(path) == self.baseline_games:
                raise FileNotFoundError("simulated predecessor disappearance")
            return real_hash(Path(path))

        with patch("pq.executable_pins.sha256_file", side_effect=disappear):
            with self.assertRaisesRegex(ExecutablePinError, "cannot be hashed"):
                bind_submission_config(self.pins, manifest, config)

    def test_blob_verification_io_race_is_bounded(self):
        manifest = self._manifest()
        with patch.object(
            self.pins,
            "verify_pin",
            return_value=(True, []),
        ), patch.object(
            self.pins,
            "verify_blob",
            side_effect=OSError("simulated blob read failure"),
        ):
            with self.assertRaisesRegex(ExecutablePinError, "blob cannot be verified"):
                bind_submission_config(self.pins, manifest, self._config_value())


if __name__ == "__main__":
    unittest.main()
