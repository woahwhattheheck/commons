from __future__ import annotations

import importlib
import os
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
TARGETS = (
    (
        "revenue.rfp_clarification_questions.compiler",
        ROOT / "revenue" / "rfp_clarification_questions" / "compiler.py",
    ),
    (
        "revenue.procurement_qa_answer_delta.cli",
        ROOT / "revenue" / "procurement_qa_answer_delta" / "cli.py",
    ),
    (
        "revenue.procurement_solicitation_ingest.ingest",
        ROOT / "revenue" / "procurement_solicitation_ingest" / "ingest.py",
    ),
)


class WindowsCanonicalBinaryIOTest(unittest.TestCase):
    def test_every_low_level_open_requests_binary_mode(self) -> None:
        needle = 'getattr(os, "O_BINARY", 0)'
        for module_name, source_path in TARGETS:
            with self.subTest(module=module_name):
                source = source_path.read_text(encoding="utf-8")
                self.assertIn(needle, source)
                self.assertGreaterEqual(source.count(needle), 1)

    def test_crlf_lf_ctrl_z_bytes_round_trip_exactly(self) -> None:
        payload = b"crlf:\r\nlf:\nctrl-z:\x1a\x00tail\r\n"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for index, (module_name, _source_path) in enumerate(TARGETS):
                with self.subTest(module=module_name):
                    module = importlib.import_module(module_name)
                    source = root / f"source-{index}.bin"
                    output = root / f"output-{index}.bin"
                    source.write_bytes(payload)
                    self.assertEqual(module.read_bytes(str(source)), payload)
                    module.write_exclusive(str(output), payload)
                    self.assertEqual(output.read_bytes(), payload)
                    if os.name == "nt":
                        self.assertNotEqual(getattr(os, "O_BINARY", 0), 0)


if __name__ == "__main__":
    unittest.main()
