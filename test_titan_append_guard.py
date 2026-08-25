#!/usr/bin/env python3
"""Titan append guard measures a fixture. It does not write titan.gguf."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from titan_append_guard import (
    INCIDENT_BASE,
    INCIDENT_COPY_COUNT,
    INCIDENT_FIRST_END,
    INCIDENT_LIVE_SIZE,
    INCIDENT_PAYLOAD,
    INCIDENT_SHA256,
    SLACK_TS,
    build_fixture,
    classify,
    identical_copy_count,
    load_catalog,
    measure_from_rows,
    measure_spans,
    measure_tree,
    refuse_further_append,
    repair_plan,
)


class TestTitanAppendGuard(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_incident_arithmetic_is_three_copies(self):
        extra = INCIDENT_LIVE_SIZE - INCIDENT_BASE
        self.assertEqual(extra, INCIDENT_PAYLOAD * INCIDENT_COPY_COUNT)
        self.assertEqual(INCIDENT_FIRST_END - INCIDENT_BASE, INCIDENT_PAYLOAD)
        self.assertEqual(INCIDENT_LIVE_SIZE - INCIDENT_FIRST_END, INCIDENT_PAYLOAD * 2)

    def test_refuse_closes_incident_size(self):
        packet = {
            "claimed_append_base": INCIDENT_BASE,
            "claimed_append_end": INCIDENT_FIRST_END,
            "written_bytes": INCIDENT_PAYLOAD,
            "titan": "WRITTEN",
        }
        refused, reason = refuse_further_append(packet, INCIDENT_LIVE_SIZE)
        self.assertTrue(refused)
        self.assertIn("103831308164", reason)
        allowed, _ = refuse_further_append(packet, INCIDENT_BASE)
        self.assertFalse(allowed)

    def test_refuse_closes_unexpected_size_without_realloc(self):
        packet = {
            "claimed_append_base": 100,
            "claimed_append_end": 108,
            "written_bytes": 8,
            "titan": "WRITTEN",
        }
        refused, reason = refuse_further_append(packet, 116)
        self.assertTrue(refused)
        self.assertIn("will not reallocate", reason)

    def test_fixture_three_identical_spans(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, baseline, length, sha = build_fixture(tmp)
            spans = measure_spans(path, baseline, length)
            self.assertEqual(len(spans), 3)
            self.assertEqual(identical_copy_count(spans), 3)
            self.assertEqual({row["sha256"] for row in spans}, {sha})
            before = os.path.getsize(path)
            refused, _ = refuse_further_append(
                {
                    "claimed_append_base": baseline,
                    "claimed_append_end": baseline + length,
                    "written_bytes": length,
                },
                before,
                path=path,
            )
            self.assertTrue(refused)
            self.assertEqual(os.path.getsize(path), before)

    def test_apply_flag_blocks_land(self):
        measured = measure_from_rows(
            {
                "live_size": INCIDENT_LIVE_SIZE,
                "payload_len": INCIDENT_PAYLOAD,
                "copy_count": INCIDENT_COPY_COUNT,
                "span_sha256": INCIDENT_SHA256,
                "refused": True,
                "fixture_copies": 3,
                "fixture_identical": True,
                "apply": True,
                "repair_plan_apply": False,
                "titan_write": "WRITTEN",
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")
        self.assertIn("Do not truncate", classify(measured)["note"])

    def test_repair_plan_stays_off(self):
        plan = repair_plan()
        self.assertFalse(plan["apply"])
        self.assertEqual(plan["canonical_first_copy"], "UNDECIDED")
        self.assertEqual(plan["preserve_bytes"], INCIDENT_LIVE_SIZE)
        self.assertIn("truncate", plan["do_not"])

    def test_live_tree_matches_the_report(self):
        catalog_path = os.path.join(ROOT, "ground", "TITAN_APPEND_GUARD.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog_text = handle.read()
        catalog = load_catalog(catalog_text)
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertFalse(catalog["apply"])
        self.assertTrue(catalog["preserve_exact"])
        self.assertEqual(catalog["live_size"], INCIDENT_LIVE_SIZE)
        self.assertEqual(catalog["payload_len"], INCIDENT_PAYLOAD)
        self.assertEqual(catalog["copy_count"], INCIDENT_COPY_COUNT)
        self.assertEqual(catalog["span_sha256"], INCIDENT_SHA256)
        row = measure_tree(ROOT, catalog_text)
        self.assertTrue(row["measured"])
        self.assertTrue(row["arithmetic_ok"])
        self.assertTrue(row["sha_ok"])
        self.assertTrue(row["refused"])
        self.assertEqual(row["fixture_copies"], 3)
        self.assertTrue(row["fixture_identical"])
        self.assertFalse(row["repair_plan"]["apply"])
        self.assertEqual(row["titan_write"], "NOT_WRITTEN")
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertIn("still not the file", classify(row)["note"])


if __name__ == "__main__":
    unittest.main()
