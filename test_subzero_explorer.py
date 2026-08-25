#!/usr/bin/env python3
"""Subzero Artifact Explorer leftover verifies hashes and refuses sold runtime."""

from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from subzero_explorer import (
    ALREADY_LANDED,
    CALIBRATION,
    EVIDENCE_CLASSES,
    EXPECTED_EXCERPTS,
    HANDOFF_ID,
    LDA_BLOCK,
    LDA_SHA,
    REQUIRED_PHRASES,
    SCHEMA_REL,
    SEARCH_SPACE,
    SLACK_TS,
    V2_SLACK_TS,
    V2_SPEC_ID,
    classify,
    evidence_class,
    load_catalog,
    load_schema,
    measure_from_rows,
    measure_root,
    pinned_links,
    receipt_ok,
)


class TestSubzeroExplorer(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_failed_calibration_is_instrument_failure(self):
        verdict = classify(
            {
                "measured": True,
                "calibration_ok": False,
                "calibration_hits": [],
                "card_present": True,
                "catalog_present": True,
                "door_present": True,
            }
        )
        self.assertEqual(verdict["state"], "UNMEASURED")
        self.assertIn("instrument failure", verdict["note"])
        self.assertIn("never 0", verdict["note"].lower())

    def test_missing_paths_are_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "door_present": False,
                "misses": ["ground/SUBZERO_EXPLORER.md"],
                "calibration_ok": True,
            }
        )
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_sold_host_training_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "door_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "excerpt_count": EXPECTED_EXCERPTS,
                "hash_match_count": EXPECTED_EXCERPTS,
                "runtime_sold": False,
                "host_training_sold": True,
                "titan_mutation_sold": False,
                "lda_blocked": True,
                "copy_private_lda": False,
                "structural_only": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
                "titan": "NOT_WRITTEN",
                "schema_ok": True,
                "v2_present": True,
                "presence_never_escalates": True,
                "evidence_classes_strict": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("host training", verdict["note"].lower())

    def test_complete_leftover_is_integrated(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "door_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "excerpt_count": EXPECTED_EXCERPTS,
                "hash_match_count": EXPECTED_EXCERPTS,
                "runtime_sold": False,
                "host_training_sold": False,
                "titan_mutation_sold": False,
                "lda_blocked": True,
                "copy_private_lda": False,
                "structural_only": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
                "titan": "NOT_WRITTEN",
                "schema_ok": True,
                "v2_present": True,
                "presence_never_escalates": True,
                "evidence_classes_strict": True,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("still not the file", verdict["note"])

    def test_v2_gap_without_schema_is_not_landed(self):
        measured = measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "door_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "excerpt_count": EXPECTED_EXCERPTS,
                "hash_match_count": EXPECTED_EXCERPTS,
                "runtime_sold": False,
                "host_training_sold": False,
                "titan_mutation_sold": False,
                "lda_blocked": True,
                "copy_private_lda": False,
                "structural_only": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
                "titan": "NOT_WRITTEN",
                "schema_ok": False,
                "v2_present": False,
                "presence_never_escalates": False,
                "evidence_classes_strict": False,
            }
        )
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertIn("v2 receipt-gap", verdict["note"])

    def test_malformed_and_presence_never_escalate(self):
        self.assertEqual(evidence_class({}), "UNKNOWN")
        self.assertEqual(evidence_class({"malformed": True, "header_ok": True}), "UNKNOWN")
        self.assertEqual(evidence_class({"missing": True}), "UNKNOWN")
        self.assertEqual(
            evidence_class(
                {
                    "presence_only": True,
                    "header_ok": True,
                    "hash_match": True,
                    "path": "excerpts/20260823/muhl_grbn.mno",
                }
            ),
            "STRUCTURAL_ONLY",
        )
        self.assertEqual(
            evidence_class({"login_required": True, "header_ok": True, "hash_match": True}),
            "UNKNOWN",
        )
        self.assertEqual(
            evidence_class({"privileged_tier": True, "header_ok": True, "hash_match": True}),
            "UNKNOWN",
        )
        bad_runtime = {
            "path": "excerpts/20260823/muhl_grbn.mno",
            "runtime_receipt": {"kind": "SUBZERO_RUNTIME_RECEIPT"},
        }
        self.assertEqual(evidence_class(bad_runtime), "UNKNOWN")
        self.assertFalse(receipt_ok({"kind": "SUBZERO_RUNTIME_RECEIPT"}, "SUBZERO_RUNTIME_RECEIPT"))
        runtime = {
            "kind": "SUBZERO_RUNTIME_RECEIPT",
            "artifact": "excerpts/20260823/muhl_grbn.mno",
            "sha256": "a" * 64,
            "cross_process": True,
            "pid": os.getpid() + 17,
            "host": "other-process",
            "no_auth": True,
            "no_gate": True,
            "login_required": False,
            "privileged_tier": False,
        }
        self.assertEqual(
            evidence_class(
                {
                    "path": "excerpts/20260823/muhl_grbn.mno",
                    "runtime_receipt": runtime,
                }
            ),
            "RUNTIME_MEASURED",
        )
        same_pid = dict(runtime)
        same_pid["pid"] = os.getpid()
        self.assertEqual(
            evidence_class(
                {
                    "path": "excerpts/20260823/muhl_grbn.mno",
                    "runtime_receipt": same_pid,
                }
            ),
            "UNKNOWN",
        )
        buyer = {
            "kind": "SUBZERO_BUYER_VALIDATION",
            "artifact": "excerpts/20260823/muhl_grbn.mno",
            "sha256": "b" * 64,
            "status": "PASS",
            "bound": True,
            "buyer_id": "P01_catalog_receipt",
            "no_auth": True,
            "no_gate": True,
            "login_required": False,
            "privileged_tier": False,
        }
        self.assertEqual(
            evidence_class(
                {
                    "path": "excerpts/20260823/muhl_grbn.mno",
                    "buyer_receipt": buyer,
                }
            ),
            "CUSTOMER_READY",
        )
        unbound = dict(buyer)
        unbound["bound"] = False
        self.assertEqual(
            evidence_class(
                {
                    "path": "excerpts/20260823/muhl_grbn.mno",
                    "buyer_receipt": unbound,
                }
            ),
            "UNKNOWN",
        )
        self.assertEqual(list(EVIDENCE_CLASSES), ["STRUCTURAL_ONLY", "RUNTIME_MEASURED", "CUSTOMER_READY", "UNKNOWN"])

    def test_live_tree_has_the_leftover(self):
        row = measure_root(ROOT)
        self.assertTrue(row["measured"])
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(row["landed_missing"], [])
        self.assertEqual(row["excerpt_count"], EXPECTED_EXCERPTS)
        self.assertEqual(row["hash_match_count"], EXPECTED_EXCERPTS)
        self.assertTrue(row["structural_only"])
        self.assertTrue(row["lda_blocked"])
        self.assertFalse(row["host_training_sold"])
        self.assertFalse(row["runtime_sold"])
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(SLACK_TS, "1787646413.997539")
        self.assertEqual(HANDOFF_ID, "jojo-model-work-profitability-bridge-20260825-01")
        self.assertEqual(LDA_SHA, "fb0b0b2f59f8ca81741371b6ddd8036b164e77e8")
        self.assertEqual(LDA_BLOCK, "BLOCKED_ON_PUBLISHED_WIDE_RECEIVER_RESULT")
        self.assertEqual(len(CALIBRATION), 4)
        self.assertGreaterEqual(len(SEARCH_SPACE), 8)
        with open(os.path.join(ROOT, "ground", "SUBZERO_EXPLORER.json"), encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["label"], "STRUCTURAL_ONLY")
        self.assertEqual(catalog["host_training"], "NOT_SOLD")
        self.assertEqual(catalog["lda_state"], LDA_BLOCK)
        self.assertEqual(catalog["expected_excerpts"], EXPECTED_EXCERPTS)
        self.assertEqual(catalog["evidence_classes"], list(EVIDENCE_CLASSES))
        self.assertEqual(catalog["v2"]["spec_id"], V2_SPEC_ID)
        self.assertEqual(catalog["v2"]["slack_ts"], V2_SLACK_TS)
        self.assertTrue(catalog["v2"]["presence_never_escalates"])
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertTrue(row["schema_ok"])
        self.assertTrue(row["v2_present"])
        self.assertTrue(row["presence_never_escalates"])
        self.assertTrue(row["evidence_classes_strict"])
        self.assertNotEqual(row["source_commit"], "FINDER-FAILED")
        self.assertNotEqual(row["source_tree"], "FINDER-FAILED")
        self.assertEqual(len(row["source_commit"]), 40)
        pin = pinned_links(row["source_commit"])
        self.assertIn(row["source_commit"], pin[SCHEMA_REL.replace("\\", "/")])
        self.assertNotIn("/HEAD/", pin[SCHEMA_REL.replace("\\", "/")])
        self.assertGreaterEqual(row["archetypes"]["fabricators"], 53)
        self.assertGreaterEqual(row["archetypes"]["tests"], 32)
        with open(os.path.join(ROOT, SCHEMA_REL), encoding="utf-8") as handle:
            schema = load_schema(handle.read())
        self.assertTrue(schema["ok"])
        self.assertFalse(any(item.get("runtime_measured") for item in row["excerpts"]))
        self.assertTrue(all(item.get("evidence_class") == "STRUCTURAL_ONLY" for item in row["excerpts"]))


if __name__ == "__main__":
    unittest.main()
