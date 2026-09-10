# SPDX-License-Identifier: Apache-2.0
"""Predecessor-killing tests for canonical TITAN release drift reporting."""
from __future__ import annotations

import copy
import hashlib
import json
import tarfile
import unittest

import build_integrated as b
import release_drift as d

OLD_ARCHIVE_SHA256 = "17f536087b3a6baf4ae1222a051285766a3ea8c2ca5af6edc190d4f527e12b86"
NEW_ARCHIVE_SHA256 = "5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1"
EXPECTED_PREDECESSOR_DRIFT = [
    "TITAN-RELEASE.md",
    "reference/decision/README.md",
]


class ReleaseDriftTests(unittest.TestCase):
    def test_live_release_is_source_exact(self):
        report = d.analyze()
        self.assertTrue(report["clean"], json.dumps(report, indent=2, sort_keys=True))
        self.assertEqual(report["runtime_files_expected"], 109)
        self.assertEqual(report["runtime_member_drift"], [])
        self.assertEqual(report["manifest_metadata_drift"], [])
        self.assertEqual(report["receipt_drift"], [])
        self.assertEqual(report["artifacts"]["archive"]["actual_sha256"], NEW_ARCHIVE_SHA256)

    def test_superseded_archive_is_retained_and_names_the_two_doc_drifts(self):
        historical = b.ROOT / "exports/historical" / f"titan-{OLD_ARCHIVE_SHA256}.tar.gz"
        raw = historical.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), OLD_ARCHIVE_SHA256)
        with tarfile.open(historical, mode="r:gz") as archive:
            predecessor = json.load(archive.extractfile("SOURCE.json"))
        expected = json.loads(b.render()[1])
        members, metadata = d.compare_manifests(predecessor, expected)
        self.assertEqual([row["member"] for row in members], EXPECTED_PREDECESSOR_DRIFT)
        self.assertEqual(metadata, [])
        for row in members:
            self.assertEqual({field["field"] for field in row["fields"]}, {"bytes", "sha256"})
        self.assertTrue(all(".py" not in row["member"] for row in members))

    def test_member_add_remove_and_bool_int_differences_fail_closed(self):
        expected = {
            "runtime": {
                "main.py": {"source_path": "main.py", "sha256": "a" * 64, "bytes": 7},
                "doc.md": {"source_path": "doc.md", "sha256": "b" * 64, "bytes": 9},
            },
            "default": {"enabled": True},
        }
        actual = copy.deepcopy(expected)
        actual["runtime"]["main.py"]["bytes"] = True
        del actual["runtime"]["doc.md"]
        actual["runtime"]["extra.py"] = {
            "source_path": "extra.py",
            "sha256": "c" * 64,
            "bytes": 1,
        }
        members, metadata = d.compare_manifests(actual, expected)
        self.assertEqual([row["member"] for row in members], ["doc.md", "extra.py", "main.py"])
        self.assertEqual(metadata, [])
        main = next(row for row in members if row["member"] == "main.py")
        self.assertEqual(main["fields"], [{"field": "bytes", "actual": True, "expected": 7}])

    def test_true_vs_one_and_false_vs_zero_fail_closed(self):
        """Predecessor-killing: Python True==1 / False==0 must not hide JSON type drift."""
        # Top-level scalar field True vs 1
        deltas = d.field_deltas({"flag": True}, {"flag": 1})
        self.assertEqual(deltas, [{"field": "flag", "actual": True, "expected": 1}])

        # Top-level scalar field False vs 0
        deltas = d.field_deltas({"flag": False}, {"flag": 0})
        self.assertEqual(deltas, [{"field": "flag", "actual": False, "expected": 0}])

        # Nested inside dict (runtime member shape)
        expected = {
            "runtime": {
                "main.py": {"source_path": "main.py", "sha256": "a" * 64, "bytes": 1},
            }
        }
        actual = copy.deepcopy(expected)
        actual["runtime"]["main.py"]["bytes"] = True
        members, metadata = d.compare_manifests(actual, expected)
        self.assertEqual([row["member"] for row in members], ["main.py"])
        self.assertEqual(metadata, [])
        main = members[0]
        self.assertEqual(main["fields"], [{"field": "bytes", "actual": True, "expected": 1}])

        # Nested False vs 0
        expected2 = {
            "runtime": {
                "main.py": {"source_path": "main.py", "sha256": "a" * 64, "bytes": 0},
            }
        }
        actual2 = copy.deepcopy(expected2)
        actual2["runtime"]["main.py"]["bytes"] = False
        members2, _ = d.compare_manifests(actual2, expected2)
        self.assertEqual([row["member"] for row in members2], ["main.py"])
        self.assertEqual(
            members2[0]["fields"], [{"field": "bytes", "actual": False, "expected": 0}]
        )

        # Nested list / mapping recursion
        self.assertFalse(d.json_values_equal([True], [1]))
        self.assertFalse(d.json_values_equal({"x": False}, {"x": 0}))
        self.assertTrue(d.json_values_equal({"x": True}, {"x": True}))
        self.assertTrue(d.json_values_equal([0, False], [0, False]))
        self.assertFalse(d.json_values_equal([0, False], [0, 0]))

        # _MISSING handling
        self.assertTrue(d.json_values_equal(d._MISSING, d._MISSING))
        self.assertFalse(d.json_values_equal(d._MISSING, None))
        self.assertFalse(d.json_values_equal(True, d._MISSING))

    def test_malformed_runtime_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "actual manifest runtime"):
            d.compare_manifests({"runtime": []}, {"runtime": {}})
        with self.assertRaisesRegex(ValueError, "runtime member 'main.py'"):
            d.compare_manifests({"runtime": {"main.py": []}}, {"runtime": {"main.py": {}}})


if __name__ == "__main__":
    unittest.main()
