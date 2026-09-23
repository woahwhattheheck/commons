"""Real-engine and real-process tests for the synthetic delivery walkthrough."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from coordination import outbound_delivery_truth as engine
from coordination import outbound_delivery_truth_demo as demo

ROOT = Path(__file__).resolve().parent


class DeliveryWalkthroughTests(unittest.TestCase):
    def test_all_eleven_cases_replay_with_the_real_engine(self):
        report = demo.build_demo()
        self.assertIs(report["synthetic"], True)
        self.assertEqual(report["case_count"], 11)
        self.assertEqual(len(report["cases"]), 11)
        self.assertEqual(len({row["id"] for row in report["cases"]}), 11)
        for row in report["cases"]:
            with self.subTest(case=row["id"]):
                self.assertIs(row["synthetic"], True)
                self.assertIs(engine.verify_delivery_truth(row["input"], row["artifact"])["valid"], True)
                self.assertEqual(row["artifact"], engine.compile_delivery_truth(row["input"]))
                self.assertTrue(all(v is False for v in row["artifact"]["authority"].values()))

    def test_every_delivery_state_is_exercised(self):
        self.assertEqual({r["artifact"]["delivery_state"] for r in demo.build_demo()["cases"]}, {
            "UNSENT", "PROVIDER_SUBMITTED_PENDING_DELIVERY", "DELIVERY_UNKNOWN",
            "DELIVERY_FAILED", "DELIVERED_EVIDENCE",
        })

    def test_legacy_never_manufactures_submission_receipt(self):
        rows = [r for r in demo.build_demo()["cases"] if r["input"]["legacy_local_sent"] is not None]
        self.assertEqual(len(rows), 4)
        for row in rows:
            p = row["artifact"]["collision_projection"]
            self.assertIs(p["provider_submission_observed"], False)
            self.assertIs(p["same_route_dedupe_hold"], True)

    def test_conflicting_terminals_stay_unknown_in_any_order(self):
        for row in demo.build_demo()["cases"]:
            if "conflicting" not in row["id"]:
                continue
            packet = deepcopy(row["input"])
            packet["events"].reverse()
            actual = engine.compile_delivery_truth(packet)
            self.assertEqual(actual, row["artifact"])
            self.assertEqual(actual["reason"], "conflicting_terminal_evidence")

    def test_results_are_fresh_and_repeatable(self):
        first = demo.build_demo()
        expected = deepcopy(first)
        first["cases"][0]["artifact"]["authority"]["send_authorized"] = True
        first["cases"][1]["input"]["submission"]["recipient"] = "changed-token"
        self.assertEqual(demo.build_demo(), expected)

    def test_changed_projection_is_not_silently_presented(self):
        original = engine.compile_delivery_truth
        def changed(packet):
            out = original(packet)
            out["collision_projection"]["counts_as_contacted"] = True
            return out
        with patch.object(engine, "compile_delivery_truth", changed):
            with self.assertRaisesRegex(demo.DemoError, "documented outcome"):
                demo.build_demo()

    def test_false_must_not_be_replaced_by_integer_zero(self):
        original = engine.compile_delivery_truth
        def changed(packet):
            out = original(packet)
            out["collision_projection"]["provider_submission_observed"] = 0
            return out
        with patch.object(engine, "compile_delivery_truth", changed):
            with self.assertRaises(demo.DemoError):
                demo.build_demo()

    def test_external_action_flags_cannot_be_hidden_by_empty_mapping(self):
        original = engine.compile_delivery_truth
        def changed(packet):
            out = original(packet)
            out["authority"] = {}
            return out
        with patch.object(engine, "compile_delivery_truth", changed):
            with self.assertRaisesRegex(demo.DemoError, "external action"):
                demo.build_demo()

    def test_failed_replay_does_not_emit_a_successful_demo(self):
        with patch.object(engine, "verify_delivery_truth", return_value={"valid": False}):
            with self.assertRaisesRegex(demo.DemoError, "did not verify"):
                demo.build_demo()

    def test_domain_failure_is_reported_as_nonzero_without_traceback(self):
        stderr = io.StringIO()
        with patch.object(demo, "build_demo", side_effect=demo.DemoError("synthetic mismatch")):
            with redirect_stderr(stderr):
                self.assertEqual(demo.main(["--format", "json"]), 2)
        self.assertIn("synthetic mismatch", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_markdown_keeps_synthetic_unknown_and_no_action_boundaries(self):
        report = demo.build_demo()
        text = demo.render_markdown(report)
        self.assertIn("All inputs are fictional", text)
        self.assertIn("DELIVERY_UNKNOWN", text)
        self.assertIn("not a reply, acceptance or sale", text)
        for row in report["cases"]:
            self.assertIn(row["id"], text)
            self.assertIn(row["explanation"], text)

    def test_module_direct_and_optimized_cli_outputs_are_identical(self):
        commands = [
            [sys.executable, "-m", "coordination.outbound_delivery_truth_demo", "--format", "json"],
            [sys.executable, "-O", "-m", "coordination.outbound_delivery_truth_demo", "--format", "json"],
            [sys.executable, str(ROOT / "coordination" / "outbound_delivery_truth_demo.py"), "--format", "json"],
        ]
        outputs = []
        for command in commands:
            result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(result.stderr, b"")
            outputs.append(result.stdout)
            self.assertEqual(json.loads(result.stdout), demo.build_demo())
        self.assertEqual(len({hashlib.sha256(o).hexdigest() for o in outputs}), 1)

    def test_default_cli_is_readable_and_does_not_need_an_output_directory(self):
        result = subprocess.run(
            [sys.executable, "-m", "coordination.outbound_delivery_truth_demo"],
            cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, demo.render_markdown(demo.build_demo()))

    def test_unknown_format_is_rejected(self):
        result = subprocess.run(
            [sys.executable, "-m", "coordination.outbound_delivery_truth_demo", "--format", "send"],
            cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
