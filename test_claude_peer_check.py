#!/usr/bin/env python3
"""Peer-check leftover indexes HIS 17c; laptop miss is FINDER-FAILED, never 0."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from claude_peer_check import (
    CALIBRATION,
    REQUIRED_PACKETS,
    SEARCH_SPACE,
    classify,
    index_has_17c,
    laptop_probe,
    load_catalog,
    measure_from_rows,
    measure_root,
    parse_packets,
    self_test,
    title_phrase_probe,
)


def _complete_facts(**overrides):
    facts = {
        "card_present": True,
        "catalog_present": True,
        "dump_present": True,
        "packets_found": list(REQUIRED_PACKETS),
        "packets_missing": [],
        "indexed_17c": True,
        "laptop": {"state": "FINDER-FAILED", "count": None, "hits": []},
        "title_phrases": {"state": "FINDER-FAILED", "count": None, "hits": []},
        "no_auth": True,
        "no_gate": True,
        "calibration_ok": True,
        "calibration_hits": list(CALIBRATION),
        "search_space": list(SEARCH_SPACE),
        "misses": [],
    }
    facts.update(overrides)
    return measure_from_rows(facts)


class TestClaudePeerCheck(unittest.TestCase):
    def test_self_test_ok(self):
        self.assertEqual(self_test(), "ok")

    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertEqual(row["z"], "FINDER-FAILED")
        self.assertIn("Never 0", row["note"])
        self.assertNotIn("count", row)
        self.assertNotEqual(row.get("count"), 0)

    def test_failed_calibration_is_instrument_failure(self):
        verdict = classify(
            {
                "measured": True,
                "calibration_ok": False,
                "calibration_hits": [],
                "card_present": True,
                "catalog_present": True,
                "dump_present": True,
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertEqual(verdict["z"], "FINDER-FAILED")
        self.assertIn("instrument failure", verdict["note"])
        self.assertIn("Never 0", verdict["note"])

    def test_missing_17c_is_not_landed(self):
        verdict = classify(_complete_facts(indexed_17c=False))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(verdict["z"], "FINDER-FAILED")
        self.assertIn("17c", verdict["note"])
        self.assertNotEqual(verdict.get("count"), 0)

    def test_missing_dump_packet_is_not_silent_zero(self):
        verdict = classify(
            _complete_facts(packets_missing=["17c"], indexed_17c=True)
        )
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(verdict["z"], "FINDER-FAILED")
        self.assertIn("17c", verdict["note"])

    def test_integrated_keeps_laptop_finder_failed(self):
        verdict = classify(_complete_facts())
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertEqual(verdict["z"]["laptop"], "FINDER-FAILED")
        self.assertEqual(verdict["z"]["title_phrases"], "FINDER-FAILED")

    def test_parse_packets_skips_ground_zero(self):
        text = "## 0. GROUND\n\n## 1. circuits\n\n## 17c. CLASS 17\n\n"
        self.assertEqual(parse_packets(text), ["1", "17c"])

    def test_index_has_17c_needs_both_names(self):
        self.assertFalse(index_has_17c("P39 only", {}))
        self.assertTrue(index_has_17c("| P40 | Class 17c — hooks", {}))
        self.assertTrue(
            index_has_17c("", {"p40_id": "P40", "p40_packet": "17c"})
        )

    def test_laptop_miss_has_search_space_and_no_count_zero(self):
        row = laptop_probe(["/definitely-not-bryces-laptop"])
        self.assertEqual(row["state"], "FINDER-FAILED")
        self.assertIsNone(row["count"])
        self.assertIn("/definitely-not-bryces-laptop", row["search_space"])

    def test_title_phrase_miss_is_finder_failed(self):
        with tempfile.TemporaryDirectory(prefix="peer-check-titles-") as tmp:
            row = title_phrase_probe(tmp, ["purity spiral", "GOO READ"])
        self.assertEqual(row["state"], "FINDER-FAILED")
        self.assertIsNone(row["count"])

    def test_catalog_keeps_door_open(self):
        with open(os.path.join(ROOT, "ground", "CLAUDE_PEER_CHECK.json"), encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertTrue(catalog["no_auth"])
        self.assertTrue(catalog["no_gate"])
        self.assertEqual(catalog["p40_id"], "P40")
        self.assertEqual(catalog["p40_packet"], "17c")
        self.assertIn("17c", catalog["packets"])
        self.assertIn("P40", catalog["priors"])

    def test_live_tree_indexes_17c(self):
        row = measure_root(ROOT)
        self.assertTrue(row["calibration_ok"])
        self.assertTrue(row["indexed_17c"])
        self.assertEqual(row["packets_missing"], [])
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertEqual(row["laptop"]["state"], "FINDER-FAILED")
        self.assertIsNone(row["laptop"]["count"])
        self.assertNotEqual(row["laptop"]["count"], 0)
        with open(os.path.join(ROOT, "ground", "CLAUDE_PEER_CHECK.md"), encoding="utf-8") as handle:
            card = handle.read()
        self.assertIn("P40", card)
        self.assertIn("17c", card)
        with open(
            os.path.join(ROOT, "muhl", "docs", "CLAUDE_FAILURE_MODES.md"),
            encoding="utf-8",
        ) as handle:
            dump = handle.read()
        self.assertIn("## 17c.", dump)


if __name__ == "__main__":
    unittest.main()
