#!/usr/bin/env python3
"""Docket JSON shape regressions using an isolated, real Git history."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("patent_docket_shapes", ROOT / "host/patent_docket.py")
patent_docket = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(patent_docket)

NON_STRINGS = (None, False, True, 0, 1.5, [], {}, ["value"])


class PatentDocketInputShapesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="patent-docket-shapes-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name)
        cls.env = os.environ.copy()
        # Keep Git fixtures independent of the invoking user's identity/config.
        cls.env.update({
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_AUTHOR_NAME": "Docket fixture",
            "GIT_AUTHOR_EMAIL": "docket-fixture@example.invalid",
            "GIT_COMMITTER_NAME": "Docket fixture",
            "GIT_COMMITTER_EMAIL": "docket-fixture@example.invalid",
            "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00",
        })
        cls.git("init", "-q")
        # These are synthetic validator fixtures, not production filing records.
        files = {
            "fixture-source.txt": b"x",
            "fixture-inventor.txt": b"Inventor: Bryce Muhlnickel\n",
            "fixture-status.txt": b"provisionals are filed\n",
        }
        for name, raw in files.items():
            (cls.root / name).write_bytes(raw)
        cls.git("add", "--", *files)
        cls.git("-c", "commit.gpgsign=false", "commit", "-qm", "Add validation fixtures")
        commit = cls.git("rev-parse", "HEAD")
        timestamp = cls.git("show", "-s", "--format=%cI", "HEAD")

        def source(name):
            raw = files[name]
            return {
                "path": name,
                "blob_sha": cls.git("rev-parse", "HEAD:" + name),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "byte_count": len(raw),
                "public_url": "https://github.com/woahwhattheheck/commons/blob/main/" + name,
            }

        cls.source = source("fixture-source.txt")
        cls.receipt = {
            "path": cls.source["path"],
            "commit_sha": commit,
            "disclosed_at": timestamp,
            "public_url": "https://github.com/woahwhattheheck/commons/blob/%s/%s" % (commit, cls.source["path"]),
        }
        cls.schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://example.invalid/revenue/ip/patent_docket.schema.json",
            "type": "object",
            "additionalProperties": False,
        }
        cls.docket = {
            "schema_version": "commons-patent-docket/v1",
            "kind": "PATENT_DOCKET",
            "generated_at": timestamp,
            "generated_from_main": commit,
            "scope": "Synthetic input-shape test fixture",
            "legal_scope": {key: False for key in patent_docket.LEGAL_SCOPE_KEYS},
            "omitted_private_fields": sorted(patent_docket.PRIVATE_KEYS),
            "inventor_provenance": dict(source("fixture-inventor.txt"), evidence_key="fixture", statement="fixture"),
            "status_provenance": dict(source("fixture-status.txt"), evidence_key="fixture", statement="fixture"),
            "entries": [{
                "id": "fixture-entry",
                "title": "Synthetic source fixture",
                "invention_summary": "Validator fixture only",
                "inventors": ["Bryce Muhlnickel"],
                "jurisdiction": "US",
                "filing_type": "PROVISIONAL",
                "filing_status": "UNKNOWN",
                "source": cls.source,
                "earliest_public_receipt": cls.receipt,
                "counsel_questions": ["Fixture only"],
            }],
        }

    @classmethod
    def git(cls, *args):
        return subprocess.run(
            ["git", "-C", str(cls.root), *args],
            env=cls.env, check=True, capture_output=True, text=True,
        ).stdout.strip()

    def assert_invalid(self, docket=None, schema=None, message="invalid"):
        with self.assertRaisesRegex(patent_docket.DocketError, message):
            patent_docket.validate(
                self.root,
                self.docket if docket is None else docket,
                self.schema if schema is None else schema,
            )

    def run_cli(self, docket, schema):
        folder = self.root / "revenue/ip"
        folder.mkdir(parents=True, exist_ok=True)
        (self.root / patent_docket.DOCKET_PATH).write_text(json.dumps(docket), encoding="utf-8")
        (self.root / patent_docket.SCHEMA_PATH).write_text(json.dumps(schema), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(ROOT / "host/patent_docket.py"), "validate", "--root", str(self.root)],
            env=self.env, check=False, capture_output=True, text=True,
        )

    def test_valid_fixture_uses_real_blobs_and_history(self):
        self.assertEqual(patent_docket._validate_source(self.root, self.source, "source"), b"x")
        patent_docket._validate_receipt(self.root, self.receipt, self.source["path"], "receipt")
        result = patent_docket.validate(self.root, self.docket, self.schema)
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["entries"], 1)
        cli = self.run_cli(self.docket, self.schema)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        self.assertEqual(json.loads(cli.stdout)["status"], "VALID")

    def test_blob_reader_requires_string_hash(self):
        for value in NON_STRINGS:
            with self.subTest(value=value), self.assertRaisesRegex(patent_docket.DocketError, "invalid blob sha"):
                patent_docket._blob_bytes(self.root, value)

    def test_source_hashes_require_strings(self):
        for key in ("blob_sha", "sha256"):
            for value in NON_STRINGS:
                source = dict(self.source, **{key: value})
                with self.subTest(key=key, value=value), self.assertRaisesRegex(patent_docket.DocketError, key + " invalid"):
                    patent_docket._validate_source(self.root, source, "source")

    def test_source_byte_count_is_positive_integer_not_boolean(self):
        for value in (True, False, None, 0, -1, 1.0, "1", [], {}):
            with self.subTest(value=value), self.assertRaisesRegex(patent_docket.DocketError, "byte_count invalid"):
                patent_docket._validate_source(self.root, dict(self.source, byte_count=value), "source")

    def test_receipt_hash_requires_string(self):
        for value in NON_STRINGS:
            with self.subTest(value=value), self.assertRaisesRegex(patent_docket.DocketError, "commit_sha invalid"):
                patent_docket._validate_receipt(self.root, dict(self.receipt, commit_sha=value), self.source["path"], "receipt")

    def test_generated_hash_requires_string(self):
        for value in NON_STRINGS:
            with self.subTest(value=value):
                self.assert_invalid(dict(self.docket, generated_from_main=value), message="generated_from_main invalid")

    def test_schema_requires_object(self):
        for value in (None, False, 1, "schema", []):
            with self.subTest(value=value), self.assertRaisesRegex(patent_docket.DocketError, "schema must be an object"):
                patent_docket.validate(self.root, self.docket, value)

    def test_schema_id_requires_string(self):
        for value in NON_STRINGS:
            with self.subTest(value=value):
                self.assert_invalid(schema=dict(self.schema, **{"$id": value}), message="schema id mismatch")

    def test_omitted_fields_require_strings_before_deduplication(self):
        for value in NON_STRINGS:
            with self.subTest(value=value):
                omitted = self.docket["omitted_private_fields"] + [value]
                self.assert_invalid(dict(self.docket, omitted_private_fields=omitted), message="omitted_private_fields invalid")
        duplicate = self.docket["omitted_private_fields"] * 2
        self.assert_invalid(dict(self.docket, omitted_private_fields=duplicate), message="omitted_private_fields invalid")

    def test_entry_id_requires_string(self):
        for value in NON_STRINGS:
            with self.subTest(value=value):
                docket = copy.deepcopy(self.docket)
                docket["entries"][0]["id"] = value
                self.assert_invalid(docket, message="id invalid")

    def test_entry_status_requires_string_before_set_membership(self):
        for value in NON_STRINGS:
            with self.subTest(value=value):
                docket = copy.deepcopy(self.docket)
                docket["entries"][0]["filing_status"] = value
                self.assert_invalid(docket, message="filing_status invalid")

    def test_legal_scope_requires_actual_booleans(self):
        for value in (None, 0, "", [], {}):
            with self.subTest(value=value):
                docket = copy.deepcopy(self.docket)
                docket["legal_scope"]["patentability_claimed"] = value
                self.assert_invalid(docket, message="legal_scope values must be booleans")

    def test_malformed_cli_has_diagnostic_not_traceback(self):
        cases = [
            (dict(self.docket, generated_from_main=None), self.schema),
            (self.docket, []),
            (self.docket, dict(self.schema, **{"$id": 1})),
            (dict(self.docket, omitted_private_fields=[[]]), self.schema),
        ]
        for docket, schema in cases:
            with self.subTest(docket_type=type(docket).__name__, schema=schema):
                result = self.run_cli(docket, schema)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertIn("PATENT DOCKET INVALID:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_existing_format_and_drift_checks_remain(self):
        for value in ("", "f" * 39, "g" * 40, "F" * 40, "f" * 40 + "\n"):
            with self.subTest(value=value):
                self.assert_invalid(dict(self.docket, generated_from_main=value), message="generated_from_main invalid")
        docket = copy.deepcopy(self.docket)
        docket["entries"][0]["source"]["sha256"] = "0" * 64
        self.assert_invalid(docket, message="sha256 drift")
        docket = copy.deepcopy(self.docket)
        docket["entries"][0]["earliest_public_receipt"]["disclosed_at"] = "2026-02-01T00:00:00Z"
        self.assert_invalid(docket, message="disclosure timestamp drift")


if __name__ == "__main__":
    unittest.main()
