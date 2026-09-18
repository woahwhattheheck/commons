#!/usr/bin/env python3
"""WINNER FOLD proofs: losers store zero, return scales with winners, ties deterministic."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOL = ROOT / "host" / "winner_fold.py"


def run(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), *argv],
        capture_output=True, text=True, timeout=60,
    )


class TestWinnerFold(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.fold = str(Path(self.td.name) / "fold.json")

    def tearDown(self):
        self.td.cleanup()

    def _open(self, addr_bits: int = 64) -> dict:
        r = run("open", self.fold, "--addr-bits", str(addr_bits), "--question", "best route")
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_fold_record_is_winner_only(self):
        opened = self._open()
        self.assertEqual(opened["winner_only"], 1)
        self.assertEqual(opened["stored_per_lane"], 0)

    def test_losing_lanes_store_zero(self):
        self._open()
        r = run("lane", self.fold, "--lane", "l1", "--nonce", "aa", "--score", "10")
        self.assertTrue(json.loads(r.stdout)["lane_is_current_winner"])
        for i in range(2, 12):
            r = run("lane", self.fold, "--lane", f"l{i}", "--nonce", f"{i:02x}", "--score", "5")
            out = json.loads(r.stdout)
            self.assertFalse(out["lane_is_current_winner"])
            self.assertEqual(out["stored_bytes_for_this_lane"], 0)

    def test_return_bytes_do_not_scale_with_lane_count(self):
        self._open()
        run("lane", self.fold, "--lane", "l1", "--nonce", "aa", "--score", "10")
        small = json.loads(run("status", self.fold).stdout)["return_bytes"]
        for i in range(2, 62):
            run("lane", self.fold, "--lane", f"l{i}", "--nonce", f"{i:04x}", "--score", "1")
        big = json.loads(run("status", self.fold).stdout)["return_bytes"]
        self.assertEqual(small, big)
        self.assertEqual(json.loads(run("status", self.fold).stdout)["lanes_seen"], 61)

    def test_close_surfaces_only_the_winner(self):
        self._open()
        run("lane", self.fold, "--lane", "slow", "--nonce", "01", "--score", "3")
        run("lane", self.fold, "--lane", "fast", "--nonce", "02", "--score", "9")
        run("lane", self.fold, "--lane", "mid", "--nonce", "03", "--score", "5")
        r = run("close", self.fold)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["winner"]["lane"], "fast")
        self.assertEqual(out["winner"]["nonce"], "02")
        self.assertEqual(out["lanes_seen"], 3)
        self.assertEqual(out["stored_per_lane"], 0)
        self.assertEqual(out["return_scales_with"], "winners")

    def test_tie_break_is_deterministic(self):
        self._open()
        run("lane", self.fold, "--lane", "b", "--nonce", "ff", "--score", "7")
        run("lane", self.fold, "--lane", "a", "--nonce", "01", "--score", "7")
        out = json.loads(run("close", self.fold).stdout)
        self.assertEqual(out["winner"]["nonce"], "01")
        self.assertEqual(out["winner"]["lane"], "a")

    def test_nonce_must_fit_addr_bits(self):
        self._open(addr_bits=8)
        r = run("lane", self.fold, "--lane", "l1", "--nonce", "1ff", "--score", "1")
        self.assertEqual(r.returncode, 2)
        self.assertIn("addr_bits", r.stderr)

    def test_closed_fold_rejects_new_lanes(self):
        self._open()
        run("lane", self.fold, "--lane", "l1", "--nonce", "aa", "--score", "1")
        self.assertEqual(run("close", self.fold).returncode, 0)
        r = run("lane", self.fold, "--lane", "l2", "--nonce", "bb", "--score", "2")
        self.assertEqual(r.returncode, 3)

    def test_close_without_winner_fails_closed(self):
        self._open()
        self.assertEqual(run("close", self.fold).returncode, 3)


if __name__ == "__main__":
    unittest.main()
