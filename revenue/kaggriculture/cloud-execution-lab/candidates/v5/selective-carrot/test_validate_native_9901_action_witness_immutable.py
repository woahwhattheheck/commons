#!/usr/bin/env python3
from __future__ import annotations

import unittest

import action_divergence_witness as witness
import immutable_action_divergence_witness as immutable
import validate_native_9901_action_witness as base
import validate_native_9901_action_witness_immutable as validator


def meta(manifest, prefix):
    return {
        f"{prefix}_files": dict(manifest),
        f"{prefix}_manifest_sha256": witness._digest(manifest),
    }


class ImmutableWitnessValidatorTests(unittest.TestCase):
    def _authority(self):
        support = dict(validator.EXPECTED_PACK_SUPPORT)
        candidate = {"main.py": "1" * 64}
        apex = dict(validator.EXPECTED_APEX_RUNTIME)
        snapshot_entry = immutable._sha_bytes(
            immutable._deterministic_adapter("official.py", "main.py")
        )

        def side(source_sha, files, archive):
            return {
                "source_entry_sha256": source_sha,
                "snapshot_entry_sha256": snapshot_entry,
                **meta(files, "candidate"),
                **meta(support, "contract"),
                "archive_member_manifest_sha256": (
                    witness._digest(files) if archive else None
                ),
                "archive_members_verified": archive,
            }

        evaluator = {"evaluate.py": base.EXPECTED["evaluator"]}
        loader = {"evaluate.py": base.EXPECTED["loader"]}
        engine = dict(base.EXPECTED["engine"])
        return {
            "engine_sha256": dict(base.EXPECTED["engine"]),
            "left_entry_sha256": base.EXPECTED["left_entry"],
            "right_entry_sha256": base.EXPECTED["right_entry"],
            "opponent_entry_sha256": base.EXPECTED["opponent_entry"],
            "execution_snapshot": {
                "schema": immutable.SNAPSHOT_SCHEMA,
                "control": {
                    **meta(evaluator, "evaluator"),
                    **meta(loader, "loader"),
                    **meta(engine, "engine"),
                    "engine_sha256": dict(base.EXPECTED["engine"]),
                },
                "left": side(base.EXPECTED["left_entry"], candidate, True),
                "right": side(base.EXPECTED["right_entry"], candidate, True),
                "opponent": side(base.EXPECTED["opponent_entry"], apex, False),
            },
        }

    def test_exact_snapshot_authority_passes(self):
        authority = self._authority()
        got = validator.validate_snapshot_authority(authority)
        self.assertTrue(got["immutable_execution_snapshot_verified"])
        self.assertEqual(got["schema"], immutable.SNAPSHOT_SCHEMA)
        self.assertEqual(
            got["execution_snapshot_sha256"],
            witness._digest(authority["execution_snapshot"]),
        )

    def test_missing_snapshot_rejected(self):
        authority = self._authority()
        authority.pop("execution_snapshot")
        with self.assertRaisesRegex(validator.SnapshotValidationError, "missing"):
            validator.validate_snapshot_authority(authority)

    def test_source_entry_mismatch_rejected(self):
        authority = self._authority()
        authority["execution_snapshot"]["left"]["source_entry_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            validator.SnapshotValidationError, "source entry differs"
        ):
            validator.validate_snapshot_authority(authority)

    def test_candidate_archive_manifest_mismatch_rejected(self):
        authority = self._authority()
        authority["execution_snapshot"]["right"][
            "archive_member_manifest_sha256"
        ] = "0" * 64
        with self.assertRaisesRegex(
            validator.SnapshotValidationError, "candidate/archive manifest mismatch"
        ):
            validator.validate_snapshot_authority(authority)

    def test_pack_contract_drift_rejected(self):
        authority = self._authority()
        contract = authority["execution_snapshot"]["left"]["contract_files"]
        contract["official.py"] = "0" * 64
        authority["execution_snapshot"]["left"]["contract_manifest_sha256"] = witness._digest(
            contract
        )
        with self.assertRaisesRegex(
            validator.SnapshotValidationError, "official.py mismatch"
        ):
            validator.validate_snapshot_authority(authority)

    def test_apex_runtime_drift_rejected(self):
        authority = self._authority()
        candidate = authority["execution_snapshot"]["opponent"]["candidate_files"]
        candidate["agent.so"] = "0" * 64
        authority["execution_snapshot"]["opponent"]["candidate_manifest_sha256"] = witness._digest(
            candidate
        )
        with self.assertRaisesRegex(
            validator.SnapshotValidationError, "agent.so mismatch"
        ):
            validator.validate_snapshot_authority(authority)

    def test_snapshot_entry_must_be_deterministic_relative_adapter(self):
        authority = self._authority()
        authority["execution_snapshot"]["left"]["snapshot_entry_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            validator.SnapshotValidationError, "snapshot_entry_sha256 mismatch"
        ):
            validator.validate_snapshot_authority(authority)

    def test_path_poison_rejected_even_with_recomputed_digest(self):
        authority = self._authority()
        candidate = authority["execution_snapshot"]["left"]["candidate_files"]
        candidate["../escape.py"] = candidate["main.py"]
        authority["execution_snapshot"]["left"]["candidate_manifest_sha256"] = witness._digest(
            candidate
        )
        authority["execution_snapshot"]["left"]["archive_member_manifest_sha256"] = witness._digest(
            candidate
        )
        with self.assertRaisesRegex(
            validator.SnapshotValidationError, "path noncanonical"
        ):
            validator.validate_snapshot_authority(authority)


if __name__ == "__main__":
    unittest.main()
