from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "revenue" / "uark_rfp09112026_cmmc"
CURRENT_PATH = PKG / "current_authority.py"
FIXTURE_PATH = PKG / "synthetic_candidate.json"


def load_current():
    spec = importlib.util.spec_from_file_location("uark_current_entry_test", CURRENT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UarkCurrentEntryTests(unittest.TestCase):
    def test_imported_main_and_current_renderer_fail_closed(self) -> None:
        current = load_current()
        with self.assertRaisesRegex(current.InputError, "CLI-only"):
            current.render_markdown({})
        current._REQUIRE_DIRECT_ISOLATED_ENTRY = lambda: None
        self.assertEqual(current.main(["compile", str(FIXTURE_PATH)]), 2)

    def test_historical_renderer_is_visibly_not_current(self) -> None:
        current = load_current()
        packet = current.compile_historical(
            json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        )
        rendered = current.render_markdown_historical(packet)
        self.assertIn("HISTORICAL / INTEGRITY ONLY", rendered)
        self.assertIn("NOT CURRENT", rendered)

    def test_direct_isolated_current_markdown_is_truth_labeled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            packet = Path(td) / "packet.json"
            markdown = Path(td) / "packet.md"
            proc = subprocess.run(
                [sys.executable, "-I", "-S", str(CURRENT_PATH), "compile",
                 str(FIXTURE_PATH), "--json-out", str(packet),
                 "--markdown-out", str(markdown)],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            rendered = markdown.read_text(encoding="utf-8")
            self.assertIn("CURRENT qualification", rendered)
            self.assertNotIn("HISTORICAL / INTEGRITY ONLY", rendered)


if __name__ == "__main__":
    unittest.main()
