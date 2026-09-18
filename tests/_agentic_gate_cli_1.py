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


class AgenticGenAICliCustodyTestsPart1(unittest.TestCase):
    def test_duplicate_json_key_rejected_at_any_depth(self):
        raw = b'{"outer":{"x":1,"x":2}}'
        with self.assertRaisesRegex(EvidenceError, "duplicate JSON"):
            cli._strict_json_loads(raw, source="memory")

    def test_nonfinite_json_constant_rejected(self):
        with self.assertRaises(EvidenceError):
            cli._strict_json_loads(b'{"x":NaN}', source="memory")

    def test_invalid_utf8_rejected(self):
        with self.assertRaises(EvidenceError):
            cli._strict_json_loads(b"\xff", source="memory")

    def test_retained_descriptor_read_returns_exact_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "packet.json"
            payload = b'{"schema_version":2}'
            path.write_bytes(payload)
            self.assertEqual(cli._read_bytes_bounded(path), payload)

    def test_symlink_input_rejected(self):
        if not hasattr(os, "O_NOFOLLOW"):
            self.skipTest("host lacks O_NOFOLLOW")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target.json"
            link = root / "link.json"
            target.write_text("{}", encoding="utf-8")
            link.symlink_to(target)
            with self.assertRaises(OSError):
                cli._read_bytes_bounded(link)

    def test_directory_input_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(EvidenceError):
                cli._read_bytes_bounded(Path(temporary))

    def test_visible_input_replacement_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "packet.json"
            displaced = root / "displaced.json"
            original = b"a" * (cli._READ_CHUNK * 2)
            path.write_bytes(original)
            real_read = os.read
            calls = 0

            def hostile_read(fd, amount):
                nonlocal calls
                chunk = real_read(fd, amount)
                calls += 1
                if calls == 1:
                    path.rename(displaced)
                    path.write_bytes(b"b" * len(original))
                return chunk

            with mock.patch.object(cli.os, "read", side_effect=hostile_read):
                with self.assertRaisesRegex(
                    EvidenceError,
                    "generation changed|visible input no longer names retained generation",
                ):
                    cli._read_bytes_bounded(path)
            self.assertEqual(displaced.read_bytes(), original)
            self.assertEqual(path.read_bytes(), b"b" * len(original))

    def test_in_place_rewrite_with_restored_mtime_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "packet.json"
            original = b"a" * (cli._READ_CHUNK * 2)
            replacement = b"b" * len(original)
            path.write_bytes(original)
            before = path.stat()
            real_read = os.read
            calls = 0

            def hostile_read(fd, amount):
                nonlocal calls
                chunk = real_read(fd, amount)
                calls += 1
                if calls == 1:
                    with path.open("r+b", buffering=0) as writer:
                        writer.seek(0)
                        writer.write(replacement)
                        writer.flush()
                        os.fsync(writer.fileno())
                    os.utime(
                        path,
                        ns=(before.st_atime_ns, before.st_mtime_ns),
                    )
                return chunk

            with mock.patch.object(cli.os, "read", side_effect=hostile_read):
                with self.assertRaisesRegex(
                    EvidenceError,
                    "generation changed",
                ):
                    cli._read_bytes_bounded(path)

    def test_occupied_second_output_prevents_first_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "receipt.json"
            second = root / "receipt.md"
            second.write_text("occupied", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                cli._publish_exclusive(
                    [(first, b"first"), (second, b"second")]
                )
            self.assertFalse(first.exists())
            self.assertEqual(second.read_text(), "occupied")

    def test_occupied_first_output_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "receipt.json"
            first.write_text("foreign", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                cli._publish_exclusive([(first, b"ours")])
            self.assertEqual(first.read_text(), "foreign")

    def test_final_symlink_output_rejected_without_following(self):
        if not hasattr(os, "O_NOFOLLOW"):
            self.skipTest("host lacks O_NOFOLLOW")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            foreign = root / "foreign"
            foreign.write_text("foreign", encoding="utf-8")
            output = root / "receipt.json"
            output.symlink_to(foreign)
            with self.assertRaises(FileExistsError):
                cli._publish_exclusive([(output, b"ours")])
            self.assertEqual(foreign.read_text(), "foreign")

    def test_symlinked_parent_component_rejected(self):
        if not hasattr(os, "O_NOFOLLOW"):
            self.skipTest("host lacks O_NOFOLLOW")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real = root / "real"
            real.mkdir()
            linked = root / "linked"
            linked.symlink_to(real, target_is_directory=True)
            with self.assertRaises(OSError):
                cli._publish_exclusive(
                    [(linked / "receipt.json", b"ours")]
                )
            self.assertFalse((real / "receipt.json").exists())

    def test_duplicate_output_target_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "receipt.json"
            with self.assertRaisesRegex(EvidenceError, "duplicate output"):
                cli._publish_exclusive(
                    [(output, b"one"), (output, b"two")]
                )
            self.assertFalse(output.exists())
