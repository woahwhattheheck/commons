from __future__ import annotations

import copy
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


    def test_live_serializer_rebind_cannot_self_ratify_false_safe(self):
        data = packet()
        data["runs"][0]["provenance"]["pull_requests"] = [
            {"number": 1, "state": "OPEN", "current_head_sha": SHA_A}
        ]
        report = auditor.build_report(data)
        self.assertEqual(report["rows"][0]["decision"], "HOLD")

        tampered = copy.deepcopy(report)
        tampered["rows"][0]["decision"] = "SAFE_TO_CANCEL"
        tampered["rows"][0]["reasons"] = ["ALL_ASSOCIATED_PRS_CLOSED_OR_STALE"]
        tampered["counts"] = {"HOLD": 0, "SAFE_TO_CANCEL": 1}

        old_dumps = auditor.json.dumps
        auditor.json.dumps = lambda *args, **kwargs: "{}"
        try:
            unsigned = dict(tampered)
            unsigned.pop("report_receipt")
            tampered["report_receipt"] = auditor.sha256_hex(
                auditor.canonical_json(unsigned)
            )
            with self.assertRaisesRegex(
                auditor.AuditError, "semantic recompile mismatch"
            ):
                auditor.verify_report(tampered)
        finally:
            auditor.json.dumps = old_dumps

    def test_live_digest_rebind_cannot_change_report_generation(self):
        baseline = auditor.build_report(packet())

        class FakeDigest:
            def hexdigest(self):
                return "0" * 64

        old_sha256 = auditor.hashlib.sha256
        auditor.hashlib.sha256 = lambda *args, **kwargs: FakeDigest()
        try:
            rebuilt = auditor.build_report(packet())
            self.assertEqual(rebuilt, baseline)
            self.assertTrue(auditor.verify_report(rebuilt))
        finally:
            auditor.hashlib.sha256 = old_sha256

    def test_live_parser_rebind_does_not_change_strict_parse(self):
        old_loads = auditor.json.loads
        auditor.json.loads = lambda *args, **kwargs: {"forged": True}
        try:
            self.assertEqual(auditor.loads_strict('{"x":1}'), {"x": 1})
        finally:
            auditor.json.loads = old_loads

    def test_public_work_limit_rebind_cannot_widen_captured_generation(self):
        original_safe = auditor.MAX_SAFE_INTEGER
        original_bytes = auditor.MAX_JSON_BYTES
        original_depth = auditor.MAX_JSON_DEPTH
        original_nodes = auditor.MAX_JSON_NODES
        original_runs = auditor.MAX_RUNS
        original_prs = auditor.MAX_PULL_REQUESTS_PER_RUN
        auditor.MAX_SAFE_INTEGER = 10**100
        auditor.MAX_JSON_BYTES = 10**9
        auditor.MAX_JSON_DEPTH = 10**6
        auditor.MAX_JSON_NODES = 10**9
        auditor.MAX_RUNS = 10**9
        auditor.MAX_PULL_REQUESTS_PER_RUN = 10**9
        try:
            with self.assertRaises(auditor.AuditError):
                auditor._freeze_plain_json(original_safe + 1)

            with self.assertRaisesRegex(auditor.AuditError, "canonical JSON exceeds"):
                auditor._freeze_plain_json("x" * (original_bytes + 1))

            deep = None
            for _ in range(original_depth + 2):
                deep = [deep]
            with self.assertRaisesRegex(auditor.AuditError, "nesting"):
                auditor._freeze_plain_json(deep)

            with self.assertRaisesRegex(auditor.AuditError, "node budget|node count"):
                auditor._freeze_plain_json([None] * (original_nodes + 1))

            too_many_runs = packet()
            too_many_runs["runs"] = [packet()["runs"][0]] * (original_runs + 1)
            with self.assertRaisesRegex(auditor.AuditError, "runs exceeds"):
                auditor.normalize_packet(too_many_runs)

            too_many_prs = packet()
            template_pr = too_many_prs["runs"][0]["provenance"]["pull_requests"][0]
            too_many_prs["runs"][0]["provenance"]["pull_requests"] = [
                dict(template_pr) for _ in range(original_prs + 1)
            ]
            with self.assertRaisesRegex(
                auditor.AuditError, "too many associated pull requests"
            ):
                auditor.normalize_packet(too_many_prs)
        finally:
            auditor.MAX_SAFE_INTEGER = original_safe
            auditor.MAX_JSON_BYTES = original_bytes
            auditor.MAX_JSON_DEPTH = original_depth
            auditor.MAX_JSON_NODES = original_nodes
            auditor.MAX_RUNS = original_runs
            auditor.MAX_PULL_REQUESTS_PER_RUN = original_prs


    def test_exported_build_report_rebind_cannot_self_ratify_false_safe(self):
        data = packet()
        data["runs"][0]["provenance"]["pull_requests"] = [
            {"number": 1, "state": "OPEN", "current_head_sha": SHA_A}
        ]
        report = auditor.build_report(data)
        self.assertEqual(report["rows"][0]["decision"], "HOLD")

        tampered = copy.deepcopy(report)
        tampered["rows"][0]["decision"] = "SAFE_TO_CANCEL"
        tampered["rows"][0]["reasons"] = ["ALL_ASSOCIATED_PRS_CLOSED_OR_STALE"]
        tampered["counts"] = {"HOLD": 0, "SAFE_TO_CANCEL": 1}
        unsigned = dict(tampered)
        unsigned.pop("report_receipt")
        tampered["report_receipt"] = auditor.sha256_hex(
            auditor.canonical_json(unsigned)
        )

        original_build_report = auditor.build_report
        auditor.build_report = lambda _retained: tampered
        try:
            with self.assertRaisesRegex(
                auditor.AuditError, "semantic recompile mismatch"
            ):
                auditor.verify_report(tampered)
        finally:
            auditor.build_report = original_build_report

    def test_exported_canonical_json_rebind_cannot_collapse_verifier(self):
        data = packet()
        data["runs"][0]["provenance"]["pull_requests"] = [
            {"number": 1, "state": "OPEN", "current_head_sha": SHA_A}
        ]
        report = auditor.build_report(data)
        tampered = copy.deepcopy(report)
        tampered["rows"][0]["decision"] = "SAFE_TO_CANCEL"
        tampered["rows"][0]["reasons"] = ["ALL_ASSOCIATED_PRS_CLOSED_OR_STALE"]
        tampered["counts"] = {"HOLD": 0, "SAFE_TO_CANCEL": 1}

        original_canonical_json = auditor.canonical_json
        auditor.canonical_json = lambda _value: b"{}"
        try:
            tampered["input_digest"] = auditor.sha256_hex(
                auditor.canonical_json(tampered["retained_input"])
            )
            unsigned = dict(tampered)
            unsigned.pop("report_receipt")
            tampered["report_receipt"] = auditor.sha256_hex(
                auditor.canonical_json(unsigned)
            )
            with self.assertRaises(auditor.AuditError):
                auditor.verify_report(tampered)
        finally:
            auditor.canonical_json = original_canonical_json


if __name__ == "__main__":
    unittest.main()
