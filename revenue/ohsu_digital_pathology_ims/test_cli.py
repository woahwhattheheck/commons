# SPDX-License-Identifier: Apache-2.0
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from cli import main
from test_qualification import NOW, qualified_payload


class CliTests(unittest.TestCase):
    def test_public_fixture_holds_with_exit_3(self):
        fixture = Path(__file__).parent / "fixtures" / "public_listing_only.json"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main([str(fixture), "--evaluated-at", NOW])
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out.getvalue())["decision"], "HOLD")

    def test_ready_bundle_exit_0_and_atomic_output(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            src = td / "bundle.json"; dst = td / "receipt.json"
            src.write_text(json.dumps(qualified_payload()), encoding="utf-8")
            code = main([str(src), "--evaluated-at", NOW, "--output", str(dst)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(dst.read_text())["decision"], "READY_FOR_INTERNAL_BID_REVIEW")
            self.assertFalse((td / "receipt.json.tmp").exists())

    def test_malformed_json_exit_2(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "bad.json"; src.write_text("{", encoding="utf-8")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = main([str(src), "--evaluated-at", NOW])
            self.assertEqual(code, 2)
            self.assertIn("ERROR:", err.getvalue())

    def test_missing_file_exit_2(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main(["/definitely/missing.json", "--evaluated-at", NOW])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
