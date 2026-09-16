# SPDX-License-Identifier: Apache-2.0
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import current_authority
from cli import main
from test_qualification import NOW, qualified_payload


class CliTests(unittest.TestCase):
    def test_public_fixture_holds_with_exit_3(self):
        fixture = Path(__file__).parent / "fixtures" / "public_listing_only.json"
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as td, mock.patch.object(
            current_authority, "TRUSTED_ROOT_PATH", Path(td) / "missing.sha256"
        ), mock.patch.object(current_authority, "_utc_now_string", return_value=NOW), contextlib.redirect_stdout(out):
            code = main([str(fixture)])
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out.getvalue())["decision"], "HOLD")

    def test_ready_bundle_exit_0_and_atomic_output_with_retained_root(self):
        p = qualified_payload()
        root = p["requirements_manifest"]["completeness_attestation"]["sha256"]
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            src = td / "bundle.json"; dst = td / "receipt.json"
            root_path = td / "trusted_completeness.sha256"
            src.write_text(json.dumps(p), encoding="utf-8")
            root_path.write_text(root + "\n", encoding="utf-8")
            with mock.patch.object(current_authority, "TRUSTED_ROOT_PATH", root_path), mock.patch.object(
                current_authority, "_utc_now_string", return_value=NOW
            ):
                code = main([str(src), "--output", str(dst)])
            self.assertEqual(code, 0)
            receipt = json.loads(dst.read_text())
            self.assertEqual(receipt["decision"], "READY_FOR_INTERNAL_BID_REVIEW")
            self.assertTrue(receipt["current_authority"])
            self.assertEqual(receipt["trusted_completeness_root_sha256"], root)
            self.assertFalse((td / "receipt.json.tmp").exists())

    def test_cli_rejects_caller_clock_override(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as raised:
            main(["/unused.json", "--evaluated-at", NOW])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("unrecognized arguments", err.getvalue())

    def test_malformed_json_exit_2(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "bad.json"; src.write_text("{", encoding="utf-8")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = main([str(src)])
            self.assertEqual(code, 2)
            self.assertIn("ERROR:", err.getvalue())

    def test_missing_file_exit_2(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main(["/definitely/missing.json"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
