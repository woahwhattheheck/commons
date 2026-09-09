#!/usr/bin/env python3
"""Real JSON integer-limit failures retain the liveness input-error contract."""
from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from host import agent_liveness_index as live

APP = Path(__file__).resolve().parent / "host" / "agent_liveness_index.py"
OBSERVED = "2026-09-08T12:00:00Z"
COMMIT = "a" * 40
DIGITS = "7" * 1000


@contextlib.contextmanager
def integer_limit():
    """Set a deterministic test limit and restore it, never disable the guard."""
    previous = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(640)
    try:
        yield
    finally:
        sys.set_int_max_str_digits(previous)


@unittest.skipUnless(hasattr(sys, "set_int_max_str_digits"), "Python has no integer conversion limit")
class JSONLimitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.docs = {
            "presence.json": [{"from": "SAMPLE", "id": "r1", "ts": OBSERVED}],
            "lastseen.json": [{"from": "SAMPLE", "id": "r1", "ts": OBSERVED}],
            "claims.json": {"claims": []},
        }
        for name, value in self.docs.items():
            (self.root / name).write_text(json.dumps(value), encoding="utf-8")
        self.expected = live.scan(self.root, OBSERVED, COMMIT)
        self.snapshot = self.root / "snapshot.json"
        self.snapshot.write_text(live.canonical_text(self.expected), encoding="utf-8")
        self.output = self.root / "output.json"
        self.output.write_bytes(b"retain output sentinel\n")

    def inject_integer(self, name, digits=DIGITS):
        value = json.loads((self.root / name).read_text(encoding="utf-8"))
        target = value[0] if isinstance(value, list) else value
        target["unused_metadata"] = "INTEGER_PLACEHOLDER"
        text = json.dumps(value).replace('"INTEGER_PLACEHOLDER"', digits)
        (self.root / name).write_text(text, encoding="utf-8")

    def files(self):
        return {path.name: path.read_bytes() for path in self.root.iterdir()}

    def cli(self, *args):
        environment = dict(os.environ, PYTHONINTMAXSTRDIGITS="640")
        return subprocess.run(
            [sys.executable, "-B", str(APP), "--root", str(self.root), *map(str, args)],
            env=environment, capture_output=True, text=True, encoding="utf-8",
            timeout=10, check=False,
        )

    def rejects_cli(self, *args):
        before = self.files()
        result = self.cli(*args)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.startswith("agent-liveness-index: "), result.stderr)
        self.assertIn("invalid JSON", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.files(), before)

    def test_library_snapshot_normalizes_integer_limit(self):
        self.inject_integer("snapshot.json")
        with integer_limit():
            with self.assertRaisesRegex(live.AgentLivenessError, "snapshot.json: invalid JSON") as caught:
                live.check_snapshot(self.root, self.snapshot)
            self.assertIsInstance(caught.exception.__cause__, ValueError)
            self.assertNotIsInstance(caught.exception.__cause__, json.JSONDecodeError)
            self.assertEqual(sys.get_int_max_str_digits(), 640)

    def test_library_scan_normalizes_each_source_integer_limit(self):
        for name in live.SOURCE_PATHS:
            with self.subTest(source=name):
                original = (self.root / name).read_bytes()
                try:
                    self.inject_integer(name)
                    with integer_limit():
                        with self.assertRaisesRegex(live.AgentLivenessError, name + ": invalid JSON"):
                            live.scan(self.root, OBSERVED, COMMIT)
                        self.assertEqual(sys.get_int_max_str_digits(), 640)
                finally:
                    (self.root / name).write_bytes(original)

    def test_bad_snapshot_decode_precedes_source_access(self):
        self.inject_integer("snapshot.json")
        for name in live.SOURCE_PATHS:
            (self.root / name).unlink()
        with integer_limit():
            with self.assertRaisesRegex(live.AgentLivenessError, "snapshot.json: invalid JSON"):
                live.check_snapshot(self.root, self.snapshot)

    def test_cli_bad_snapshot_is_structured_and_read_only(self):
        self.inject_integer("snapshot.json")
        self.rejects_cli("--check", self.snapshot, "--output", self.output)

    def test_cli_each_bad_source_keeps_existing_output(self):
        for name in live.SOURCE_PATHS:
            with self.subTest(source=name):
                original = (self.root / name).read_bytes()
                try:
                    self.inject_integer(name)
                    self.rejects_cli("--observed-at", OBSERVED, "--source-commit", COMMIT,
                                     "--output", self.output)
                finally:
                    (self.root / name).write_bytes(original)

    def test_cli_check_with_bad_source_is_structured(self):
        self.inject_integer("claims.json")
        self.rejects_cli("--check", self.snapshot)

    def test_json_syntax_exception_and_coordinates_are_preserved(self):
        for name in ("snapshot.json", "presence.json"):
            with self.subTest(name=name):
                original = (self.root / name).read_bytes()
                try:
                    (self.root / name).write_text("{\n", encoding="utf-8")
                    operation = (lambda: live.check_snapshot(self.root, self.snapshot)) if name == "snapshot.json" else (lambda: live.scan(self.root, OBSERVED, COMMIT))
                    with self.assertRaises(json.JSONDecodeError) as caught:
                        operation()
                    self.assertEqual((caught.exception.lineno, caught.exception.colno), (2, 1))
                finally:
                    (self.root / name).write_bytes(original)

    def test_unicode_decode_exception_is_preserved(self):
        for name in ("snapshot.json", "presence.json"):
            with self.subTest(name=name):
                original = (self.root / name).read_bytes()
                try:
                    (self.root / name).write_bytes(b"\xff")
                    with self.assertRaises(UnicodeDecodeError):
                        if name == "snapshot.json":
                            live.check_snapshot(self.root, self.snapshot)
                        else:
                            live.scan(self.root, OBSERVED, COMMIT)
                finally:
                    (self.root / name).write_bytes(original)

    def test_valid_integer_metadata_still_roundtrips(self):
        self.inject_integer("presence.json", "7" * 100)
        with integer_limit():
            expected = live.scan(self.root, OBSERVED, COMMIT)
            self.snapshot.write_text(live.canonical_text(expected), encoding="utf-8")
            self.assertEqual(live.check_snapshot(self.root, self.snapshot), expected)
            self.assertEqual(sys.get_int_max_str_digits(), 640)
        result = self.cli("--check", self.snapshot)
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        self.assertTrue(result.stdout.startswith("MATCH 1 identities 1 fresh"))

    def test_digit_strings_are_not_numeric_conversion_errors(self):
        value = self.docs["claims.json"]
        value["unused_metadata"] = DIGITS
        (self.root / "claims.json").write_text(json.dumps(value), encoding="utf-8")
        with integer_limit():
            result = live.scan(self.root, OBSERVED, COMMIT)
        self.assertEqual(result["summary"], self.expected["summary"])

    def test_original_valid_output_bytes_are_unchanged(self):
        before = self.files()
        result = self.cli("--observed-at", OBSERVED, "--source-commit", COMMIT)
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        self.assertEqual(result.stdout, live.canonical_text(self.expected))
        self.assertEqual(self.files(), before)

    def test_schema_errors_are_not_reclassified_as_decoder_errors(self):
        self.snapshot.write_text("null", encoding="utf-8")
        with self.assertRaisesRegex(live.AgentLivenessError, "must be an object") as caught:
            live.check_snapshot(self.root, self.snapshot)
        self.assertNotIn("invalid JSON", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
