#!/usr/bin/env python3
"""Frozen MUHC corpus leftover. Does not remint the peer container land."""

from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))
sys.path.insert(0, ROOT)

import muhc
import muhc_corpus
from muhc_corpus import (
    CALIBRATION,
    PEER_RECEIPT,
    PUBLISHED_PROGRAM,
    ROWS,
    SEARCH_SPACE,
    measure_root,
)


class TestMuhcCorpus(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        report = measure_root(os.path.join(ROOT, "does-not-exist-muhc-corpus"))
        self.assertEqual(report["state"], "UNMEASURED")
        self.assertEqual(report["z"], "FINDER-FAILED")
        self.assertFalse(report["calibration_ok"])

    def test_peer_files_are_not_this_leftover(self):
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "muhc.py")))
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "test_muhc.py")))
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "ground", "MUHC.md")))
        self.assertEqual(PEER_RECEIPT, "cursor-grok-46-muhc-roundtrip-20260825-01")
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "p", PEER_RECEIPT + ".md")))

    def test_same_run_known_present(self):
        hits = [rel for rel in CALIBRATION if os.path.isfile(os.path.join(ROOT, rel))]
        self.assertEqual(hits, list(CALIBRATION))
        self.assertGreaterEqual(len(SEARCH_SPACE), 8)

    def test_frozen_rows_pin_sha(self):
        for row in ROWS:
            path = os.path.join(ROOT, row["path"])
            self.assertTrue(os.path.isfile(path), row["path"])
            self.assertEqual(os.path.getsize(path), row["bytes"], row["id"])

    def test_gguf_miss_names_search_space(self):
        report = measure_root(ROOT)
        self.assertEqual(report["gguf"]["state"], "ABSENT")
        self.assertEqual(report["gguf"]["hits"], [])
        self.assertIn("*.gguf", report["gguf"]["search_space"])
        self.assertIn("titan NOT_WRITTEN", report["gguf"]["note"])

    def test_zstd_capability_is_measured_not_zero(self):
        report = measure_root(ROOT)
        self.assertIn(report["zstd"]["state"], ("PRESENT", "ABSENT"))
        self.assertIn("zstandard", report["zstd"]["search_space"][0])
        if report["zstd"]["state"] == "PRESENT":
            self.assertIn("module present", report["zstd"]["note"])
            for row in report["rows"]:
                self.assertIsInstance(row["entropy_file"]["zstd_file"], int)
                self.assertGreater(row["entropy_file"]["zstd_file"], 0)
        else:
            self.assertIn("ModuleNotFoundError", report["zstd"]["note"])
            for row in report["rows"]:
                self.assertIsNone(row["entropy_file"]["zstd_file"])
        self.assertIsInstance(report["rows"][0]["entropy_file"]["bz2_file"], int)
        self.assertIsInstance(report["rows"][0]["entropy_file"]["lzma_file"], int)

        with (
            mock.patch.object(muhc_corpus, "zstandard_mod", None),
            mock.patch.object(muhc_corpus, "zstd_mod", None),
        ):
            entropy, state, note = muhc_corpus.entropy_file(b"forced-absence-control")
        self.assertEqual(state, "ABSENT")
        self.assertIsNone(entropy["zstd_file"])
        self.assertIn("ModuleNotFoundError", note)

    def test_live_tree_matrix_and_roundtrip(self):
        report = measure_root(ROOT)
        self.assertEqual(report["state"], "INTEGRATED")
        by_id = {row["id"]: row for row in report["rows"]}
        self.assertTrue(by_id["tail7"]["stack_roundtrip_ok"])
        self.assertTrue(by_id["shot1bpp"]["stack_roundtrip_ok"])
        self.assertTrue(by_id["SEED0"]["stack_roundtrip_ok"])
        self.assertTrue(by_id["FOUNDRY0"]["stack_roundtrip_ok"])
        self.assertTrue(by_id["AUTOFAB0"]["stack_roundtrip_ok"])
        seed = by_id["SEED0"]["muhc"]
        self.assertGreater(seed["stack_v1"]["container_b"], seed["zlib_file"]["container_b"])
        foundry = by_id["FOUNDRY0"]["muhc"]
        self.assertLess(foundry["stack_v1"]["container_b"], foundry["zlib_file"]["container_b"])
        self.assertEqual(foundry["stack_v1"]["container_b"], 274)
        autofab = by_id["AUTOFAB0"]["muhc"]
        self.assertLess(autofab["evolve_v1"]["container_b"], autofab["zlib_file"]["container_b"])
        self.assertEqual(report["published_program"], PUBLISHED_PROGRAM)

    def test_peer_decode_api_still_independent(self):
        path = os.path.join(ROOT, "compress", "muhc_v1", "corpus", "tail7.bin")
        with open(path, "rb") as handle:
            data = handle.read()
        blob = muhc.encode_bytes(data, 5, codec="stack", tile_w=3, tile_h=2)
        rec, header = muhc.decode_bytes(blob)
        self.assertEqual(rec, data)
        self.assertTrue(blob.startswith(b"MUHC"))
        self.assertEqual(header["codec_name"], "stack_v1")


if __name__ == "__main__":
    unittest.main()
