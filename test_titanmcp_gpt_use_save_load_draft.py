#!/usr/bin/env python3
"""Isolated KEEP battery for live titanmcp SAVE DRAFT / LOAD DRAFT buttons.

Does not remint pad runtime, titanmcp.html, or the 1.4.5 setup-schema pin.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

import commons_mcp as cm


ROOT = Path(__file__).resolve().parent
HOST = ROOT / "host" / "titanmcp_save_load_draft.py"
_spec = importlib.util.spec_from_file_location("titanmcp_save_load_draft", HOST)
schema = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(schema)


RECORDED_HTML = """<!doctype html><html><body>
<div class="actions"><button type="button" class="ghost" id="btn-save-draft">SAVE DRAFT</button><button type="button" class="ghost" id="btn-load-draft">LOAD DRAFT</button></div>
<input type="file" id="draft-file" accept=".json,application/json" hidden/>
<script>registerTool()</script>
<p>titanmcp 1.4.5</p>
</body></html>
"""


class TitanmcpGptUseSaveLoadDraftTests(unittest.TestCase):
    def test_recorded_markup_classifies_match(self) -> None:
        row = schema.classify_html(RECORDED_HTML)
        self.assertTrue(row["ok"])
        self.assertTrue(row["has_save_draft"])
        self.assertTrue(row["has_load_draft"])
        self.assertTrue(row["has_draft_file"])
        self.assertTrue(row["has_register_tool"])
        self.assertEqual(row["missing"], [])

    def test_missing_save_draft_is_finder_failed(self) -> None:
        row = schema.classify_html("<html>registerTool titanmcp LOAD DRAFT</html>")
        self.assertFalse(row["ok"])
        self.assertFalse(row["has_save_draft"])
        self.assertIn(schema.BUTTON_MARKUP, row["missing"])

    def test_button_ids_are_exact(self) -> None:
        self.assertIn('id="btn-save-draft">SAVE DRAFT</button>', schema.BUTTON_MARKUP)
        self.assertIn('id="btn-load-draft">LOAD DRAFT</button>', schema.BUTTON_MARKUP)
        self.assertIn('id="draft-file"', schema.DRAFT_FILE_INPUT)

    def test_commons_identity_keep(self) -> None:
        self.assertEqual(cm.SERVER_NAME, "commons")
        self.assertEqual(cm.SERVER_VERSION, "1.4.0")

    def test_does_not_remint_listed_keep_paths(self) -> None:
        for rel in schema.DO_NOT_REMINT:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_titanmcp_html_unread_no_remint(self) -> None:
        text = (ROOT / "titanmcp.html").read_text(encoding="utf-8")
        self.assertIn("titanmcp 1.4.5", text)
        self.assertIn("webmcp-pad.vercel.app", text)
        self.assertNotIn("btn-save-draft", text)

    def test_bake_deploy_go_refused_sent_zero(self) -> None:
        for flag in ("--bake", "--deploy", "--go"):
            proc = subprocess.run(
                [sys.executable, str(HOST), flag],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["refused"], flag)
            self.assertEqual(payload["verdict"], "REFUSED")


if __name__ == "__main__":
    unittest.main()
