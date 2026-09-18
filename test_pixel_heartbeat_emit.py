#!/usr/bin/env python3
"""Current pixel heartbeat emitter writes honest session-state only."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from pixel_heartbeat_emit import (
    build_heartbeat,
    emit_root,
    merge_index,
    self_test,
)


class TestPixelHeartbeatEmit(unittest.TestCase):
    def test_self_test_ok(self):
        self.assertEqual(self_test(), "ok")

    def test_guessed_without_path_is_fabricated(self):
        built = build_heartbeat("DEMON", "", "guessed search", "2026-08-25T08:00:00Z")
        self.assertTrue(built["fabricated"])
        self.assertFalse(built["valid"])

    def test_empty_src_is_fabricated(self):
        built = build_heartbeat(
            "RIVET", "host/pixel_heartbeat_emit.py", "", "2026-08-25T08:00:00Z"
        )
        self.assertTrue(built["fabricated"])

    def test_honest_heartbeat_is_valid(self):
        built = build_heartbeat(
            "RIVET",
            "host/pixel_heartbeat_emit.py",
            "Cursor automation wrote the emitter",
            "2026-08-25T08:00:00Z",
            verb="shipping",
            on="cursor-cloud",
            sha="da2bd66b2bfa95847dc08bc4077a46385a8dbd77",
        )
        self.assertTrue(built["valid"])
        self.assertEqual(built["name"], "RIVET.json")
        self.assertFalse(built["fabricated"])

    def test_merge_index_keeps_player2(self):
        self.assertEqual(
            merge_index(["PLAYER2.json"], ["RIVET.json"]),
            ["PLAYER2.json", "RIVET.json"],
        )

    def test_emit_root_writes_and_preserves_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            pixel_dir = os.path.join(tmp, "pixels")
            os.makedirs(pixel_dir)
            with open(os.path.join(pixel_dir, "index.json"), "w", encoding="utf-8") as handle:
                json.dump(["PLAYER2.json"], handle)
            with open(os.path.join(pixel_dir, "PLAYER2.json"), "w", encoding="utf-8") as handle:
                json.dump({"from": "PLAYER2", "ts": "2026-08-20T11:05:00Z", "src": "session"}, handle)
            result = emit_root(
                tmp,
                "RIVET",
                "host/pixel_heartbeat_emit.py",
                "Cursor automation wrote the emitter",
                verb="shipping",
                on="cursor-cloud",
                sha="da2bd66b2",
                ts="2026-08-25T08:01:38Z",
                now="2026-08-25T08:01:38Z",
            )
            self.assertTrue(result["wrote"])
            self.assertEqual(result["freshness"], "HOT")
            with open(os.path.join(pixel_dir, "index.json"), encoding="utf-8") as handle:
                listed = json.load(handle)
            self.assertEqual(listed, ["PLAYER2.json", "RIVET.json"])
            self.assertTrue(os.path.isfile(os.path.join(pixel_dir, "PLAYER2.json")))


if __name__ == "__main__":
    unittest.main()
