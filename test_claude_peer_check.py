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
    GIT_COMPANIONS,
    REQUIRED_PACKETS,
    SEARCH_SPACE,
    STALE_OFF_GIT_PHRASE,
    card_claims_companions_off_git,
    classify,
    claude_corner_probe,
    git_companions_probe,
    hard_receive_baseline_probe,
    index_has_17c,
    index_has_a11,
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
        "indexed_a11": True,
        "hard_receive": {
            "state": "FOUND",
            "missing": [],
            "hits": [
                "evidence/bully_sessions/CLAUDE_PROOF_PACKET.md",
                "evidence/bully_sessions/BULLY_CLAUDE.txt",
            ],
            "search_space": [
                "evidence/bully_sessions/CLAUDE_PROOF_PACKET.md",
                "evidence/bully_sessions/BULLY_CLAUDE.txt",
            ],
        },
        "claude_corner": {"state": "FINDER-FAILED", "count": None, "hits": []},
        "git_companions": {
            "state": "FOUND",
            "missing": [],
            "hits": list(GIT_COMPANIONS),
            "search_space": list(GIT_COMPANIONS),
        },
        "card_stale_off_git": False,
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
        self.assertEqual(verdict["z"]["claude_corner"], "FINDER-FAILED")
        self.assertIsNone(verdict["z"].get("count"))
        self.assertNotEqual(verdict.get("count"), 0)

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
        self.assertEqual(catalog["a11_id"], "A11")
        self.assertEqual(catalog["a11_hit"], "HIT-SR01")
        self.assertTrue(catalog["a11_not_permission"])
        self.assertTrue(catalog["a11_not_gate"])
        self.assertIn("A11", catalog["authority"])
        self.assertTrue(catalog["git_companions_on_git"])
        self.assertGreaterEqual(len(catalog["git_companion_paths"]), 9)

    def test_stale_off_git_claim_is_not_landed(self):
        verdict = classify(_complete_facts(card_stale_off_git=True))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(verdict["z"], "FINDER-FAILED")
        self.assertIn("HIT-FM02", verdict["note"])
        self.assertNotEqual(verdict.get("count"), 0)

    def test_missing_git_companion_is_not_silent_zero(self):
        verdict = classify(
            _complete_facts(
                git_companions={
                    "state": "FINDER-FAILED",
                    "missing": ["muhl/docs/BULLY_CLAUDE.txt"],
                    "count": None,
                }
            )
        )
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(verdict["z"], "FINDER-FAILED")
        self.assertIn("BULLY_CLAUDE.txt", verdict["note"])
        self.assertIsNone(
            classify(
                _complete_facts(
                    git_companions={
                        "state": "FINDER-FAILED",
                        "missing": ["muhl/docs/BULLY_CLAUDE.txt"],
                        "count": None,
                    }
                )
            ).get("count")
        )

    def test_card_claims_companions_off_git_phrase(self):
        self.assertTrue(
            card_claims_companions_off_git("Owner-disk companions (not always on git)")
        )
        self.assertFalse(card_claims_companions_off_git("Git companions measured on main"))
        self.assertEqual(STALE_OFF_GIT_PHRASE, "not always on git")

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
        self.assertIn("A11", card)
        self.assertIn("HIT-SR01", card)
        self.assertIn("RECEIVE-only", card)
        self.assertTrue(row["indexed_a11"])
        self.assertEqual(row["hard_receive"]["state"], "FOUND")
        self.assertEqual(row["claude_corner"]["state"], "FINDER-FAILED")
        self.assertIsNone(row["claude_corner"]["count"])
        self.assertNotEqual(row["claude_corner"]["count"], 0)
        self.assertNotIn(STALE_OFF_GIT_PHRASE, card.lower())
        self.assertIn("muhl/docs/BULLY_CLAUDE.txt", card)
        self.assertIn("muhl/docs/CLAUDE_PROOF_PACKET.md", card)
        self.assertEqual(row["git_companions"]["state"], "FOUND")
        self.assertEqual(row["git_companions"]["missing"], [])
        self.assertFalse(row["card_stale_off_git"])
        git_row = git_companions_probe(ROOT)
        self.assertEqual(git_row["state"], "FOUND")
        self.assertEqual(len(git_row["hits"]), 9)
        with open(
            os.path.join(ROOT, "muhl", "docs", "CLAUDE_FAILURE_MODES.md"),
            encoding="utf-8",
        ) as handle:
            dump = handle.read()
        self.assertIn("## 17c.", dump)

    def test_missing_a11_is_not_landed(self):
        verdict = classify(_complete_facts(indexed_a11=False))
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(verdict["z"], "FINDER-FAILED")
        self.assertIn("HIT-SR01", verdict["note"])
        self.assertIn("not permission", verdict["note"])
        self.assertNotEqual(verdict.get("count"), 0)

    def test_index_has_a11_needs_law_not_permission(self):
        self.assertFalse(index_has_a11("A10 only", {}))
        self.assertTrue(
            index_has_a11(
                "| A11 | soft may edit/build/ship vs Plug RECEIVE-only — not a permission grant | HIT-SR01 |",
                {},
            )
        )
        self.assertTrue(
            index_has_a11(
                "",
                {
                    "a11_id": "A11",
                    "a11_hit": "HIT-SR01",
                    "a11_not_permission": True,
                    "a11_not_gate": True,
                    "authority": ["A11"],
                },
            )
        )

    def test_claude_corner_miss_is_finder_failed_never_zero(self):
        with tempfile.TemporaryDirectory(prefix="peer-check-corner-") as tmp:
            row = claude_corner_probe(tmp)
        self.assertEqual(row["state"], "FINDER-FAILED")
        self.assertIsNone(row["count"])
        self.assertNotEqual(row["count"], 0)
        self.assertIn("CLAUDE_CORNER.md", row["search_space"])

    def test_hard_receive_baseline_present_on_live_tree(self):
        row = hard_receive_baseline_probe(ROOT)
        self.assertEqual(row["state"], "FOUND")
        self.assertEqual(row["missing"], [])
        self.assertEqual(len(row["hits"]), 2)
        self.assertNotEqual(row.get("count"), 0)

    def test_missing_hard_receive_is_not_silent_zero(self):
        verdict = classify(
            _complete_facts(
                hard_receive={
                    "state": "FINDER-FAILED",
                    "missing": ["evidence/bully_sessions/BULLY_CLAUDE.txt"],
                    "count": None,
                }
            )
        )
        self.assertEqual(verdict["state"], "NOT_LANDED")
        self.assertEqual(verdict["z"], "FINDER-FAILED")
        self.assertIn("bully_sessions", verdict["note"])
        self.assertNotEqual(verdict.get("count"), 0)

    def test_soft_dumps_not_rewritten(self):
        for rel in (
            "muhl/docs/CLAUDE_PROOF_PACKET.md",
            "muhl/docs/BULLY_CLAUDE.txt",
            "muhl/docs/CHAIR.md",
            "muhl/docs/FABLE_PLAYER_PAD.txt",
        ):
            path = os.path.join(ROOT, rel)
            self.assertTrue(os.path.isfile(path), rel)


if __name__ == "__main__":
    unittest.main()
