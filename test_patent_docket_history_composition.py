#!/usr/bin/env python3
"""Full docket/CLI composition of rename history and input-shape validation."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

import test_patent_docket_history as history


ROOT = Path(__file__).resolve().parent
mod = history.mod


class DocketHistoryCompositionTests(unittest.TestCase):
    def make_case(self, original="source original.txt"):
        # Reuse the canonical real-Git fixture without inheriting its test cases.
        fixture = history.SourceReceiptHistoryTests(methodName="runTest")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        files = {
            original: b"x",
            "unlinked.txt": b"x",
            "inventor.txt": b"Inventor: Bryce Muhlnickel\n",
            "status.txt": b"provisionals are filed\n",
        }
        for path, raw in files.items():
            fixture.write(path, raw.decode("utf-8"))
        created, stamp = fixture.commit("Add synthetic composition fixtures")
        fixture.git("mv", "--", original, "middle.txt")
        fixture.commit("First rename")
        fixture.git("mv", "--", "middle.txt", "current.txt")
        fixture.commit("Second rename")

        def source(path, raw):
            return {
                "path": path,
                "blob_sha": fixture.git("rev-parse", "HEAD:" + path),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "byte_count": len(raw),
                "public_url": history.URL + "main/" + path,
            }

        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://example.invalid/revenue/ip/patent_docket.schema.json",
            "type": "object",
            "additionalProperties": False,
        }
        docket = {
            "schema_version": "commons-patent-docket/v1",
            "kind": "PATENT_DOCKET",
            "generated_at": stamp,
            "generated_from_main": created,
            "scope": "Synthetic cross-component validator fixture only",
            "legal_scope": {key: False for key in mod.LEGAL_SCOPE_KEYS},
            "omitted_private_fields": sorted(mod.PRIVATE_KEYS),
            "inventor_provenance": dict(source("inventor.txt", files["inventor.txt"]), evidence_key="fixture", statement="fixture"),
            "status_provenance": dict(source("status.txt", files["status.txt"]), evidence_key="fixture", statement="fixture"),
            "entries": [{
                "id": "fixture-entry",
                "title": "Synthetic renamed source",
                "invention_summary": "Validator fixture only",
                "inventors": ["Bryce Muhlnickel"],
                "jurisdiction": "US",
                "filing_type": "PROVISIONAL",
                "filing_status": "UNKNOWN",
                "source": source("current.txt", files[original]),
                "earliest_public_receipt": fixture.receipt(original, created, stamp),
                "counsel_questions": ["Fixture only"],
            }],
        }
        return fixture, docket, schema

    def cli(self, fixture, docket, schema, command="validate"):
        (fixture.root / mod.DOCKET_PATH).parent.mkdir(parents=True, exist_ok=True)
        (fixture.root / mod.DOCKET_PATH).write_text(json.dumps(docket), encoding="utf-8")
        (fixture.root / mod.SCHEMA_PATH).write_text(json.dumps(schema), encoding="utf-8")
        return subprocess.run(
            [sys.executable, "-B", str(ROOT / "host/patent_docket.py"), command, "--root", str(fixture.root)],
            env=fixture.env, capture_output=True, text=True, check=False,
        )

    def assert_rejected(self, fixture, docket, schema, diagnostic):
        with self.assertRaisesRegex(mod.DocketError, diagnostic):
            mod.validate(fixture.root, docket, schema)
        result = self.cli(fixture, docket, schema)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("PATENT DOCKET INVALID:", result.stderr)
        self.assertIn(diagnostic, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_full_validator_consumes_linked_historical_receipt(self):
        fixture, docket, schema = self.make_case()
        before = copy.deepcopy(docket)
        result = mod.validate(fixture.root, docket, schema)
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["entries"], 1)
        self.assertEqual(docket, before)

    def test_validate_and_summary_cli_consume_linked_history(self):
        fixture, docket, schema = self.make_case()
        expected = mod.validate(fixture.root, docket, schema)
        for command in ("validate", "summary"):
            with self.subTest(command=command):
                result = self.cli(fixture, docket, schema, command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(json.loads(result.stdout), expected)

    def test_full_cli_preserves_special_historical_filenames(self):
        for original in ("tab\tname.txt", "line\nbreak.txt", "caf\u00e9-\u96ea.txt"):
            with self.subTest(original=original):
                fixture, docket, schema = self.make_case(original)
                result = self.cli(fixture, docket, schema)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["status"], "VALID")

    def test_malformed_receipt_hash_after_rename_is_a_diagnostic(self):
        fixture, docket, schema = self.make_case()
        for value in (None, False, True, 0, 1.5, [], {}, ["value"]):
            with self.subTest(value=value):
                candidate = copy.deepcopy(docket)
                candidate["entries"][0]["earliest_public_receipt"]["commit_sha"] = value
                self.assert_rejected(fixture, candidate, schema, "commit_sha invalid")

    def test_boolean_byte_count_after_rename_is_rejected(self):
        fixture, docket, schema = self.make_case()
        docket["entries"][0]["source"]["byte_count"] = True
        self.assert_rejected(fixture, docket, schema, "byte_count invalid")

    def test_identical_but_unlinked_source_cannot_supply_receipt(self):
        fixture, docket, schema = self.make_case()
        receipt = docket["entries"][0]["earliest_public_receipt"]
        receipt["path"] = "unlinked.txt"
        receipt["public_url"] = history.URL + receipt["commit_sha"] + "/unlinked.txt"
        self.assert_rejected(fixture, docket, schema, "path must equal source path")

    def test_historical_url_mismatch_remains_rejected(self):
        fixture, docket, schema = self.make_case()
        receipt = docket["entries"][0]["earliest_public_receipt"]
        receipt["public_url"] = history.URL + receipt["commit_sha"] + "/current.txt"
        self.assert_rejected(fixture, docket, schema, "public_url mismatch")


if __name__ == "__main__":
    unittest.main()
