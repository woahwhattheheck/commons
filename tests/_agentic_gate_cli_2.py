from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from revenue.agentic_genai_evaluation_gate import cli
from revenue.agentic_genai_evaluation_gate.gate import (
    DECISION_HOLD,
    DECISION_RELEASE,
    EvidenceError,
    compile_receipt,
    render_markdown,
    verify_receipt,
)
from revenue.agentic_genai_evaluation_gate.golden import build_golden_packet
from ._agentic_gate_base import AgenticGateCase, EVAL_AT


class AgenticGenAICliCustodyTestsPart2(unittest.TestCase):
    def test_missing_parent_rejected_without_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "missing"
            output = parent / "receipt.json"
            with self.assertRaises(OSError):
                cli._publish_exclusive([(output, b"ours")])
            self.assertFalse(parent.exists())

    def test_successful_multi_output_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "receipt.json"
            second = root / "receipt.md"
            cli._publish_exclusive(
                [(first, b"json"), (second, b"markdown")]
            )
            self.assertEqual(first.read_bytes(), b"json")
            self.assertEqual(second.read_bytes(), b"markdown")
            self.assertEqual(first.stat().st_mode & 0o777, 0o600)
            self.assertEqual(second.stat().st_mode & 0o777, 0o600)

    def test_short_write_is_drained(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "out"
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            real_write = os.write

            def short_write(target_fd, data):
                return real_write(target_fd, data[:3])

            try:
                with mock.patch.object(
                    cli.os,
                    "write",
                    side_effect=short_write,
                ):
                    cli._drain_write(fd, b"abcdefghij")
                os.fsync(fd)
            finally:
                os.close(fd)
            self.assertEqual(path.read_bytes(), b"abcdefghij")

    def test_final_name_replacement_is_detected_and_not_deleted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "receipt.json"
            displaced = root / "displaced.json"
            original_revalidate = cli._revalidate_target
            attacked = False

            def hostile_revalidate(target, *, final):
                nonlocal attacked
                if not final and not attacked:
                    attacked = True
                    output.rename(displaced)
                    output.write_bytes(b"foreign")
                return original_revalidate(target, final=final)

            with mock.patch.object(
                cli,
                "_revalidate_target",
                side_effect=hostile_revalidate,
            ):
                with self.assertRaisesRegex(
                    EvidenceError,
                    "visible output",
                ):
                    cli._publish_exclusive([(output, b"ours")])
            self.assertEqual(output.read_bytes(), b"foreign")
            self.assertEqual(displaced.read_bytes(), b"ours")

    def test_parent_rename_replacement_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "visible"
            parent.mkdir()
            moved = root / "moved"
            output = parent / "receipt.json"
            original_revalidate = cli._revalidate_target
            attacked = False

            def hostile_revalidate(target, *, final):
                nonlocal attacked
                if final and not attacked:
                    attacked = True
                    parent.rename(moved)
                    parent.mkdir()
                return original_revalidate(target, final=final)

            with mock.patch.object(
                cli,
                "_revalidate_target",
                side_effect=hostile_revalidate,
            ):
                with self.assertRaisesRegex(
                    EvidenceError,
                    "visible parent identity changed",
                ):
                    cli._publish_exclusive([(output, b"ours")])
            self.assertFalse(output.exists())
            self.assertEqual(
                (moved / "receipt.json").read_bytes(),
                b"ours",
            )

    def test_cli_compile_and_verify_end_to_end(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            packet_path = root / "packet.json"
            receipt_path = root / "receipt.json"
            markdown_path = root / "receipt.md"
            packet_path.write_text(
                json.dumps(build_golden_packet()),
                encoding="utf-8",
            )
            with mock.patch.object(cli, "_now", return_value=EVAL_AT):
                with mock.patch("sys.stdout"):
                    compile_code = cli.main(
                        [
                            "compile",
                            os.fspath(packet_path),
                            os.fspath(receipt_path),
                            "--markdown-out",
                            os.fspath(markdown_path),
                        ]
                    )
                    verify_code = cli.main(
                        [
                            "verify",
                            os.fspath(packet_path),
                            os.fspath(receipt_path),
                        ]
                    )
            self.assertEqual(compile_code, 0)
            self.assertEqual(verify_code, 0)
            self.assertEqual(
                json.loads(receipt_path.read_text())["decision"],
                DECISION_RELEASE,
            )
            self.assertIn(
                "authorizes no deployment",
                markdown_path.read_text(),
            )

    def test_cli_occupied_markdown_prevents_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            packet_path = root / "packet.json"
            receipt_path = root / "receipt.json"
            markdown_path = root / "receipt.md"
            packet_path.write_text(
                json.dumps(build_golden_packet()),
                encoding="utf-8",
            )
            markdown_path.write_text("foreign", encoding="utf-8")
            with mock.patch.object(cli, "_now", return_value=EVAL_AT):
                with mock.patch("sys.stderr"):
                    code = cli.main(
                        [
                            "compile",
                            os.fspath(packet_path),
                            os.fspath(receipt_path),
                            "--markdown-out",
                            os.fspath(markdown_path),
                        ]
                    )
            self.assertEqual(code, 4)
            self.assertFalse(receipt_path.exists())
            self.assertEqual(markdown_path.read_text(), "foreign")
