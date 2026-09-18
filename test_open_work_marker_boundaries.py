#!/usr/bin/env python3
"""Work markers must not manufacture a valid ID by truncating a longer token."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from host import open_work as ow


ROOT = Path(__file__).resolve().parent
LONG_ID = "preserve-work-marker-".ljust(80, "a")
MARKERS = ("WORK ORDER ", "OWNER LAND ORDER ", "work\torder: ", "owner land order= ")


class WorkMarkerBoundaryContract(unittest.TestCase):
    def test_all_valid_lengths_and_marker_formats_are_preserved(self):
        for length in range(8, 81):
            ident = "work-job" + "a" * (length - 8)
            for marker in MARKERS:
                with self.subTest(length=length, marker=marker):
                    self.assertEqual(ow.extract_work_ids(marker + ident), [ident])
                    self.assertEqual(ow.extract_work_ids(marker + "`" + ident + "`"), [ident])

    def test_overlong_tokens_are_not_truncated(self):
        self.assertEqual(len(LONG_ID), 80)
        for tail in ("a", "7", ".", "_", "-", "long-suffix-20260907-01", "x" * 80):
            invalid = LONG_ID + tail
            self.assertFalse(ow.is_work_id(invalid))
            for marker in MARKERS:
                for quoted in (False, True):
                    with self.subTest(tail=tail, marker=marker, quoted=quoted):
                        token = "`" + invalid + "`" if quoted else invalid
                        self.assertEqual(ow.extract_work_ids(marker + token), [])

    def test_existing_delimiters_remain_supported_at_maximum_length(self):
        for delimiter in ("", " ", "\n", "\t", ",", ";", ")", "]", "`"):
            with self.subTest(delimiter=delimiter):
                self.assertEqual(ow.extract_work_ids("WORK ORDER " + LONG_ID + delimiter), [LONG_ID])

    def test_scan_continues_after_invalid_token_and_deduplicates_valid_ids(self):
        valid = "remaining-work-marker-20260907-01"
        text = (
            "WORK ORDER " + LONG_ID + "overflow "
            "WORK ORDER " + valid + ",\n"
            "OWNER LAND ORDER `" + valid + "`\n"
            "WORK ORDER " + LONG_ID + "\n"
        )
        self.assertEqual(ow.extract_work_ids(text), [valid, LONG_ID])

    def test_structured_header_and_marker_both_preserve_complete_ids(self):
        for ident in (LONG_ID, LONG_ID + "x"):
            with self.subTest(length=len(ident)):
                record = ow.parse_structured_record(
                    "from: PEER\nid: " + ident + "\n\n---\n\nWORK ORDER `" + ident + "`\n"
                )
                expected = [ident] if len(ident) == 80 else []
                self.assertEqual(record["work_ids"], expected)
                self.assertEqual(record["id"], ident if expected else "")


class WorkMarkerProjectionContract(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="open-work-markers-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.valid = "remaining-work-marker-20260907-01"
        source = self.root / "p" / "marker-source-record-20260907-01.md"
        source.parent.mkdir()
        source.write_text(
            "from: PEER\nid: marker-source-record-20260907-01\n\n---\n\n"
            "WORK ORDER " + LONG_ID + "overflow\n"
            "WORK ORDER " + self.valid + "\n",
            encoding="utf-8",
        )
        self.git("init", "-q")
        self.git("add", ".")
        self.git("-c", "user.name=Commons Test", "-c",
                 "user.email=commons-test@example.invalid", "commit", "-qm", "fixture")
        self.sha = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.check_output(
            ["git", *args], cwd=self.root, text=True, stderr=subprocess.PIPE,
        )

    def assert_snapshot(self, snapshot):
        self.assertEqual(snapshot["errors"], [])
        self.assertEqual([item["id"] for item in snapshot["items"]], [self.valid])
        self.assertEqual(snapshot["counts"]["OPEN"], 1)
        self.assertEqual(snapshot["items"][0]["class"], "OPEN")
        self.assertEqual(snapshot["items"][0]["receipt"], "404")
        self.assertEqual(self.git("diff", "--", "p"), "")

    def test_projection_does_not_invent_a_truncated_work_record(self):
        snapshot = ow.project(str(self.root), self.sha)
        self.assert_snapshot(snapshot)
        ow.write_snapshot(str(self.root), snapshot)
        listing = self.root / ow.LISTING_REL
        self.assertEqual([path.name for path in listing.glob("*.md")], [self.valid + "-open.md"])
        machine = json.loads((self.root / ow.MACHINE_REL).read_text(encoding="utf-8"))
        self.assertEqual(machine["items"], snapshot["items"])

    def test_cli_uses_the_same_complete_token_boundaries(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "host" / "open_work.py"),
             "--root", str(self.root), "--main-sha", self.sha],
            check=True, capture_output=True, text=True,
        )
        self.assert_snapshot(json.loads(result.stdout))


if __name__ == "__main__":
    unittest.main()
