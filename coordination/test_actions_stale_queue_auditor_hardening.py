from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "actions_stale_queue_auditor.py"
spec = importlib.util.spec_from_file_location(
    "actions_stale_queue_auditor_hardening_target", MODULE_PATH
)
assert spec and spec.loader
auditor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditor)

SHA_A = "a" * 40
SHA_B = "b" * 40


def packet():
    return {
        "schema": auditor.INPUT_SCHEMA,
        "repository": "woahwhattheheck/commons",
        "default_branch": "main",
        "observed_at": "2026-09-17T21:00:00Z",
        "runs": [
            {
                "run_id": 1,
                "workflow": "tests",
                "event": "pull_request",
                "status": "queued",
                "head_branch": "feature",
                "head_sha": SHA_A,
                "provenance": {
                    "complete": True,
                    "sources": ["RUN_DIRECT", "BRANCH_QUERY", "COMMIT_QUERY"],
                    "pull_requests": [
                        {"number": 1, "state": "CLOSED", "current_head_sha": SHA_B}
                    ],
                },
            }
        ],
    }


class CanonicalWorkBoundaryTests(unittest.TestCase):
    def _bomb_dumps(self, *args, **kwargs):
        raise AssertionError(
            "json.dumps must not be entered for over-budget direct object"
        )

    def test_huge_direct_scalar_rejects_before_serializer(self):
        data = packet()
        data["oversized"] = "x" * (auditor.MAX_JSON_BYTES + 1)
        old = auditor.json.dumps
        auditor.json.dumps = self._bomb_dumps
        try:
            with self.assertRaisesRegex(auditor.AuditError, "canonical JSON exceeds"):
                auditor.build_report(data)
        finally:
            auditor.json.dumps = old

    def test_huge_direct_key_rejects_before_serializer(self):
        data = packet()
        data["k" * (auditor.MAX_JSON_BYTES + 1)] = None
        old = auditor.json.dumps
        auditor.json.dumps = self._bomb_dumps
        try:
            with self.assertRaisesRegex(auditor.AuditError, "canonical JSON exceeds"):
                auditor.build_report(data)
        finally:
            auditor.json.dumps = old

    def test_repeated_long_scalar_charges_each_serialized_occurrence(self):
        data = packet()
        shared = "z" * 60_000
        data["amplification"] = [shared] * 18
        old = auditor.json.dumps
        auditor.json.dumps = self._bomb_dumps
        try:
            with self.assertRaisesRegex(auditor.AuditError, "canonical JSON exceeds"):
                auditor.build_report(data)
        finally:
            auditor.json.dumps = old

    def test_large_dict_rejects_before_hostile_child_touch(self):
        class Bomb:
            pass

        data = {
            f"k{i}": None
            for i in range((auditor.MAX_JSON_NODES // 2) + 1)
        }
        data["k0"] = Bomb()
        with self.assertRaisesRegex(auditor.AuditError, "remaining node budget"):
            auditor._freeze_plain_json(data)

    def test_json_string_cost_matches_encoder_for_escaping_and_unicode(self):
        samples = [
            "plain",
            'quote"slash\\',
            "line\nfeed",
            "snowman \u0001 \u2603 \U0001f680",
        ]
        for value in samples:
            expected = len(json.dumps(value, ensure_ascii=False).encode("utf-8"))
            observed = auditor._json_string_serialized_size(
                value, remaining=auditor.MAX_JSON_BYTES
            )
            self.assertEqual(observed, expected)

    def test_public_provenance_policy_rebind_does_not_widen_compiler(self):
        old_required = auditor.REQUIRED_PROVENANCE_SOURCES
        old_allowed = auditor.ALLOWED_PROVENANCE_SOURCES
        auditor.REQUIRED_PROVENANCE_SOURCES = frozenset()
        auditor.ALLOWED_PROVENANCE_SOURCES = frozenset({"RUN_DIRECT", "FAKE"})
        try:
            data = packet()
            data["runs"][0]["provenance"]["sources"] = ["RUN_DIRECT"]
            report = auditor.build_report(data)
            self.assertEqual(report["rows"][0]["decision"], "HOLD")
            self.assertIn(
                "PROVENANCE_SOURCES_INCOMPLETE", report["rows"][0]["reasons"]
            )

            data = packet()
            data["runs"][0]["provenance"]["sources"] = [
                "RUN_DIRECT", "BRANCH_QUERY", "FAKE"
            ]
            with self.assertRaisesRegex(
                auditor.AuditError, "unknown provenance source"
            ):
                auditor.build_report(data)
        finally:
            auditor.REQUIRED_PROVENANCE_SOURCES = old_required
            auditor.ALLOWED_PROVENANCE_SOURCES = old_allowed


if __name__ == "__main__":
    unittest.main()
