"""Failure-receipt regressions; no SDK installation, network, or provider spend."""
from __future__ import annotations

import hashlib
import io
import json
import sys
import unittest
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import test_e2b_executor as fixtures
from tools.e2b_executor import executor
from tools.e2b_executor.__main__ import main


@dataclass
class SDKCommandExit(Exception):
    """Official CommandExitException result fields, supplied by a fake SDK."""
    stderr: str
    stdout: str
    exit_code: int
    error: str | None = None

    def __str__(self):
        return f"Command exited with code {self.exit_code}: {self.stderr}"


def fake_sdk():
    module = ModuleType("e2b")
    module.CommandExitException = SDKCommandExit
    return module


class FailureReceiptTests(unittest.TestCase):
    setUp = fixtures.E2BExecutorTests.setUp
    run_job = fixtures.E2BExecutorTests.run_job

    def check_receipt(self, receipt):
        payload = dict(receipt)
        digest = payload.pop("receipt_sha256")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode()
        self.assertEqual(digest, hashlib.sha256(encoded).hexdigest())
        self.assertFalse(receipt["green"])
        self.assertTrue(receipt["kill_attempted"])
        self.assertFalse(receipt["truth_boundary"]["git_commit_binding_verified"])

    def test_completed_command_survives_later_transport_failure(self):
        sandbox = fixtures.FakeSandbox(self.digest, user_results=[
            SimpleNamespace(exit_code=0, stdout="first completed", stderr=""),
            TimeoutError("transport interrupted"),
        ])
        with patch.dict(sys.modules, {"e2b": fake_sdk()}):
            receipt, _ = self.run_job(sandbox)
        self.check_receipt(receipt)
        self.assertEqual(receipt["error"]["kind"], "TimeoutError")
        self.assertEqual(len(receipt["commands"]), 1)
        self.assertEqual(receipt["commands"][0]["stdout_excerpt"], "first completed")
        self.assertTrue(receipt["kill_succeeded"])

    def test_sdk_nonzero_exit_retains_both_outputs_and_stops(self):
        sandbox = fixtures.FakeSandbox(self.digest, user_results=[
            SDKCommandExit("assertion failed", "test progress", 7),
            SimpleNamespace(exit_code=0, stdout="must not execute", stderr=""),
        ])
        with patch.dict(sys.modules, {"e2b": fake_sdk()}):
            receipt, _ = self.run_job(sandbox)
        self.check_receipt(receipt)
        self.assertEqual(receipt["error"]["kind"], "COMMAND_FAILED")
        self.assertEqual(len(receipt["commands"]), 1)
        result = receipt["commands"][0]
        self.assertEqual((result["exit_code"], result["stdout_excerpt"],
                          result["stderr_excerpt"]), (7, "test progress", "assertion failed"))
        self.assertEqual(result["stdout_sha256"], hashlib.sha256(b"test progress").hexdigest())
        self.assertEqual(len(sandbox.commands.user_results), 1)

    def test_success_then_sdk_failure_preserves_order_and_redaction(self):
        secret = "synthetic-e2b-secret"
        sandbox = fixtures.FakeSandbox(self.digest, user_results=[
            SimpleNamespace(exit_code=0, stdout="first", stderr=""),
            SDKCommandExit(f"stderr {secret}", f"stdout {secret}", 23),
        ])
        with patch.dict(sys.modules, {"e2b": fake_sdk()}):
            receipt, _ = self.run_job(sandbox, api_key=secret)
        self.check_receipt(receipt)
        self.assertEqual([row["order"] for row in receipt["commands"]], [0, 1])
        self.assertEqual([row["exit_code"] for row in receipt["commands"]], [0, 23])
        self.assertNotIn(secret, json.dumps(receipt))
        self.assertIn("[REDACTED_E2B_API_KEY]", receipt["commands"][1]["stderr_excerpt"])

    def test_exception_with_result_shaped_attributes_is_not_command_success(self):
        error = RuntimeError("provider disconnected")
        error.exit_code, error.stdout, error.stderr = 0, "not execution evidence", ""
        sandbox = fixtures.FakeSandbox(self.digest, user_results=[error])
        with patch.dict(sys.modules, {"e2b": fake_sdk()}):
            receipt, _ = self.run_job(sandbox)
        self.check_receipt(receipt)
        self.assertEqual(receipt["error"]["kind"], "RuntimeError")
        self.assertEqual(receipt["commands"], [])

    def test_sdk_exception_cannot_report_zero_or_malformed_exit(self):
        for code in (0, False, True, None, "7"):
            with self.subTest(code=code):
                sandbox = fixtures.FakeSandbox(self.digest, user_results=[
                    SDKCommandExit("invalid", "", code),
                ])
                with patch.dict(sys.modules, {"e2b": fake_sdk()}):
                    receipt, _ = self.run_job(sandbox)
                self.check_receipt(receipt)
                self.assertEqual(receipt["commands"], [])
                self.assertEqual(receipt["error"]["kind"], "ProviderExecutionError")

    def test_missing_optional_sdk_preserves_original_exception(self):
        sandbox = fixtures.FakeSandbox(self.digest, user_results=[TimeoutError("offline")])
        with patch.dict(sys.modules, {"e2b": None}):
            receipt, _ = self.run_job(sandbox)
        self.check_receipt(receipt)
        self.assertEqual(receipt["error"]["kind"], "TimeoutError")

    def test_completed_receipts_survive_later_malformed_result(self):
        sandbox = fixtures.FakeSandbox(self.digest, user_results=[
            SimpleNamespace(exit_code=0, stdout="completed", stderr=""),
            SimpleNamespace(exit_code=False, stdout="invalid result", stderr=""),
        ])
        receipt, _ = self.run_job(sandbox)
        self.check_receipt(receipt)
        self.assertEqual(len(receipt["commands"]), 1)
        self.assertEqual(receipt["error"]["kind"], "ProviderExecutionError")

    def test_transport_and_teardown_failure_keep_partial_results(self):
        sandbox = fixtures.FakeSandbox(self.digest, user_results=[
            SimpleNamespace(exit_code=0, stdout="completed", stderr=""),
            TimeoutError("transport failure"),
        ], kill_error=RuntimeError("teardown failure"))
        with patch.dict(sys.modules, {"e2b": fake_sdk()}):
            receipt, _ = self.run_job(sandbox)
        self.check_receipt(receipt)
        self.assertEqual(len(receipt["commands"]), 1)
        self.assertEqual(receipt["error"]["kind"], "TimeoutError")
        self.assertFalse(receipt["kill_succeeded"])

    def test_internal_stage_rejects_boolean_exit_code(self):
        sandbox = SimpleNamespace(commands=SimpleNamespace(run=lambda *_a, **_kw:
            SimpleNamespace(exit_code=False, stdout="not a valid result", stderr="")))
        with self.assertRaises(executor.ProviderExecutionError):
            executor._checked_internal_stage(sandbox, "MANIFEST", "pass", 1)

    def test_sdk_preflight_failure_stays_non_green_without_user_commands(self):
        sandbox = fixtures.FakeSandbox(self.digest)
        sandbox.commands.run = lambda *_a, **_kw: (_ for _ in ()).throw(
            SDKCommandExit("preflight failure", "", 91))
        with patch.dict(sys.modules, {"e2b": fake_sdk()}):
            receipt, _ = self.run_job(sandbox)
        self.check_receipt(receipt)
        self.assertEqual(receipt["commands"], [])
        self.assertEqual(receipt["error"]["kind"], "ProviderExecutionError")
        self.assertTrue(receipt["kill_succeeded"])

    def test_extreme_json_depth_is_structured_validation_failure(self):
        raw = b"[" * 2000 + b"0" + b"]" * 2000
        with self.assertRaises(executor.JobValidationError):
            executor.load_job_packet_bytes(raw)

    def test_cli_extreme_depth_returns_json_not_traceback(self):
        raw = "[" * 2000 + "0" + "]" * 2000
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO(raw)), patch("sys.stdout", output):
            code = main([])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())["error"], "JobValidationError")


if __name__ == "__main__":
    unittest.main()
