#!/usr/bin/env python3
"""Real file/CLI regressions for liveness input shapes and decode failures."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from host import agent_liveness_index as live

ROOT = Path(__file__).resolve().parent
APP = ROOT / "host" / "agent_liveness_index.py"
OBSERVED = "2026-09-08T12:00:00Z"
COMMIT = "a" * 40
BLOBS = {name: str(index) * 40 for index, name in enumerate(live.SOURCE_PATHS, 1)}


def documents():
    row = {"from": "SAMPLE", "id": "receipt-1", "ts": "2026-09-08T11:00:00Z"}
    return {
        "presence.json": [dict(row, presence="PRESENT")],
        "lastseen.json": [dict(row, to="TABLE")],
        "claims.json": {"claims": [dict(row, status="OPEN", href="./p/receipt-1.html")]},
    }


def build(blobs=BLOBS, data=None, observed=OBSERVED):
    data = documents() if data is None else data
    return live.build_index(
        presence=data["presence.json"], lastseen=data["lastseen.json"],
        claims=data["claims.json"], observed_at=observed,
        source_commit=COMMIT, source_blobs=blobs,
    )


class BlobShapeTests(unittest.TestCase):
    def test_blob_collection_requires_an_object(self):
        for value in (None, False, 5, "paths", [], list(live.SOURCE_PATHS),
                      tuple(live.SOURCE_PATHS), set(live.SOURCE_PATHS)):
            with self.subTest(value=value):
                with self.assertRaisesRegex(live.AgentLivenessError, "source_blobs must be an object"):
                    build(value)

    def test_blob_ids_require_strings(self):
        for value in (None, False, 123, [], ["a"] * 40, {"a": 1}, b"a" * 40):
            with self.subTest(value=value):
                blobs = dict(BLOBS, **{"presence.json": value})
                original = copy.deepcopy(blobs)
                with self.assertRaisesRegex(live.AgentLivenessError, "source blob for presence.json"):
                    build(blobs)
                self.assertEqual(blobs, original)

    def test_existing_hex_and_width_checks_remain(self):
        for value in ("", "a" * 39, "a" * 41, "g" * 40, "A" * 40):
            with self.subTest(value=value):
                with self.assertRaisesRegex(live.AgentLivenessError, "40-character Git SHA"):
                    build(dict(BLOBS, **{"presence.json": value}))

    def test_exact_source_names_remain_required(self):
        for value in ({}, {"presence.json": "a" * 40}, dict(BLOBS, extra="b" * 40)):
            with self.subTest(value=value):
                with self.assertRaisesRegex(live.AgentLivenessError, "exactly the three source files"):
                    build(value)

    def test_valid_input_is_deterministic_and_unmodified(self):
        data, blobs = documents(), dict(BLOBS)
        before = copy.deepcopy((data, blobs))
        first = build(blobs, data)
        self.assertEqual(live.canonical_text(first), live.canonical_text(build(blobs, data)))
        self.assertEqual((data, blobs), before)
        self.assertEqual(first["source_blobs"], BLOBS)
        self.assertEqual(first["summary"]["fresh_6h"], 1)
        self.assertEqual(first["identities"][0]["session_reachability"], "NOT_VERIFIED")
        self.assertEqual(first["truth"]["messages_sent"], 0)

    def test_timestamp_precision_and_routing_are_preserved(self):
        cases = (
            ("2026-09-08T06:00:00Z", "FRESH_6H", 21600),
            ("2026-09-08T05:59:59.999999999Z", "RECENT_24H", 21600),
            ("2026-09-07T12:00:00Z", "RECENT_24H", 86400),
            ("2026-09-07T11:59:59.999999999Z", "STALE", 86400),
            ("2026-09-08T07:00:00-04:00", "FRESH_6H", 3600),
        )
        for timestamp, freshness, age in cases:
            with self.subTest(timestamp=timestamp):
                data = documents()
                for name in ("presence.json", "lastseen.json"):
                    data[name][0]["ts"] = timestamp
                actual = build(data=data)["identities"][0]
                self.assertEqual((actual["receipt_freshness"], actual["age_seconds"]), (freshness, age))
        data = documents()
        for name in ("presence.json", "lastseen.json"):
            data[name][0]["ts"] = "2026-09-08T12:00:00.000000001Z"
        with self.assertRaisesRegex(live.AgentLivenessError, "in the future"):
            build(data=data)


class FileAndCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name, value in documents().items():
            (self.root / name).write_text(json.dumps(value) + "\n", encoding="utf-8")
        self.snapshot = self.root / "snapshot.json"
        self.output = self.root / "output.json"
        self.output.write_bytes(b"retain existing output\n")

    def files(self):
        return {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, "-B", str(APP), "--root", str(self.root), *map(str, args)],
            capture_output=True, text=True, encoding="utf-8", timeout=10, check=False,
        )

    def assert_rejected(self, *args, contains=None):
        before = self.files()
        result = self.cli(*args)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.startswith("agent-liveness-index: "), result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        if contains is not None:
            self.assertIn(contains, result.stderr)
        self.assertEqual(self.files(), before)

    def scan_args(self):
        return ("--observed-at", OBSERVED, "--source-commit", COMMIT, "--output", self.output)

    def test_snapshot_nonobjects_have_structured_library_error(self):
        for value in (None, False, True, 0, 1.5, "snapshot", [], ["schema"]):
            with self.subTest(value=value):
                self.snapshot.write_text(json.dumps(value), encoding="utf-8")
                before = self.files()
                with self.assertRaisesRegex(live.AgentLivenessError, "must be an object"):
                    live.check_snapshot(self.root, self.snapshot)
                self.assertEqual(self.files(), before)

    def test_snapshot_nonobjects_have_structured_cli_error(self):
        for value in (None, False, True, 0, 1.5, "snapshot", [], ["schema"]):
            with self.subTest(value=value):
                self.snapshot.write_text(json.dumps(value), encoding="utf-8")
                self.assert_rejected("--check", self.snapshot, "--output", self.output,
                                     contains="must be an object")

    def test_snapshot_nonobject_is_rejected_before_missing_sources(self):
        for name in live.SOURCE_PATHS:
            (self.root / name).unlink()
        self.snapshot.write_text("null", encoding="utf-8")
        self.assert_rejected("--check", self.snapshot, contains="must be an object")

    def test_snapshot_wrong_schema_retains_diagnostic(self):
        for value in ({}, {"schema": None}, {"schema": []}, {"schema": "other"}):
            with self.subTest(value=value):
                self.snapshot.write_text(json.dumps(value), encoding="utf-8")
                self.assert_rejected("--check", self.snapshot, contains="is not " + live.SCHEMA)

    def test_snapshot_missing_metadata_is_rejected(self):
        self.snapshot.write_text(json.dumps({"schema": live.SCHEMA}), encoding="utf-8")
        self.assert_rejected("--check", self.snapshot, contains="observed_at must be nonempty")

    def test_snapshot_invalid_utf8_has_structured_cli_error(self):
        self.snapshot.write_bytes(b'{"schema":"\xff"}')
        self.assert_rejected("--check", self.snapshot)

    def test_each_source_invalid_utf8_has_structured_cli_error(self):
        for name in live.SOURCE_PATHS:
            with self.subTest(name=name):
                path = self.root / name
                original = path.read_bytes()
                try:
                    path.write_bytes(b"[\xff]")
                    self.assert_rejected(*self.scan_args())
                finally:
                    path.write_bytes(original)

    def test_invalid_utf8_source_during_snapshot_check(self):
        expected = live.scan(self.root, OBSERVED, COMMIT)
        self.snapshot.write_text(live.canonical_text(expected), encoding="utf-8")
        (self.root / "claims.json").write_bytes(b"\xffbroken")
        self.assert_rejected("--check", self.snapshot)

    def test_invalid_json_syntax_remains_structured(self):
        self.snapshot.write_text("{", encoding="utf-8")
        self.assert_rejected("--check", self.snapshot)
        (self.root / "presence.json").write_text("{", encoding="utf-8")
        self.assert_rejected(*self.scan_args())

    def test_existing_invalid_source_shape_is_structured(self):
        for name in live.SOURCE_PATHS:
            with self.subTest(name=name):
                path = self.root / name
                original = path.read_bytes()
                try:
                    path.write_text("null", encoding="utf-8")
                    self.assert_rejected(*self.scan_args())
                finally:
                    path.write_bytes(original)

    def test_missing_source_keeps_oserror_contract(self):
        (self.root / "claims.json").unlink()
        self.assert_rejected(*self.scan_args())

    def test_valid_scan_stdout_output_and_check_roundtrip(self):
        original_sources = {name: (self.root / name).read_bytes() for name in live.SOURCE_PATHS}
        stdout = self.cli("--observed-at", OBSERVED, "--source-commit", COMMIT)
        self.assertEqual((stdout.returncode, stdout.stderr), (0, ""))
        expected = live.scan(self.root, OBSERVED, COMMIT)
        self.assertEqual(stdout.stdout, live.canonical_text(expected))
        written = self.cli(*self.scan_args())
        self.assertEqual((written.returncode, written.stdout, written.stderr), (0, "", ""))
        self.assertEqual(self.output.read_bytes(), stdout.stdout.encode("utf-8"))
        checked = self.cli("--check", self.output)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(checked.stdout, "MATCH 1 identities 1 fresh 0 stale 0 unknown\n")
        self.assertEqual(checked.stderr, "")
        self.assertEqual(live.check_snapshot(self.root, self.output), expected)
        for name, raw in original_sources.items():
            self.assertEqual((self.root / name).read_bytes(), raw)

    def test_tampered_snapshot_is_not_promoted(self):
        expected = live.scan(self.root, OBSERVED, COMMIT)
        expected["identities"][0]["session_reachability"] = "LIVE"
        self.snapshot.write_text(live.canonical_text(expected), encoding="utf-8")
        self.assert_rejected("--check", self.snapshot, contains="differs from its exact source inputs")

    def test_source_byte_change_is_detected(self):
        expected = live.scan(self.root, OBSERVED, COMMIT)
        self.snapshot.write_text(live.canonical_text(expected), encoding="utf-8")
        path = self.root / "presence.json"
        path.write_bytes(path.read_bytes() + b"\n")
        self.assert_rejected("--check", self.snapshot, contains="differs from its exact source inputs")


if __name__ == "__main__":
    unittest.main()
