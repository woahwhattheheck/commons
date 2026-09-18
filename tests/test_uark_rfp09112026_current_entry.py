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
QUALIFIER_PATH = PKG / "qualifier.py"
FIXTURE_PATH = PKG / "synthetic_candidate.json"


def load_current():
    spec = importlib.util.spec_from_file_location("uark_current_entry_test", CURRENT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_qualifier():
    spec = importlib.util.spec_from_file_location("uark_historical_facade_test", QUALIFIER_PATH)
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

    def test_legacy_historical_facade_labels_import_and_refuses_persisted_markdown(self) -> None:
        qualifier = load_qualifier()
        packet = qualifier.compile_historical(
            json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        )
        rendered = qualifier.render_markdown(packet)
        self.assertIn("HISTORICAL / INTEGRITY ONLY", rendered)
        self.assertIn("NOT CURRENT", rendered)

        for optimized in (False, True):
            with self.subTest(optimized=optimized), tempfile.TemporaryDirectory() as td:
                packet_path = Path(td) / "historical.json"
                markdown_path = Path(td) / "historical.md"
                command = [sys.executable]
                if optimized:
                    command.append("-O")
                command.extend(
                    [
                        str(QUALIFIER_PATH),
                        "compile",
                        str(FIXTURE_PATH),
                        "--json-out",
                        str(packet_path),
                        "--markdown-out",
                        str(markdown_path),
                    ]
                )
                proc = subprocess.run(
                    command,
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertIn("HISTORICAL_INTEGRITY_ONLY", proc.stderr)
                self.assertIn("refuses persisted Markdown", proc.stderr)
                self.assertFalse(packet_path.exists(), "refusal must occur before JSON publication")
                self.assertFalse(markdown_path.exists(), "historical Markdown must not be persisted")

    def test_facade_function_metadata_cannot_recover_unsafe_legacy_callables(self) -> None:
        qualifier = load_qualifier()
        packet = qualifier.compile_historical(
            json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        )

        for exported in (
            qualifier.compile_historical,
            qualifier.verify_packet_historical,
            qualifier.render_markdown,
            qualifier.main,
        ):
            for default in exported.__defaults__ or ():
                self.assertFalse(callable(default), "callable must not be retained in function defaults")
            for cell in exported.__closure__ or ():
                self.assertFalse(callable(cell.cell_contents), "callable must not be retained in closure cells")

        # The predecessor used compile_historical.__globals__ (or wrapper
        # __defaults__) to recover the original raw renderer/main.  The core
        # namespace itself is now hardened before export, so those same routes
        # can recover only truth-labeled/refusing callables.
        core_globals = qualifier.compile_historical.__globals__
        recovered_renderer = core_globals["render_markdown"]
        recovered_main = core_globals["main"]
        self.assertIs(recovered_renderer, qualifier.render_markdown)
        self.assertIs(recovered_main, qualifier.main)
        recovered = recovered_renderer(packet)
        self.assertIn("HISTORICAL / INTEGRITY ONLY", recovered)
        self.assertIn("NOT CURRENT", recovered)

        with tempfile.TemporaryDirectory() as td:
            packet_path = Path(td) / "escaped.json"
            markdown_path = Path(td) / "escaped.md"
            rc = recovered_main(
                [
                    "compile",
                    str(FIXTURE_PATH),
                    "--json-out",
                    str(packet_path),
                    "--markdown-out",
                    str(markdown_path),
                ]
            )
            self.assertEqual(rc, 2)
            self.assertFalse(packet_path.exists(), "metadata bypass must not publish JSON first")
            self.assertFalse(markdown_path.exists(), "metadata bypass must not persist historical Markdown")

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
