#!/usr/bin/env python3
"""Focused tests for the public GRBN one-settle walker.

Work order kimi-subzero-walker-20260829-01. Does not rewrite the
excerpt or the structural fabricator. Does not open titan.
"""
from __future__ import annotations

import hashlib
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from subzero_walk import (
    ARTIFACT_REL,
    EXCERPT_GIT_BLOB,
    EXCERPT_REL,
    EXCERPT_SHA256,
    FAB_GIT_BLOB,
    FAB_REL,
    N_GATE,
    SIDECAR_GIT_BLOB,
    SIDECAR_REL,
    format_artifact,
    git_blob_sha1,
    load_artifact,
    load_excerpt,
    measure,
    nk_next_from_state,
    self_test,
    walk_settle,
)


def _blob_sha(rel):
    with open(os.path.join(ROOT, rel), "rb") as handle:
        return git_blob_sha1(handle.read())


class TestSubzeroWalk(unittest.TestCase):
    def test_frozen_blobs_byte_for_byte(self):
        self.assertEqual(_blob_sha(EXCERPT_REL), EXCERPT_GIT_BLOB)
        self.assertEqual(_blob_sha(SIDECAR_REL), SIDECAR_GIT_BLOB)
        self.assertEqual(_blob_sha(FAB_REL), FAB_GIT_BLOB)
        excerpt = load_excerpt(ROOT)
        self.assertEqual(hashlib.sha256(excerpt).hexdigest(), EXCERPT_SHA256)

    def test_sync_settle_matches_nk_oracle_and_committed_artifact(self):
        row, blob, gates, addrs = measure(ROOT, snapshot=True)
        self.assertEqual(row["gates_evaluated"], N_GATE)
        self.assertEqual(row["class"], "RUNTIME_MEASURED")
        self.assertEqual(row["titan"], "NOT_WRITTEN")
        self.assertEqual(row["init_popcount"], 0)
        self.assertEqual(row["next_popcount"], 125)
        init = [blob[addr] & 1 for addr in addrs]
        nk = nk_next_from_state(init)
        sync = [1 if ch == "1" else 0 for ch in row["next_state_bits"]]
        self.assertEqual(sync, nk)
        self.assertEqual(load_artifact(ROOT), format_artifact(row))
        self.assertTrue(os.path.isfile(os.path.join(ROOT, ARTIFACT_REL)))

    def test_snapshot_rule_sync_is_not_async(self):
        row, blob, gates, addrs = measure(ROOT, snapshot=True)
        async_bits = walk_settle(blob, gates, addrs, snapshot=False)
        sync_bits = [1 if ch == "1" else 0 for ch in row["next_state_bits"]]
        self.assertNotEqual(sync_bits, async_bits)
        self.assertEqual(sum(async_bits), 128)
        self.assertEqual(sum(sync_bits), 125)

    def test_walker_does_not_mutate_excerpt(self):
        before = load_excerpt(ROOT)
        measure(ROOT, snapshot=True)
        after = load_excerpt(ROOT)
        self.assertEqual(before, after)
        self.assertEqual(git_blob_sha1(after), EXCERPT_GIT_BLOB)

    def test_self_test_and_stdlib_only(self):
        result = self_test(ROOT)
        self.assertTrue(result["ok"])
        with open(os.path.join(ROOT, "host", "subzero_walk.py"), encoding="utf-8") as handle:
            src = handle.read()
        self.assertIn("does not open titan.gguf", src.lower())
        banned = ("import numpy", "import cupy", "from numpy")
        for phrase in banned:
            self.assertNotIn(phrase, src)

    def test_walker_does_not_write_live_containers(self):
        with open(os.path.join(ROOT, "host", "subzero_walk.py"), encoding="utf-8") as handle:
            src = handle.read()
        self.assertIn("does not write commons.mno", src.lower())
        self.assertNotIn('open(os.path.join(root, "titan.gguf")', src)
        self.assertNotIn('open("commons.mno"', src)


if __name__ == "__main__":
    unittest.main()
