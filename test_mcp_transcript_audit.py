from __future__ import annotations

import importlib
import os
import subprocess
import sys
import textwrap
import unittest
from importlib import resources
from pathlib import Path

import _mcp_transcript_audit_regression_suite as _legacy
from _mcp_transcript_audit_regression_suite import *  # noqa: F401,F403

import tools.mcp_transcript_audit as _package
import tools.mcp_transcript_audit._audit_core as _core
import tools.mcp_transcript_audit.audit as _facade


def _fractional_request_source():
    events = valid_events()
    events[3] = (CLIENT, {"jsonrpc": "2.0", "id": 1.5, "method": "tools/list", "params": {}})
    events[4] = (SERVER, {"jsonrpc": "2.0", "id": 1.5, "result": {"tools": []}})
    return capture(events)


def _fractional_response_source():
    events = valid_events()
    events[3] = (CLIENT, {"jsonrpc": "2.0", "id": 12, "method": "tools/list", "params": {}})
    events[4] = (SERVER, {"jsonrpc": "2.0", "id": 12.5, "result": {"tools": []}})
    return capture(events)


def _historical_fractional_pass_receipt(source: bytes) -> bytes:
    donor_source = resources.files("tools.mcp_transcript_audit").joinpath(
        "_audit_engine_source.txt"
    ).read_text(encoding="utf-8")
    namespace = {
        "__name__": "tools.mcp_transcript_audit._historical_test_engine",
        "__package__": "tools.mcp_transcript_audit",
        "__file__": "<historical-mcp-transcript-audit-engine>",
    }
    exec(compile(donor_source, namespace["__file__"], "exec"), namespace)
    receipt = namespace["audit_transcript"](source)
    if receipt["status"] != "PASS":
        raise AssertionError("historical donor must demonstrate the withdrawn fractional-ID PASS")
    return namespace["canonical_json_bytes"](receipt)


class RequestIdDomainTests(unittest.TestCase):
    def assert_policy(self, audit, verify):
        request_source = _fractional_request_source()
        response_source = _fractional_response_source()
        for source in (request_source, response_source):
            receipt = audit(source)
            self.assertEqual(receipt["status"], "HOLD")
            self.assertIn("INVALID_CAPTURE_EVENT", reason_codes(receipt))

        historical_receipt = _historical_fractional_pass_receipt(request_source)
        verification = verify(request_source, historical_receipt)
        self.assertFalse(verification["valid"])
        self.assertIn("RECEIPT_RECOMPUTE_MISMATCH", verification["reasons"])

    def test_integral_numeric_id_spelling_roundtrip_passes(self):
        events = valid_events()
        events[3] = (CLIENT, {"jsonrpc": "2.0", "id": 12.0, "method": "tools/list", "params": {}})
        events[4] = (SERVER, {"jsonrpc": "2.0", "id": 12, "result": {"tools": []}})
        self.assertEqual(audit_transcript(capture(events))["status"], "PASS")

    def test_package_facade_and_core_enforce_integer_domain(self):
        for module in (_package, _facade, _core):
            self.assert_policy(module.audit_transcript, module.verify_receipt)

    def test_core_reload_cannot_restore_fractional_policy(self):
        old_audit = _package.audit_transcript
        old_verify = _package.verify_receipt
        reloaded_core = importlib.reload(_core)
        self.assert_policy(old_audit, old_verify)
        self.assert_policy(reloaded_core.audit_transcript, reloaded_core.verify_receipt)

    def test_facade_reload_cannot_restore_fractional_policy(self):
        old_audit = _package.audit_transcript
        old_verify = _package.verify_receipt
        reloaded_facade = importlib.reload(_facade)
        self.assert_policy(old_audit, old_verify)
        self.assert_policy(reloaded_facade.audit_transcript, reloaded_facade.verify_receipt)

    def test_validator_rebinding_cannot_change_exported_policy(self):
        old_audit = _package.audit_transcript
        old_verify = _package.verify_receipt
        permissive = lambda value: ("number", (0, "15", -1))
        try:
            for module in (_package, _facade, _core):
                module._typed_id_key = permissive
                module._original_typed_id_key = permissive
                module._core = type("PermissiveCore", (), {"_typed_id_key": permissive})()
            self.assert_policy(old_audit, old_verify)
            self.assert_policy(_facade.audit_transcript, _facade.verify_receipt)
            self.assert_policy(_core.audit_transcript, _core.verify_receipt)
        finally:
            importlib.reload(_core)
            importlib.reload(_facade)

    def test_engine_resource_is_not_importable(self):
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("tools.mcp_transcript_audit._audit_engine_source")

    def test_fresh_process_core_first_import_order(self):
        script = textwrap.dedent(
            """
            import importlib
            core = importlib.import_module("tools.mcp_transcript_audit._audit_core")
            legacy = importlib.import_module("_mcp_transcript_audit_regression_suite")

            events = legacy.valid_events()
            events[3] = (legacy.CLIENT, {"jsonrpc": "2.0", "id": 1.5, "method": "tools/list", "params": {}})
            events[4] = (legacy.SERVER, {"jsonrpc": "2.0", "id": 1.5, "result": {"tools": []}})
            source = legacy.capture(events)
            if core.audit_transcript(source)["status"] != "HOLD":
                raise SystemExit("core-first fractional request bypass")

            facade = importlib.import_module("tools.mcp_transcript_audit.audit")
            importlib.reload(core)
            importlib.reload(facade)
            core._typed_id_key = lambda value: ("number", (0, "15", -1))
            facade._original_typed_id_key = core._typed_id_key
            if facade.audit_transcript(source)["status"] != "HOLD":
                raise SystemExit("reload/rebind fractional request bypass")
            """
        )
        command = [sys.executable]
        if sys.flags.optimize:
            command.append("-O")
        command.extend(["-c", script])
        env = dict(os.environ)
        repo = str(Path(__file__).resolve().parent)
        env["PYTHONPATH"] = repo + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        completed = subprocess.run(
            command,
            cwd=repo,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


def _iter_tests(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from _iter_tests(test)
        else:
            yield test


def load_tests(loader, _tests, _pattern):
    blocked = {
        "CorrelationHostileTests.test_fractional_numeric_id_roundtrip_passes",
        "CorrelationHostileTests.test_fractional_numeric_id_mismatch_holds",
    }
    suite = unittest.TestSuite()
    for test in _iter_tests(loader.loadTestsFromModule(_legacy)):
        if not any(test.id().endswith(name) for name in blocked):
            suite.addTest(test)
    suite.addTests(loader.loadTestsFromTestCase(RequestIdDomainTests))
    return suite


if __name__ == "__main__":
    unittest.main()
