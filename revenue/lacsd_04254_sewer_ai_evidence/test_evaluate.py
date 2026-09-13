from __future__ import annotations

import ast
import copy
import hashlib
import io
import json
import math
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKAGE_DIR))

import evaluate  # noqa: E402


class EvidenceEvaluatorTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.document = evaluate.load_json(PACKAGE_DIR / "fixtures.json")
        self.policy = evaluate.load_json(PACKAGE_DIR / "policy.json")
        self.evaluator_sha = hashlib.sha256(
            (PACKAGE_DIR / "evaluate.py").read_bytes()
        ).hexdigest()

    def evaluate(self, document=None, policy=None):
        return evaluate.evaluate_document(
            self.document if document is None else document,
            self.policy if policy is None else policy,
            evaluator_sha256=self.evaluator_sha,
        )

    def scenario(self, receipt, scenario_id):
        return next(
            item for item in receipt["scenarios"]
            if item["scenario_id"] == scenario_id
        )

    def test_canonical_suite_is_ready(self):
        receipt = self.evaluate()
        self.assertEqual("READY", receipt["status"])
        self.assertEqual([], receipt["hold_reasons"])
        self.assertEqual(
            {
                "scenarios_total": 10,
                "assertions_passed": 10,
                "assertions_failed": 0,
                "work_intents_total": 3,
                "unique_work_intent_ids": 3,
                "duplicate_work_intent_ids": 0,
                "duplicate_packets_suppressed": 1,
            },
            receipt["metrics"],
        )

    def test_receipt_is_byte_deterministic(self):
        first = evaluate.canonical_text(self.evaluate())
        second = evaluate.canonical_text(self.evaluate())
        self.assertEqual(first.encode("utf-8"), second.encode("utf-8"))

    def test_checked_in_example_receipt_matches(self):
        expected = evaluate.load_json(PACKAGE_DIR / "example_receipt.json")
        self.assertEqual(expected, self.evaluate())

    def test_actionable_duplicate_packet_mints_one_intent(self):
        item = self.scenario(
            self.evaluate(), "blockage-drift-duplicate-retransmission"
        )
        self.assertTrue(item["assertion"]["passed"])
        self.assertEqual(1, item["result"]["duplicates_suppressed"])
        self.assertEqual(1, len(item["result"]["work_intents"]))
        intent = item["result"]["work_intents"][0]
        self.assertTrue(intent["intent_only"])
        self.assertFalse(intent["external_execution"])
        self.assertEqual(intent["work_intent_id"], intent["idempotency_key"])

    def test_retransmission_position_does_not_change_intent_id(self):
        baseline = self.scenario(
            self.evaluate(), "blockage-drift-duplicate-retransmission"
        )["result"]["work_intents"][0]["work_intent_id"]
        mutated = copy.deepcopy(self.document)
        scenario = mutated["fixtures"][0]
        duplicate = scenario["packets"].pop(2)
        scenario["packets"].append(duplicate)
        replay = self.scenario(
            self.evaluate(mutated), "blockage-drift-duplicate-retransmission"
        )["result"]["work_intents"][0]["work_intent_id"]
        self.assertEqual(baseline, replay)

    def test_conflicting_packet_id_fails_closed(self):
        item = self.scenario(self.evaluate(), "conflicting-retransmission-hold")
        self.assertEqual("HOLD", item["result"]["decision"])
        self.assertEqual("CONFLICTING_PACKET_ID", item["result"]["hold_reason"])
        self.assertEqual([], item["result"]["work_intents"])

    def test_every_hold_has_zero_work_intents(self):
        receipt = self.evaluate()
        for item in receipt["scenarios"]:
            if item["result"]["decision"] == "HOLD":
                self.assertEqual([], item["result"]["work_intents"], item["scenario_id"])

    def test_threshold_edge_is_inclusive(self):
        item = self.scenario(self.evaluate(), "blockage-threshold-edge")
        self.assertEqual("WORK_INTENT", item["result"]["decision"])
        self.assertEqual(0.2, item["result"]["evidence"]["flow_drop_ratio"])
        self.assertEqual(15.0, item["result"]["evidence"]["level_rise_pct"])
        self.assertEqual(1.0, item["result"]["evidence"]["max_rain_mm_15m"])

    def test_below_threshold_produces_no_action(self):
        mutated = copy.deepcopy(self.document)
        scenario = next(
            item for item in mutated["fixtures"]
            if item["scenario_id"] == "blockage-threshold-edge"
        )
        scenario["packets"][-1]["flow_lps"] = 80.0001
        scenario["expected"] = {
            "decision": "NO_ACTION",
            "anomaly_class": "NONE",
            "work_intents": 0,
            "hold_reason": None,
        }
        receipt = self.evaluate(mutated)
        item = self.scenario(receipt, "blockage-threshold-edge")
        self.assertEqual("READY", receipt["status"])
        self.assertEqual("NO_ACTION", item["result"]["decision"])

    def test_stale_evidence_holds(self):
        item = self.scenario(self.evaluate(), "stale-evidence-hold")
        self.assertEqual("STALE_EVIDENCE", item["result"]["hold_reason"])
        self.assertGreater(
            item["result"]["evidence"]["age_seconds"],
            self.policy["freshness_max_seconds"],
        )

    def test_evaluation_before_last_packet_holds(self):
        mutated = copy.deepcopy(self.document)
        scenario = mutated["fixtures"][2]
        scenario["evaluation_at"] = "2026-09-13T12:14:59Z"
        scenario["expected"] = {
            "decision": "HOLD",
            "anomaly_class": "UNDETERMINED",
            "work_intents": 0,
            "hold_reason": "EVALUATION_BEFORE_LAST_PACKET",
        }
        receipt = self.evaluate(mutated)
        self.assertEqual("READY", receipt["status"])
        self.assertEqual(
            "EVALUATION_BEFORE_LAST_PACKET",
            self.scenario(receipt, "normal-diurnal-control")["result"]["hold_reason"],
        )

    def test_insufficient_points_hold(self):
        mutated = copy.deepcopy(self.document)
        scenario = mutated["fixtures"][2]
        scenario["packets"] = scenario["packets"][:3]
        scenario["expected"] = {
            "decision": "HOLD",
            "anomaly_class": "UNDETERMINED",
            "work_intents": 0,
            "hold_reason": "INSUFFICIENT_POINTS",
        }
        receipt = self.evaluate(mutated)
        self.assertEqual("READY", receipt["status"])

    def test_unapproved_expected_label_is_rejected(self):
        mutated = copy.deepcopy(self.document)
        mutated["fixtures"][0]["expected"]["anomaly_class"] = "MAGIC_OVERFLOW"
        with self.assertRaisesRegex(evaluate.ValidationError, "not approved"):
            self.evaluate(mutated)

    def test_nonfinite_value_is_rejected(self):
        mutated = copy.deepcopy(self.document)
        mutated["fixtures"][0]["packets"][0]["flow_lps"] = math.nan
        with self.assertRaisesRegex(evaluate.ValidationError, "must be finite"):
            self.evaluate(mutated)

    def test_malformed_timestamp_is_rejected(self):
        mutated = copy.deepcopy(self.document)
        mutated["fixtures"][0]["packets"][0]["observed_at"] = "09/13/2026 12:00"
        with self.assertRaisesRegex(evaluate.ValidationError, "invalid format"):
            self.evaluate(mutated)

    def test_duplicate_scenario_id_is_rejected(self):
        mutated = copy.deepcopy(self.document)
        mutated["fixtures"][1]["scenario_id"] = mutated["fixtures"][0]["scenario_id"]
        with self.assertRaisesRegex(evaluate.ValidationError, "duplicate scenario_id"):
            self.evaluate(mutated)

    def test_unknown_document_key_is_rejected(self):
        mutated = copy.deepcopy(self.document)
        mutated["production_endpoint"] = "https://example.invalid"
        with self.assertRaisesRegex(evaluate.ValidationError, "extra=production_endpoint"):
            self.evaluate(mutated)

    def test_policy_cannot_enable_external_execution(self):
        mutated = copy.deepcopy(self.policy)
        mutated["external_execution"] = True
        with self.assertRaisesRegex(evaluate.ValidationError, "must remain false"):
            self.evaluate(policy=mutated)

    def test_policy_cannot_add_action(self):
        mutated = copy.deepcopy(self.policy)
        mutated["allowed_intents"].append("AUTO_DISPATCH_CREW")
        with self.assertRaisesRegex(evaluate.ValidationError, "must be exactly"):
            self.evaluate(policy=mutated)

    def test_policy_gap_cannot_exceed_freshness(self):
        mutated = copy.deepcopy(self.policy)
        mutated["max_gap_seconds"] = mutated["freshness_max_seconds"] + 1
        with self.assertRaisesRegex(evaluate.ValidationError, "cannot exceed"):
            self.evaluate(policy=mutated)

    def test_duplicate_json_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"schema_version":"a","schema_version":"b"}', encoding="utf-8")
            with self.assertRaisesRegex(evaluate.ValidationError, "duplicate JSON key"):
                evaluate.load_json(path)

    def test_invalid_cli_does_not_publish_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bad_input = root / "bad.json"
            output = root / "receipt.json"
            bad_input.write_text('{"schema_version":', encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = evaluate.main(
                    [
                        "--input", str(bad_input),
                        "--policy", str(PACKAGE_DIR / "policy.json"),
                        "--output", str(output),
                    ]
                )
            self.assertEqual(2, code)
            self.assertFalse(output.exists())
            self.assertIn("HOLD:", stderr.getvalue())

    def test_cli_reproduces_checked_in_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "receipt.json"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = evaluate.main(["--output", str(output)])
            self.assertEqual(0, code)
            self.assertEqual("", stdout.getvalue())
            self.assertEqual(
                evaluate.load_json(PACKAGE_DIR / "example_receipt.json"),
                evaluate.load_json(output),
            )

    def test_source_has_no_network_or_process_surface(self):
        source = (PACKAGE_DIR / "evaluate.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_imports = {
            "socket", "ssl", "http", "urllib", "requests", "subprocess",
            "asyncio", "ftplib", "smtplib", "telnetlib",
        }
        imported_roots = set()
        os_calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
            ):
                os_calls.add(node.func.attr)
        self.assertEqual(set(), imported_roots & forbidden_imports)
        self.assertLessEqual(os_calls, {"fdopen", "fsync", "replace", "unlink"})

    def test_nonclaims_and_lineage_are_explicit(self):
        receipt = self.evaluate()
        self.assertEqual("NOT_CLAIMED", receipt["scope"]["prime_bid_status"])
        self.assertEqual("NOT_CLAIMED", receipt["scope"]["buyer_acceptance"])
        self.assertFalse(receipt["scope"]["external_execution"])
        self.assertFalse(receipt["scope"]["operational_control"])
        self.assertEqual(5, len(receipt["non_claims"]))
        self.assertRegex(receipt["lineage"]["input_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(receipt["lineage"]["policy_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(receipt["lineage"]["evaluator_sha256"], r"^[0-9a-f]{64}$")


    def test_manifest_hashes_every_authored_artifact(self):
        manifest = evaluate.load_json(PACKAGE_DIR / "manifest.json")
        self.assertEqual("lacsd-04254-package-manifest-v1", manifest["schema_version"])
        self.assertEqual("LACSD-04254-SEWER-AI-EVIDENCE-ZNCX6P4-20260913", manifest["operation"])
        expected_paths = {
            "README.md",
            "evaluate.py",
            "policy.json",
            "fixtures.json",
            "example_receipt.json",
            "test_evaluate.py",
        }
        entries = manifest["artifacts"]
        self.assertEqual(expected_paths, set(entries))
        for relative_path, metadata in entries.items():
            data = (PACKAGE_DIR / relative_path).read_bytes()
            self.assertEqual(len(data), metadata["bytes"], relative_path)
            self.assertEqual(
                hashlib.sha256(data).hexdigest(),
                metadata["sha256"],
                relative_path,
            )


if __name__ == "__main__":
    unittest.main()
