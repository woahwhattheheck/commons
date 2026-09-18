from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from revenue.agentic_genai_evaluation_gate import cli
from revenue.agentic_genai_evaluation_gate.gate import (
    DECISION_RELEASE,
    EvidenceError,
)
from revenue.agentic_genai_evaluation_gate.golden import build_golden_packet
from ._agentic_gate_base import EVAL_AT


class AgenticGenAISingleOutputPublicationTests(unittest.TestCase):
    def test_successful_single_output_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "receipt.json"
            cli._publish_exclusive([(output, b"json")])
            self.assertEqual(output.read_bytes(), b"json")
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(output.stat().st_nlink, 1)

    def test_all_absent_multi_output_is_rejected_without_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "receipt.json"
            second = root / "receipt.md"
            with self.assertRaisesRegex(EvidenceError, "multi-output"):
                cli._publish_exclusive(
                    [(first, b"json"), (second, b"markdown")]
                )
            self.assertFalse(first.exists())
            self.assertFalse(second.exists())

    def test_missing_parent_rejected_without_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "missing" / "receipt.json"
            with self.assertRaises(OSError):
                cli._publish_exclusive([(output, b"ours")])
            self.assertFalse(output.parent.exists())

    def test_write_failure_leaves_no_visible_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "receipt.json"
            with mock.patch.object(cli.os, "write", side_effect=OSError("boom")):
                with self.assertRaises(OSError):
                    cli._publish_exclusive([(output, b"ours")])
            self.assertFalse(output.exists())

    def test_late_destination_collision_leaves_only_foreign_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "receipt.json"
            real_commit = cli._commit_link

            def hostile_commit(target):
                output.write_bytes(b"foreign")
                return real_commit(target)

            with mock.patch.object(
                cli,
                "_commit_link",
                side_effect=hostile_commit,
            ):
                with self.assertRaises(FileExistsError):
                    cli._publish_exclusive([(output, b"ours")])
            self.assertEqual(output.read_bytes(), b"foreign")

    def test_payload_is_not_visible_before_namespace_commit(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "receipt.json"
            original = cli._revalidate_target

            def inspect_private(target, *, final):
                if not final:
                    self.assertFalse(output.exists())
                return original(target, final=final)

            with mock.patch.object(
                cli,
                "_revalidate_target",
                side_effect=inspect_private,
            ):
                cli._publish_exclusive([(output, b"ours")])
            self.assertEqual(output.read_bytes(), b"ours")

    def test_final_name_replacement_is_detected_and_not_deleted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "receipt.json"
            displaced = root / "displaced.json"
            original = cli._revalidate_target
            attacked = False

            def hostile_revalidate(target, *, final):
                nonlocal attacked
                if final and not attacked:
                    attacked = True
                    output.rename(displaced)
                    output.write_bytes(b"foreign")
                return original(target, final=final)

            with mock.patch.object(
                cli,
                "_revalidate_target",
                side_effect=hostile_revalidate,
            ):
                with self.assertRaisesRegex(EvidenceError, "final visible"):
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
            original = cli._revalidate_target
            attacked = False

            def hostile_revalidate(target, *, final):
                nonlocal attacked
                if final and not attacked:
                    attacked = True
                    parent.rename(moved)
                    parent.mkdir()
                return original(target, final=final)

            with mock.patch.object(
                cli,
                "_revalidate_target",
                side_effect=hostile_revalidate,
            ):
                with self.assertRaisesRegex(EvidenceError, "visible parent"):
                    cli._publish_exclusive([(output, b"ours")])
            self.assertFalse(output.exists())
            self.assertEqual((moved / "receipt.json").read_bytes(), b"ours")

    def test_compile_render_verify_end_to_end(self):
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
                        ["compile", os.fspath(packet_path), os.fspath(receipt_path)]
                    )
                    render_code = cli.main(
                        ["render", os.fspath(receipt_path), os.fspath(markdown_path)]
                    )
                    verify_code = cli.main(
                        ["verify", os.fspath(packet_path), os.fspath(receipt_path)]
                    )
            self.assertEqual((compile_code, render_code, verify_code), (0, 0, 0))
            self.assertEqual(
                json.loads(receipt_path.read_text())["decision"],
                DECISION_RELEASE,
            )
            self.assertIn("authorizes no deployment", markdown_path.read_text())

    def test_deprecated_combined_output_is_rejected_before_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            packet_path = root / "packet.json"
            receipt_path = root / "receipt.json"
            markdown_path = root / "receipt.md"
            packet_path.write_text(
                json.dumps(build_golden_packet()),
                encoding="utf-8",
            )
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
            self.assertFalse(markdown_path.exists())
