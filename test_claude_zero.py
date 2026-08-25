#!/usr/bin/env python3
"""Claude-zero leftover is a measurement, not a remint of finder_zero."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from claude_zero import (
    FAILED,
    FOUND,
    UNVERIFIED,
    classify,
    find_pattern,
    load_catalog,
    measure_from_rows,
    measure_paths,
    refuse_zero_verdict,
)


class TestClaudeZero(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertEqual(row["result"], UNVERIFIED)
        self.assertIn("not 0", row["note"])

    def test_missing_calibrator_is_finder_failed(self):
        measured = measure_from_rows(
            [
                {
                    "id": "gguf-four-byte",
                    "path": "host/gguf_pp.py",
                    "pattern": "GGUF",
                    "present": False,
                    "text": "",
                }
            ]
        )
        self.assertEqual(measured["calibration"], "FAIL")
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(verdict["result"], FAILED)
        self.assertIn("FINDER-FAILED", verdict["note"])
        self.assertNotIn("count", verdict)

    def test_pattern_miss_is_unverified_not_zero(self):
        hit = find_pattern("no magic here", "GGUF", "host/gguf_pp.py", min_len=4)
        self.assertEqual(hit["result"], UNVERIFIED)
        self.assertIn("search_space", hit)
        self.assertEqual(hit["search_space"]["pattern"], "GGUF")
        self.assertEqual(hit["search_space"]["pattern_len"], 4)
        self.assertIsNone(hit.get("count"))

    def test_silent_zero_is_refused(self):
        row = refuse_zero_verdict({"count": 0, "path": "x", "pattern": "GGUF"})
        self.assertEqual(row["result"], FAILED)
        self.assertNotIn("count", row)
        self.assertIn("search_space", row)

    def test_gguf_four_byte_y_from_found_bytes(self):
        body = 'assert mm[:4] == b"GGUF", "not a GGUF file"'
        hit = find_pattern(body, "GGUF", "host/gguf_pp.py", min_len=4)
        self.assertEqual(hit["result"], FOUND)
        self.assertTrue(hit["y"].startswith("GGUF"))
        self.assertEqual(body[hit["offset"] : hit["offset"] + 4], "GGUF")

    def test_calibrated_with_retract_is_integrated(self):
        measured = measure_from_rows(
            [
                {
                    "id": "gguf-four-byte",
                    "path": "host/gguf_pp.py",
                    "pattern": "GGUF",
                    "min_len": 4,
                    "present": True,
                    "text": 'b"GGUF" four-byte magic',
                },
                {
                    "id": "head-law",
                    "path": "ground/HEAD.md",
                    "pattern": "A bake is not the board",
                    "present": True,
                    "text": "A bake is not the board\n",
                },
            ],
            [
                {
                    "id": "cairn-magic-gguf",
                    "claim": "none of the known magics present",
                    "why": "GGUF is four",
                }
            ],
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")
        self.assertEqual(
            measured["retracted_claude_zeros"][0]["verdict"], "RETRACTED"
        )

    def test_found_without_retract_list_is_candidate(self):
        measured = measure_from_rows(
            [
                {
                    "id": "gguf-four-byte",
                    "path": "host/gguf_pp.py",
                    "pattern": "GGUF",
                    "present": True,
                    "text": "GGUF",
                }
            ]
        )
        self.assertEqual(classify(measured)["state"], "CANDIDATE")

    def test_does_not_remint_finder_zero(self):
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "host", "finder_zero.py")))
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "ground", "FINDER_ZERO.md")))

    def test_live_catalog_calibrates_and_retracts(self):
        catalog_path = os.path.join(ROOT, "ground", "CLAUDE_ZERO.json")
        row = measure_paths(ROOT, catalog_path)
        self.assertTrue(row["measured"], row.get("error"))
        self.assertEqual(row["missing"], [])
        self.assertEqual(row["failed_ids"], [])
        self.assertEqual(row["unverified_ids"], [])
        self.assertEqual(row["calibration"], "PASS")
        self.assertGreaterEqual(len(row["found_ids"]), 4)
        self.assertGreaterEqual(len(row["retracted_claude_zeros"]), 4)
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(row["slack_ts"], "1787638427.993939")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], "1787638427.993939")
        paths = [item["path"] for item in catalog["calibrators"]]
        self.assertIn("host/gguf_pp.py", paths)
        self.assertIn(
            "p/cairn-every-zero-i-printed-was-mine-20260820-06.md", paths
        )
        gguf = [item for item in row["calibrators"] if item["id"] == "gguf-four-byte"][0]
        self.assertEqual(gguf["result"], FOUND)
        self.assertTrue(str(gguf["y"]).startswith("GGUF"))
        self.assertEqual(classify(row)["state"], "INTEGRATED")


if __name__ == "__main__":
    unittest.main()
