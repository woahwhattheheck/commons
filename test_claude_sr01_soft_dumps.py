#!/usr/bin/env python3
"""HIT-SR01 leftover: measure soft dumps vs RECEIVE baseline. Never silent 0."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from claude_sr01_soft_dumps import (
    CALIBRATION,
    DO_NOT_REMINT,
    DO_NOT_REWRITE,
    KNOWN_BLOBS,
    RECEIVE_BASELINE,
    SEARCH_SPACE,
    SOFT_DUMPS,
    SOFT_NEEDLE,
    classify,
    file_row,
    has_receive_phrase,
    has_soft_phrase,
    measure_from_rows,
    measure_root,
    pair_row,
    self_test,
)


def _complete(**overrides):
    facts = {
        "calibration_ok": True,
        "calibration_hits": list(CALIBRATION),
        "no_auth": True,
        "no_gate": True,
        "posting": "OPEN",
        "soft_dumps": [{"path": rel, "state": "FOUND"} for rel in SOFT_DUMPS],
        "baselines": [{"path": rel, "state": "FOUND"} for rel in RECEIVE_BASELINE],
        "pairs": [
            {
                "soft": SOFT_DUMPS[0],
                "hard": RECEIVE_BASELINE[0],
                "state": "DIVERGE",
                "diverge": True,
            },
            {
                "soft": SOFT_DUMPS[1],
                "hard": RECEIVE_BASELINE[1],
                "state": "DIVERGE",
                "diverge": True,
            },
        ],
    }
    facts.update(overrides)
    return measure_from_rows(facts)


class TestClaudeSr01SoftDumps(unittest.TestCase):
    def test_self_test_ok(self):
        self.assertEqual(self_test(), "ok")

    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertEqual(row["z"], "FINDER-FAILED")
        self.assertIn("Never 0", row["note"])
        self.assertNotEqual(row.get("count"), 0)

    def test_failed_calibration_is_instrument_failure(self):
        row = classify(_complete(calibration_ok=False, calibration_hits=[]))
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertEqual(row["z"], "FINDER-FAILED")
        self.assertIn("instrument failure", row["note"])

    def test_closed_door_is_discarded(self):
        row = classify(_complete(no_auth=False))
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("closed the door", row["note"])

    def test_missing_soft_dump_is_finder_failed(self):
        row = classify(
            _complete(
                soft_dumps=[
                    {"path": "muhl/docs/CHAIR.md", "state": "FINDER-FAILED", "count": None}
                ]
            )
        )
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertEqual(row["z"], "FINDER-FAILED")
        self.assertIn("CHAIR.md", row["note"])
        self.assertIsNone(
            classify(
                _complete(
                    soft_dumps=[
                        {
                            "path": "muhl/docs/CHAIR.md",
                            "state": "FINDER-FAILED",
                            "count": None,
                        }
                    ]
                )
            ).get("count")
        )

    def test_same_pair_is_not_silent_merge(self):
        row = classify(
            _complete(
                pairs=[
                    {
                        "soft": "s.md",
                        "hard": "h.md",
                        "state": "SAME",
                        "diverge": False,
                    }
                ]
            )
        )
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("diverge", row["note"].lower())

    def test_integrated_keeps_soft_as_not_permission(self):
        row = classify(_complete())
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertIs(row["z"]["permission"], False)
        self.assertEqual(row["z"]["pairs"], "DIVERGE")
        self.assertIn("not permission", row["note"].lower())

    def test_soft_and_receive_needles(self):
        self.assertTrue(
            has_soft_phrase("Claude peers may edit, build, ship, merge, and deploy.")
        )
        self.assertTrue(has_receive_phrase("seated_claude = NO. OPUS RECEIVES ONLY."))
        self.assertFalse(has_soft_phrase("Claude RECEIVES. Claude writes nothing."))
        self.assertFalse(has_receive_phrase("only a chair note"))
        self.assertEqual(SOFT_NEEDLE, "may edit, build, ship")

    def test_file_row_missing_is_finder_failed(self):
        with tempfile.TemporaryDirectory(prefix="sr01-soft-") as tmp:
            row = file_row(tmp, "muhl/docs/CHAIR.md", "soft")
        self.assertEqual(row["state"], "FINDER-FAILED")
        self.assertIsNone(row["count"])
        self.assertFalse(row["present"])

    def test_pair_row_missing_is_finder_failed(self):
        with tempfile.TemporaryDirectory(prefix="sr01-pair-") as tmp:
            row = pair_row(tmp, "soft.md", "hard.md")
        self.assertEqual(row["state"], "FINDER-FAILED")
        self.assertIsNone(row["count"])
        self.assertFalse(row["diverge"])

    def test_pair_row_same_bytes_is_not_diverge(self):
        with tempfile.TemporaryDirectory(prefix="sr01-same-") as tmp:
            with open(os.path.join(tmp, "a.md"), "w", encoding="utf-8") as handle:
                handle.write("same")
            with open(os.path.join(tmp, "b.md"), "w", encoding="utf-8") as handle:
                handle.write("same")
            row = pair_row(tmp, "a.md", "b.md")
        self.assertEqual(row["state"], "SAME")
        self.assertFalse(row["diverge"])

    def test_fixture_diverge_is_integrated(self):
        with tempfile.TemporaryDirectory(prefix="sr01-live-") as tmp:
            os.makedirs(os.path.join(tmp, "ground"))
            os.makedirs(os.path.join(tmp, "muhl", "docs"))
            os.makedirs(os.path.join(tmp, "evidence", "bully_sessions"))
            os.makedirs(os.path.join(tmp, "host"))
            with open(os.path.join(tmp, "ground", "HEAD.md"), "w", encoding="utf-8") as handle:
                handle.write("HEAD truth\n")
            with open(
                os.path.join(tmp, "ground", "CLAUDE_PEER_CHECK.md"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write("A11 HIT-SR01 seated_claude=NO\n")
            with open(
                os.path.join(tmp, "muhl", "docs", "CLAUDE_PROOF_PACKET.md"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write("Claude peers may edit, build, ship, merge, and deploy.\n")
            with open(
                os.path.join(tmp, "muhl", "docs", "BULLY_CLAUDE.txt"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write("It may edit, build, ship, merge, and deploy.\n")
            with open(
                os.path.join(tmp, "muhl", "docs", "CHAIR.md"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write("Fable peers may edit, build, ship, merge, and deploy.\n")
            with open(
                os.path.join(tmp, "muhl", "docs", "FABLE_PLAYER_PAD.txt"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write(
                    "seated_claude = NO. Claude peers may edit, build, ship.\n"
                )
            with open(
                os.path.join(tmp, "evidence", "bully_sessions", "CLAUDE_PROOF_PACKET.md"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write("seated_claude = NO. OPUS RECEIVES ONLY.\n")
            with open(
                os.path.join(tmp, "evidence", "bully_sessions", "BULLY_CLAUDE.txt"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write("Claude-family is NOT a builder. It writes nothing.\n")
            with open(
                os.path.join(tmp, "host", "claude_sr01_soft_dumps.py"),
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write("# leftover\n")
            row = measure_root(tmp)
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertTrue(row["calibration_ok"])
        self.assertIs(row["permission"], False)
        self.assertEqual(row["posting"], "OPEN")
        self.assertTrue(all(item["state"] == "FOUND" for item in row["soft_dumps"]))
        self.assertTrue(all(item["state"] == "FOUND" for item in row["baselines"]))
        self.assertTrue(all(item["state"] == "DIVERGE" for item in row["pairs"]))

    def test_live_tree_measures_diverge_without_rewrite(self):
        row = measure_root(ROOT)
        self.assertTrue(row["calibration_ok"])
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertEqual(row["posting"], "OPEN")
        self.assertTrue(row["no_auth"])
        self.assertTrue(row["no_gate"])
        self.assertIs(row["permission"], False)
        self.assertEqual([item["state"] for item in row["soft_dumps"]], ["FOUND"] * 4)
        self.assertEqual([item["state"] for item in row["baselines"]], ["FOUND"] * 2)
        self.assertEqual([item["state"] for item in row["pairs"]], ["DIVERGE"] * 2)
        self.assertIn("cursor-claude-peer-check-seated-receive-20260902-01", DO_NOT_REMINT)
        self.assertEqual(len(DO_NOT_REWRITE), 6)
        self.assertIn(PEER_CHECK := os.path.join("ground", "CLAUDE_PEER_CHECK.md"), SEARCH_SPACE)
        self.assertTrue(os.path.isfile(os.path.join(ROOT, PEER_CHECK)))
        for rel, expected in KNOWN_BLOBS.items():
            blob = subprocess.check_output(
                ["git", "-C", ROOT, "rev-parse", "HEAD:%s" % rel],
                text=True,
            ).strip()
            self.assertEqual(blob, expected)
        with open(
            os.path.join(ROOT, "muhl", "docs", "CLAUDE_PROOF_PACKET.md"),
            encoding="utf-8",
        ) as handle:
            soft = handle.read()
        with open(
            os.path.join(ROOT, "evidence", "bully_sessions", "CLAUDE_PROOF_PACKET.md"),
            encoding="utf-8",
        ) as handle:
            hard = handle.read()
        self.assertIn("may edit, build, ship", soft.lower())
        self.assertIn("seated_claude", hard.lower())
        self.assertNotEqual(soft, hard)


if __name__ == "__main__":
    unittest.main()
