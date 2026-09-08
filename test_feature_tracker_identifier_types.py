#!/usr/bin/env python3
"""Feature/evidence identifiers stay typed and exact through JSON projection."""
from __future__ import annotations

import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent / "host"))
import feature_tracker as ft


BAD_TYPES = (12345678, -12345678, 12345678.5, True, False, None, [], {}, ["abcdefgh"])
BAD_STRINGS = ("", "shortid", "a" * 81, "abcdefgh\n", "abcdefgh\r\n", "abcdefgh\t", "abc/defgh", "abc defgh")
GOOD_IDS = ("12345678", "a" * 80, "Abc-123_._")


def feature(identifier="sample-feature-01"):
    return {
        "schema": ft.SCHEMA_FEATURE,
        "id": identifier,
        "name": "Sample feature",
        "capability": "A source-backed sample feature.",
        "owner_subsystem": "sample",
        "carrier": "ROWAN",
        "claimed_paths": ["source.py"],
        "test_paths": [],
        "public_entrypoint": "source.py",
        "dependencies": [],
        "resource_links": [],
        "next_gap": "Measure the deployed source.",
    }


def evidence(**changes):
    record = {
        "schema": ft.SCHEMA_EVIDENCE,
        "id": "sample-evidence-01",
        "feature_id": "sample-feature-01",
        "kind": "RECEIPT",
        "receipt": "sample-receipt-01",
    }
    record.update(changes)
    return record


class IdentifierValidationTests(unittest.TestCase):
    def test_feature_rejects_non_string_ids_without_mutation(self):
        for identifier in BAD_TYPES:
            with self.subTest(identifier=identifier):
                record = feature(identifier)
                original = copy.deepcopy(record)
                self.assertTrue(ft.validate_feature(record))
                self.assertEqual(record, original)

    def test_feature_requires_a_whole_string_match(self):
        for identifier in BAD_STRINGS:
            with self.subTest(identifier=identifier):
                self.assertTrue(ft.validate_feature(feature(identifier)))

    def test_evidence_rejects_non_string_identifiers_without_mutation(self):
        for field in ("id", "feature_id"):
            for identifier in BAD_TYPES:
                with self.subTest(field=field, identifier=identifier):
                    record = evidence(**{field: identifier})
                    original = copy.deepcopy(record)
                    self.assertTrue(ft.validate_evidence(record))
                    self.assertEqual(record, original)

    def test_evidence_requires_whole_string_identifiers(self):
        for field in ("id", "feature_id"):
            for identifier in BAD_STRINGS:
                with self.subTest(field=field, identifier=identifier):
                    self.assertTrue(ft.validate_evidence(evidence(**{field: identifier})))

    def test_supersede_targets_are_typed_whole_string_ids(self):
        for field in ("superseded_by", "replaces"):
            for identifier in BAD_TYPES + BAD_STRINGS:
                with self.subTest(field=field, identifier=identifier):
                    record = evidence(kind="SUPERSEDE", **{field: identifier})
                    self.assertIn("SUPERSEDE needs superseded_by id", ft.validate_evidence(record))

    def test_valid_boundaries_numeric_strings_and_filenames_are_preserved(self):
        for identifier in GOOD_IDS:
            with self.subTest(identifier=identifier):
                self.assertEqual(ft.validate_feature(feature(identifier), identifier + ".json"), [])
                record = evidence(id=identifier, feature_id=identifier)
                self.assertEqual(ft.validate_evidence(record, identifier + ".json"), [])
                for field in ("superseded_by", "replaces"):
                    self.assertEqual(ft.validate_evidence(evidence(kind="SUPERSEDE", **{field: identifier})), [])
                self.assertIn("filename must equal id.json", ft.validate_feature(feature(identifier), "wrong.json"))
                self.assertIn("filename must equal id.json", ft.validate_evidence(record, "wrong.json"))


class IdentifierProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="commons-ft-identifiers-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "source.py").write_text("value = 1\n", encoding="utf-8")

    def write(self, folder, filename, record):
        path = self.root / folder / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record) + "\n", encoding="utf-8")
        return path

    def project(self):
        return ft.project(str(self.root))

    def test_numeric_feature_record_is_reported_not_projected(self):
        path = self.write(ft.REGISTRY_DIR, "12345678.json", feature(12345678))
        before = path.read_bytes()
        projection = self.project()
        self.assertEqual(projection["n_invalid"], 1)
        self.assertEqual(projection["features"], [])
        self.assertEqual(path.read_bytes(), before)

    def test_numeric_feature_reference_is_reported_not_silently_unmatched(self):
        self.write(ft.REGISTRY_DIR, "12345678.json", feature("12345678"))
        self.write(ft.EVIDENCE_DIR, "sample-evidence-01.json", evidence(feature_id=12345678))
        projection = self.project()
        self.assertEqual(projection["n_invalid"], 1)
        self.assertEqual(projection["features"][0]["evidence_ids"], [])
        self.assertEqual(projection["features"][0]["rollup"], "SOURCE_BUILT")

    def test_numeric_evidence_id_cannot_promote_live(self):
        self.write(ft.REGISTRY_DIR, "sample-feature-01.json", feature())
        self.write(ft.EVIDENCE_DIR, "12345678.json", evidence(
            id=12345678, kind="LIVE_MEASUREMENT", sha="a" * 40,
            url="https://example.invalid/source.py",
        ))
        projection = self.project()
        self.assertEqual(projection["n_invalid"], 1)
        self.assertEqual(projection["features"][0]["live_status"], "UNMEASURED")
        self.assertEqual(projection["features"][0]["evidence_ids"], [])

    def test_numeric_supersede_target_cannot_change_rollup(self):
        self.write(ft.REGISTRY_DIR, "sample-feature-01.json", feature())
        self.write(ft.EVIDENCE_DIR, "sample-evidence-01.json", evidence(
            kind="SUPERSEDE", superseded_by=12345678,
        ))
        projection = self.project()
        self.assertEqual(projection["n_invalid"], 1)
        self.assertEqual(projection["features"][0]["rollup"], "SOURCE_BUILT")
        self.assertEqual(projection["features"][0]["superseded_by"], "")

    def test_valid_numeric_string_reference_still_matches(self):
        self.write(ft.REGISTRY_DIR, "12345678.json", feature("12345678"))
        self.write(ft.EVIDENCE_DIR, "sample-evidence-01.json", evidence(feature_id="12345678"))
        projection = self.project()
        self.assertEqual(projection["n_invalid"], 0)
        self.assertEqual(projection["features"][0]["evidence_ids"], ["sample-evidence-01"])
        self.assertEqual(projection["features"][0]["receipts"], ["sample-receipt-01"])

    def test_cli_returns_failure_and_keeps_invalid_input_bytes(self):
        path = self.write(ft.REGISTRY_DIR, "12345678.json", feature(12345678))
        before = path.read_bytes()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = ft.main(["--root", str(self.root)])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue())["n_invalid"], 1)
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
