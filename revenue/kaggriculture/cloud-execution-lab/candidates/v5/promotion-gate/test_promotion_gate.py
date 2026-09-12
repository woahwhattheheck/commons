# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
import unittest

import promotion_gate as gate


def _rehash_manifest(manifest):
    body = {key: value for key, value in manifest.items() if key != "candidate_id"}
    manifest["candidate_id"] = "v5c:" + hashlib.sha256(
        json.dumps(
            body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()
    return manifest


def _manifest():
    body = {
        "schema": gate.IDENTITY_SCHEMA,
        "base_id": "titan-v5-main",
        "engine_id": "engine:abc",
        "opponent_pack_id": "frontier:1",
        "config_sha256": "a" * 64,
        "components": [
            {
                "name": "candidate",
                "source": "candidate.py",
                "source_sha256": "b" * 64,
                "activation": {"mode": "config", "equals": {"t": "dict", "v": []}},
            }
        ],
    }
    return _rehash_manifest({**body, "candidate_id": ""})


def _engagement(candidate_id):
    return {
        "classification": "ENGAGED",
        "observations": 8,
        "noop_threshold": 8,
        "divergence_count": 2,
        "engagement_rate": 0.25,
        "first_divergence": {
            "observation": 2,
            "key": {"seed": 7, "seat": 0, "step": 12, "phase": "market"},
            "control_fingerprint": "2" * 64,
            "candidate_fingerprint": "3" * 64,
        },
        "control_sequence_fingerprint": "4" * 64,
        "candidate_sequence_fingerprint": "5" * 64,
        "key_fields": ["seed", "seat", "step", "phase"],
        "control_id": "v5c:" + "1" * 64,
        "candidate_id": candidate_id,
    }


def _runtime(candidate_id):
    return {
        "classification": "PASS",
        "promotion_ready": True,
        "receipt_count": 8,
        "candidate_count": 1,
        "max_fallback_rate": 0.0,
        "deadline_fallback_count": 0,
        "deadline_fallback_rate": 0.0,
        "expected_design_declared": True,
        "expected_callback_count": 8,
        "expected_complete": True,
        "missing_expected": [],
        "unexpected_extra": [],
        "p99_headroom_seconds": 0.1,
        "overall": {"count": 8},
        "by_candidate": {
            candidate_id: {"count": 8, "deadline_fallback_count": 0}
        },
    }


class PromotionGateTest(unittest.TestCase):
    def test_valid_cross_evidence_receipt(self):
        manifest = _manifest()
        engagement = _engagement(manifest["candidate_id"])
        runtime = _runtime(manifest["candidate_id"])
        receipt = gate.build_receipt(manifest, engagement, runtime)
        self.assertEqual("PASS", receipt["classification"])
        self.assertTrue(receipt["promotion_ready"])
        self.assertEqual(manifest["candidate_id"], receipt["candidate_id"])
        self.assertEqual(engagement["control_id"], receipt["control_id"])
        self.assertEqual(8, receipt["runtime"]["receipt_count"])
        self.assertEqual(
            {"candidate_manifest", "engagement_report", "runtime_report"},
            set(receipt["evidence_sha256"]),
        )

    def test_cross_build_engagement_is_rejected(self):
        manifest = _manifest()
        engagement = _engagement("v5c:" + "2" * 64)
        with self.assertRaisesRegex(gate.PromotionError, "does not match candidate manifest"):
            gate.build_receipt(manifest, engagement, _runtime(manifest["candidate_id"]))

    def test_noop_engagement_is_not_promotable(self):
        manifest = _manifest()
        engagement = _engagement(manifest["candidate_id"])
        engagement["classification"] = "NO_OP_OBSERVED"
        engagement["divergence_count"] = 0
        engagement["engagement_rate"] = 0.0
        engagement["first_divergence"] = None
        with self.assertRaisesRegex(gate.PromotionError, "must be ENGAGED"):
            gate.build_receipt(manifest, engagement, _runtime(manifest["candidate_id"]))

    def test_stale_runtime_pass_with_extra_callback_is_rejected(self):
        manifest = _manifest()
        runtime = _runtime(manifest["candidate_id"])
        runtime["unexpected_extra"] = [
            {"candidate": manifest["candidate_id"], "seed": 9, "seat": 0, "step": 1}
        ]
        with self.assertRaisesRegex(gate.PromotionError, "unexpected callbacks"):
            gate.build_receipt(
                manifest, _engagement(manifest["candidate_id"]), runtime
            )

    def test_runtime_must_be_candidate_pure(self):
        manifest = _manifest()
        runtime = _runtime(manifest["candidate_id"])
        runtime["candidate_count"] = 2
        runtime["by_candidate"]["v5c:" + "3" * 64] = {
            "count": 1,
            "deadline_fallback_count": 0,
        }
        with self.assertRaisesRegex(gate.PromotionError, "exactly one candidate"):
            gate.build_receipt(
                manifest, _engagement(manifest["candidate_id"]), runtime
            )

    def test_manifest_id_tamper_is_rejected(self):
        manifest = _manifest()
        manifest["base_id"] = "other-base"
        with self.assertRaisesRegex(gate.PromotionError, "does not match manifest body"):
            gate.build_receipt(
                manifest,
                _engagement(manifest["candidate_id"]),
                _runtime(manifest["candidate_id"]),
            )

    def test_self_hashed_noncanonical_component_is_rejected(self):
        manifest = _manifest()
        manifest["components"][0]["invented"] = True
        _rehash_manifest(manifest)
        with self.assertRaisesRegex(gate.PromotionError, "exact canonical component keys"):
            gate.build_receipt(
                manifest,
                _engagement(manifest["candidate_id"]),
                _runtime(manifest["candidate_id"]),
            )

    def test_self_hashed_unsorted_component_records_are_rejected(self):
        manifest = _manifest()
        first = manifest["components"][0]
        second = {
            "name": "aaa",
            "source": "aaa.py",
            "source_sha256": "c" * 64,
            "activation": {"mode": "unconditional"},
        }
        manifest["components"] = [first, second]
        _rehash_manifest(manifest)
        with self.assertRaisesRegex(gate.PromotionError, "must be sorted by name"):
            gate.build_receipt(
                manifest,
                _engagement(manifest["candidate_id"]),
                _runtime(manifest["candidate_id"]),
            )

    def test_self_hashed_noncanonical_typed_activation_is_rejected(self):
        manifest = _manifest()
        manifest["components"][0]["activation"]["equals"] = {
            "t": "dict",
            "v": [
                ["z", {"t": "int", "v": "01"}],
                ["a", {"t": "bool", "v": True}],
            ],
        }
        _rehash_manifest(manifest)
        with self.assertRaises(gate.PromotionError):
            gate.build_receipt(
                manifest,
                _engagement(manifest["candidate_id"]),
                _runtime(manifest["candidate_id"]),
            )

    def test_partial_handwritten_engagement_report_is_rejected(self):
        manifest = _manifest()
        engagement = _engagement(manifest["candidate_id"])
        del engagement["candidate_sequence_fingerprint"]
        with self.assertRaisesRegex(gate.PromotionError, "engagement report keys mismatch"):
            gate.build_receipt(manifest, engagement, _runtime(manifest["candidate_id"]))

    def test_engagement_redundant_fields_are_exact(self):
        manifest = _manifest()
        engagement = _engagement(manifest["candidate_id"])
        engagement["engagement_rate"] = 0.5
        with self.assertRaisesRegex(gate.PromotionError, "rate disagrees"):
            gate.build_receipt(manifest, engagement, _runtime(manifest["candidate_id"]))

        engagement = _engagement(manifest["candidate_id"])
        engagement["first_divergence"]["candidate_fingerprint"] = (
            engagement["first_divergence"]["control_fingerprint"]
        )
        with self.assertRaisesRegex(gate.PromotionError, "fingerprints must differ"):
            gate.build_receipt(manifest, engagement, _runtime(manifest["candidate_id"]))

        engagement = _engagement(manifest["candidate_id"])
        del engagement["first_divergence"]["key"]["phase"]
        with self.assertRaisesRegex(gate.PromotionError, "key must match key_fields"):
            gate.build_receipt(manifest, engagement, _runtime(manifest["candidate_id"]))

    def test_runtime_summary_inconsistency_is_rejected(self):
        manifest = _manifest()
        runtime = _runtime(manifest["candidate_id"])
        runtime["deadline_fallback_count"] = 1
        with self.assertRaisesRegex(gate.PromotionError, "fallback count disagrees"):
            gate.build_receipt(
                manifest, _engagement(manifest["candidate_id"]), runtime
            )

    def test_strict_json_rejects_duplicate_keys_and_nonfinite_constants(self):
        with self.assertRaisesRegex(gate.PromotionError, "duplicate JSON object key"):
            gate._loads_strict('{"candidate_id":"a","candidate_id":"b"}')
        for token in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(token=token):
                with self.assertRaisesRegex(gate.PromotionError, "non-finite"):
                    gate._loads_strict('{"x":' + token + "}")


if __name__ == "__main__":
    unittest.main()
