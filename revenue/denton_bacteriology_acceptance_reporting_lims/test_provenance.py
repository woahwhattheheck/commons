#!/usr/bin/env python3
"""Isolated provenance regression for Denton bacteriology acceptance/reporting."""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import denton_bacteriology_acceptance_reporting_lims as gate

SOURCE_FIELDS = (
    "submission_id",
    "sample_id",
    "account_id",
    "pws_id",
    "client_id",
    "route",
    "method",
    "report_form",
    "custody_signed",
    "custody_time",
    "collected_on",
    "bottle_expires",
    "temperature_c",
    "hold_time_hours",
    "source_revision",
)
COORDINATE_FIELDS = (
    "account_id",
    "pws_id",
    "client_id",
    "sample_id",
    "source_revision",
)


def independent_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class DentonBacteriologyProvenanceTests(unittest.TestCase):
    def test_all_160_accepted_coordinates_and_hashes_match_frozen_input(self) -> None:
        expected: dict[str, dict[str, object]] = {}
        for row in gate.build_acceptance_fixture():
            if row["exception_type"] is not None:
                continue
            norm = gate.normalize_row(row)
            payload = {field: norm[field] for field in SOURCE_FIELDS}
            expected[norm["submission_id"]] = {
                **{field: norm[field] for field in COORDINATE_FIELDS},
                "source_hash": independent_sha256(payload),
            }

        result = gate.run_gate()
        actual = {item["submission_id"]: item for item in result["submissions"]}
        self.assertEqual(len(expected), 160)
        self.assertEqual(set(actual), set(expected))

        for submission_id, wanted in expected.items():
            observed = actual[submission_id]
            for field in COORDINATE_FIELDS:
                self.assertEqual(observed[field], wanted[field])
            self.assertEqual(observed["source_hash"], wanted["source_hash"])

    def test_lineage_is_exact_and_hold_rows_add_no_downstream_outputs(self) -> None:
        result = gate.run_gate()
        worksheets = {
            item["worksheet_id"]: item for item in result["worksheet_records"]
        }
        reports = {item["report_id"]: item for item in result["report_records"]}

        self.assertEqual(len(result["submissions"]), 160)
        self.assertEqual(len(worksheets), 160)
        self.assertEqual(len(reports), 160)
        for submission in result["submissions"]:
            worksheet = worksheets[submission["worksheet_id"]]
            report = reports[submission["report_id"]]
            self.assertEqual(worksheet["accession_id"], submission["accession_id"])
            self.assertEqual(worksheet["sample_id"], submission["sample_id"])
            self.assertEqual(worksheet["method"], submission["method"])
            self.assertEqual(worksheet["report_form"], submission["report_form"])
            self.assertEqual(worksheet["route"], submission["route"])
            self.assertEqual(report["accession_id"], submission["accession_id"])
            self.assertEqual(report["worksheet_id"], submission["worksheet_id"])
            self.assertEqual(report["sample_id"], submission["sample_id"])
            self.assertEqual(report["method"], submission["method"])
            self.assertEqual(report["report_form"], submission["report_form"])
            self.assertEqual(report["source_hash"], submission["source_hash"])

        journal = gate.empty_journal()
        hold_effects = 0
        for row in gate.build_acceptance_fixture():
            before = (
                len(journal["accessions"]),
                len(journal["worksheets"]),
                len(journal["reports"]),
            )
            effect = gate.ingest_row(journal, row)
            if effect["kind"] != "HOLD":
                continue
            hold_effects += 1
            after = (
                len(journal["accessions"]),
                len(journal["worksheets"]),
                len(journal["reports"]),
            )
            self.assertEqual(after, before)
            self.assertEqual(journal["holds"][-1]["worksheets_created"], 0)
            self.assertEqual(journal["holds"][-1]["reports_created"], 0)
            self.assertNotIn(
                gate.normalize_row(row)["submission_id"], journal["submissions"]
            )

        self.assertEqual(hold_effects, 40)
        self.assertEqual(len(journal["accessions"]), 160)
        self.assertEqual(len(journal["worksheets"]), 160)
        self.assertEqual(len(journal["reports"]), 160)
        self.assertEqual(len(journal["holds"]), 40)


if __name__ == "__main__":
    unittest.main()
