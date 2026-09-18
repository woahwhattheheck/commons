#!/usr/bin/env python3
"""Independent frozen truth for ward-feed-nirs-intake-validator-lims-01.

Expected values in this file are literal evidence captured from the shipped current-
main artifact. They intentionally do not import the product's mutable count maps,
route maps, hash helper, receipt, or contract as the oracle.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import unittest

import ward_feed_nirs_intake_validator as gate

DEMAND_ID = "ward-feed-nirs-intake-validator-lims-01"
EXPANDED_ROWS_SHA256 = "58b3e2fb8dfc0fba1741ce8f96b1a6bf4c9bae9b8a45bc2148f8c055fe1a9084"
FIXTURE_PAYLOAD_SHA256 = "42b2320f7651ea9b32abe9708af44ebb6524ec8174b589a2b86372e4e12882df"
ACCESSION_ROWS_SHA256 = "897b70629f9bb2059f129aa43107f16ad4fec7683861be82974fce9fea7a3afa"
HOLD_ROWS_SHA256 = "4862335ef3f2fd850e22da1db4485acf8f40824cd2925e08bc726def980c3bae"
WORKSHEET_ROWS_SHA256 = "b3edc405087db8cf2b988a6742a7cdd2e50e091d0ac36f8c6ce2aa6659cd2fca"
STAGED_REPORT_ROWS_SHA256 = "df518d459351142e037e41acd2134ecd6e80a90401bbab2a79a3abb1cc6c3148"
AUDIT_SHA256 = "d1920635f08b8c1171fd5f43ed65e75e95bb20b29994524746f00fe9d8a9cabc"
REPORT_DIGEST = "ca567854805a3a894cc1b4392083bc2955dd8c2d3944f515ae3114f418a6c1ed"

EXPECTED_HOLDS = {
    "HOLD_DESC_CALIBRATION_CONFLICT": 13,
    "HOLD_DUPLICATE_BAG_LABEL": 13,
    "HOLD_INSUFFICIENT_PREP": 13,
    "HOLD_MISSING_ANALYSIS": 14,
    "HOLD_MISSING_ID": 14,
    "HOLD_TIME_WINDOW_VIOLATION": 13,
}
EXPECTED_ROUTES = {"NIRS": 240, "WET_CHEM": 80}


def _canonical(value) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _sha256(value) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


class WardIndependentFrozenOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = gate.build_acceptance_fixture()
        cls.result = gate.run_gate(cls.rows)

    def test_expanded_fixture_is_bound_to_literal_truth(self) -> None:
        self.assertEqual(400, len(self.rows))
        self.assertEqual(EXPANDED_ROWS_SHA256, _sha256(self.rows))
        self.assertEqual(
            FIXTURE_PAYLOAD_SHA256,
            _sha256({"demand_id": DEMAND_ID, "rows": self.rows}),
        )

        holds = Counter(row["expected_hold"] for row in self.rows if row["expected_hold"] is not None)
        self.assertEqual(EXPECTED_HOLDS, dict(sorted(holds.items())))
        self.assertEqual(80, sum(holds.values()))

        routes = Counter(row["expected_route"] for row in self.rows if row["expected_hold"] is None)
        self.assertEqual(EXPECTED_ROUTES, dict(sorted(routes.items())))
        self.assertEqual(320, sum(routes.values()))

    def test_materialized_outputs_are_bound_to_literal_row_digests(self) -> None:
        self.assertEqual(ACCESSION_ROWS_SHA256, _sha256(self.result["accession_rows"]))
        self.assertEqual(HOLD_ROWS_SHA256, _sha256(self.result["hold_rows"]))
        self.assertEqual(WORKSHEET_ROWS_SHA256, _sha256(self.result["worksheet_rows"]))
        self.assertEqual(STAGED_REPORT_ROWS_SHA256, _sha256(self.result["staged_report_rows"]))
        self.assertEqual(EXPECTED_HOLDS, dict(sorted(self.result["hold_counter"].items())))
        self.assertEqual(EXPECTED_ROUTES, dict(sorted(self.result["routes"].items())))

    def test_shipped_receipt_digests_are_literal_not_self_derived_oracles(self) -> None:
        self.assertEqual(AUDIT_SHA256, self.result["audit_sha256"])
        self.assertEqual(REPORT_DIGEST, self.result["report_digest"])
        self.assertEqual(400, self.result["input_count"])
        self.assertEqual(320, self.result["accessioned"])
        self.assertEqual(80, self.result["held"])
        self.assertEqual(320, self.result["worksheet_count"])
        self.assertEqual(320, self.result["staged_report_count"])
        self.assertEqual(0, self.result["released_reports"])


if __name__ == "__main__":
    unittest.main()
