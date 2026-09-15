from __future__ import annotations

import importlib
import unittest

import tools.mcp_transcript_audit as _package
import tools.mcp_transcript_audit._audit_core as _core
import tools.mcp_transcript_audit.audit as _facade
from _mcp_transcript_audit_regression_suite import reason_codes
from test_mcp_transcript_audit import (
    _fractional_request_source,
    _fractional_response_source,
    _historical_fractional_pass_receipt,
)


class RuntimeDependencyBindingTests(unittest.TestCase):
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

    def test_runtime_dependency_rebinding_cannot_change_exported_policy(self):
        old_audit = _package.audit_transcript
        old_verify = _package.verify_receipt

        def trap(*_args, **_kwargs):
            raise AssertionError("mutable module runtime dependency was used")

        fake_builtins = type(
            "FakeBuiltins",
            (),
            {"exec": staticmethod(trap), "compile": staticmethod(trap)},
        )()
        try:
            _core.exec = trap
            _core.compile = trap
            _core._builtins = fake_builtins
            self.assert_policy(old_audit, old_verify)

            reloaded_core = importlib.reload(_core)
            self.assert_policy(old_audit, old_verify)
            self.assert_policy(
                reloaded_core.audit_transcript, reloaded_core.verify_receipt
            )

            reloaded_facade = importlib.reload(_facade)
            self.assert_policy(
                reloaded_facade.audit_transcript, reloaded_facade.verify_receipt
            )
        finally:
            for name in ("exec", "compile"):
                if hasattr(_core, name):
                    delattr(_core, name)
            importlib.reload(_core)
            importlib.reload(_facade)


if __name__ == "__main__":
    unittest.main()
