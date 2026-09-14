from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from revenue.wri_open_timber_portal.cli import main

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "public_known.json"


class CliTests(unittest.TestCase):
    def test_compile_json_and_verify(self):
        output = io.StringIO()
        with redirect_stdout(output):
            rc = main(["compile", str(FIXTURE), "--format", "json"])
        self.assertEqual(rc, 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["technical_readiness"], "TECHNICALLY_READY")
        self.assertEqual(report["submission_readiness"], "HOLD_CONTROLLING_SOURCE")
        with tempfile.TemporaryDirectory() as td:
            report_path = Path(td) / "report.json"
            report_path.write_text(json.dumps(report), encoding="utf-8")
            verified = io.StringIO()
            with redirect_stdout(verified):
                verify_rc = main(["verify", str(FIXTURE), str(report_path)])
            self.assertEqual(verify_rc, 0)
            self.assertEqual(json.loads(verified.getvalue())["verdict"], "CURRENT_TECHNICAL_CARRIER_VERIFIED")

    def test_compile_markdown(self):
        output = io.StringIO()
        with redirect_stdout(output):
            rc = main(["compile", str(FIXTURE), "--format", "markdown"])
        self.assertEqual(rc, 0)
        self.assertIn("# World Resources Institute", output.getvalue())
        self.assertIn("HOLD_CONTROLLING_SOURCE", output.getvalue())
        self.assertIn("Authority ceiling", output.getvalue())

    @unittest.skipUnless(hasattr(os, "symlink") and hasattr(os, "O_NOFOLLOW"), "requires symlink + O_NOFOLLOW")
    def test_final_component_symlink_refused(self):
        with tempfile.TemporaryDirectory() as td:
            link = Path(td) / "packet.json"
            os.symlink(FIXTURE, link)
            err = io.StringIO()
            with redirect_stderr(err):
                rc = main(["compile", str(link)])
            self.assertEqual(rc, 4)
            self.assertIn("ERROR:", err.getvalue())

    def test_duplicate_json_key_file_refused(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.json"
            bad.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err):
                rc = main(["compile", str(bad)])
            self.assertEqual(rc, 4)
            self.assertIn("duplicate JSON key", err.getvalue())


if __name__ == "__main__":
    unittest.main()
